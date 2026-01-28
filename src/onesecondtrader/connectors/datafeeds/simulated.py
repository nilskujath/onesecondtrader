from __future__ import annotations

import os
import sqlite3
import threading

import pandas as pd

from onesecondtrader.core import events, messaging, models
from onesecondtrader.core.datafeeds import DatafeedBase

_RTYPE_MAP = {
    models.BarPeriod.SECOND: 32,
    models.BarPeriod.MINUTE: 33,
    models.BarPeriod.HOUR: 34,
    models.BarPeriod.DAY: 35,
}

_PRICE_SCALE = 1e9


class SimulatedDatafeed(DatafeedBase):
    db_path: str = ""
    start_ts: int | None = None
    end_ts: int | None = None

    def __init__(self, event_bus: messaging.EventBus) -> None:
        super().__init__(event_bus)
        self._db_path = self.db_path or os.environ.get(
            "SECMASTER_DB_PATH", "secmaster.db"
        )
        self._connected = False
        self._subscriptions: set[tuple[str, models.BarPeriod]] = set()
        self._connection: sqlite3.Connection | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def connect(self) -> None:
        if self._connected:
            return
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connected = True

    def disconnect(self) -> None:
        if not self._connected:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()
        if self._connection:
            self._connection.close()
            self._connection = None
        self._connected = False

    def subscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        self._subscriptions.add((symbol, bar_period))

    def unsubscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        self._subscriptions.discard((symbol, bar_period))

    def wait_until_complete(self) -> None:
        if not self._subscriptions:
            return
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._stream,
                name=self.__class__.__name__,
                daemon=False,
            )
            self._thread.start()
        self._thread.join()

    def _stream(self) -> None:
        if not self._connection:
            return

        subscriptions = list(self._subscriptions)
        if not subscriptions:
            return

        symbol_rtype_pairs = [
            (symbol, _RTYPE_MAP[bar_period]) for symbol, bar_period in subscriptions
        ]
        rtype_by_symbol = {symbol: rtype for symbol, rtype in symbol_rtype_pairs}
        bar_period_by_symbol = {symbol: bp for symbol, bp in subscriptions}
        symbols = list(rtype_by_symbol.keys())

        cursor = self._connection.cursor()

        symbology_map = self._load_symbology(cursor, symbols)
        if not symbology_map:
            return

        all_instrument_ids = set()
        for entries in symbology_map.values():
            for entry in entries:
                all_instrument_ids.add(entry["instrument_id"])

        id_list = list(all_instrument_ids)
        rtype_list = list(set(rtype_by_symbol.values()))

        placeholders_ids = ",".join("?" * len(id_list))
        placeholders_rtypes = ",".join("?" * len(rtype_list))

        date_filter = ""
        params = id_list + rtype_list
        if self.start_ts is not None:
            date_filter += " AND ts_event >= ?"
            params.append(self.start_ts)
        if self.end_ts is not None:
            date_filter += " AND ts_event <= ?"
            params.append(self.end_ts)

        query = f"""
            SELECT instrument_id, rtype, ts_event, open, high, low, close, volume
            FROM ohlcv
            WHERE instrument_id IN ({placeholders_ids})
              AND rtype IN ({placeholders_rtypes})
              {date_filter}
            ORDER BY ts_event
        """

        cursor.execute(query, params)

        while True:
            if self._stop_event.is_set():
                return

            row = cursor.fetchone()
            if row is None:
                break

            instrument_id, rtype, ts_event, open_, high, low, close, volume = row

            symbol = self._resolve_symbol_for_bar(
                symbology_map, instrument_id, ts_event
            )
            if symbol is None:
                continue

            expected_rtype = rtype_by_symbol.get(symbol)
            if rtype != expected_rtype:
                continue

            bar_period = bar_period_by_symbol[symbol]

            self._publish(
                events.BarReceived(
                    ts_event=pd.Timestamp(ts_event, unit="ns", tz="UTC"),
                    symbol=symbol,
                    bar_period=bar_period,
                    open=open_ / _PRICE_SCALE,
                    high=high / _PRICE_SCALE,
                    low=low / _PRICE_SCALE,
                    close=close / _PRICE_SCALE,
                    volume=volume,
                )
            )
            self._event_bus.wait_until_system_idle()

    def _load_symbology(
        self, cursor: sqlite3.Cursor, symbols: list[str]
    ) -> dict[str, list[dict]]:
        placeholders = ",".join("?" * len(symbols))
        query = f"""
            SELECT symbol, instrument_id, start_date, end_date
            FROM symbology
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, start_date
        """
        cursor.execute(query, symbols)

        result: dict[str, list[dict]] = {}
        for row in cursor.fetchall():
            symbol, instrument_id, start_date, end_date = row
            start_ns = int(pd.Timestamp(start_date, tz="UTC").value)
            end_ns = int(pd.Timestamp(end_date, tz="UTC").value)
            if symbol not in result:
                result[symbol] = []
            result[symbol].append(
                {
                    "instrument_id": instrument_id,
                    "start_ns": start_ns,
                    "end_ns": end_ns,
                }
            )
        return result

    def _resolve_symbol_for_bar(
        self, symbology_map: dict[str, list[dict]], instrument_id: int, ts_event: int
    ) -> str | None:
        for symbol, entries in symbology_map.items():
            for entry in entries:
                if entry["instrument_id"] == instrument_id:
                    if entry["start_ns"] <= ts_event < entry["end_ns"]:
                        return symbol
        return None
