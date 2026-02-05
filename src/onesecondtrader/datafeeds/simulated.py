from __future__ import annotations

import itertools
import os
import sqlite3
import threading

from onesecondtrader import events, messaging, models
from onesecondtrader.datafeeds.base import DatafeedBase

_RTYPE_MAP = {
    models.BarPeriod.SECOND: 32,
    models.BarPeriod.MINUTE: 33,
    models.BarPeriod.HOUR: 34,
    models.BarPeriod.DAY: 35,
}

_RTYPE_TO_BAR_PERIOD = {v: k for k, v in _RTYPE_MAP.items()}


class SimulatedDatafeed(DatafeedBase):
    """
    Simulated market data feed backed by a secmaster SQLite database.

    This datafeed replays historical OHLCV bars from a secmaster database, resolving symbols
    via time-bounded symbology mappings. Bars are delivered in timestamp order, with all bars
    sharing the same timestamp published before calling `wait_until_system_idle`.

    Subclasses must set `publisher_name`, `dataset`, and `symbol_type` as class attributes to
    scope the feed to a specific data source. The database must contain publishers with numeric
    `source_instrument_id` values; symbol-only publishers (e.g., yfinance) are not supported.
    """

    db_path: str = ""
    publisher_name: str = ""
    dataset: str = ""
    symbol_type: str = ""
    price_scale: float = 1e9
    start_ts: int | None = None
    end_ts: int | None = None

    def __init__(self, event_bus: messaging.EventBus) -> None:
        """
        Parameters:
            event_bus:
                Event bus used to publish bar events and synchronize with subscribers.
        """
        super().__init__(event_bus)
        self._db_path = self.db_path or os.environ.get(
            "SECMASTER_DB_PATH", "secmaster.db"
        )
        if not self.publisher_name:
            raise ValueError("publisher_name is required")
        if not self.dataset:
            raise ValueError("dataset is required")
        if not self.symbol_type:
            raise ValueError("symbol_type is required")
        self._subscriptions: set[tuple[str, models.BarPeriod]] = set()
        self._subscriptions_lock = threading.Lock()
        self._connection: sqlite3.Connection | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._publisher_id: int | None = None

    def connect(self) -> None:
        """
        Open a connection to the secmaster database and resolve the publisher.

        If already connected, this method returns immediately.
        """
        if self._connection:
            return
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        row = self._connection.execute(
            "SELECT publisher_id FROM publishers WHERE name = ? AND dataset = ?",
            (self.publisher_name, self.dataset),
        ).fetchone()
        if row is None:
            raise ValueError(
                f"Publisher not found: {self.publisher_name}/{self.dataset}"
            )
        self._publisher_id = row[0]

    def disconnect(self) -> None:
        """
        Close the database connection and stop any active streaming.

        If not connected, this method returns immediately.
        """
        if not self._connection:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()
        self._connection.close()
        self._connection = None
        self._publisher_id = None

    def subscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        """
        Register symbols for bar delivery at the specified period.

        Parameters:
            symbols:
                List of ticker symbols to subscribe.
            bar_period:
                Bar aggregation period for the subscription.
        """
        with self._subscriptions_lock:
            self._subscriptions.update((s, bar_period) for s in symbols)

    def unsubscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        """
        Remove symbols from bar delivery at the specified period.

        Parameters:
            symbols:
                List of ticker symbols to unsubscribe.
            bar_period:
                Bar aggregation period for the subscription.
        """
        with self._subscriptions_lock:
            self._subscriptions.difference_update((s, bar_period) for s in symbols)

    def wait_until_complete(self) -> None:
        """
        Stream all subscribed bars and block until delivery is complete.

        Bars are published in timestamp order. After each timestamp batch, the method
        waits for all event bus subscribers to become idle before proceeding.
        """
        with self._subscriptions_lock:
            has_subscriptions = bool(self._subscriptions)
        if not has_subscriptions:
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
        if not self._connection or self._publisher_id is None:
            return

        with self._subscriptions_lock:
            subscriptions = list(self._subscriptions)
        if not subscriptions:
            return

        symbols = list({symbol for symbol, _ in subscriptions})
        rtypes = list({_RTYPE_MAP[bp] for _, bp in subscriptions})
        subscription_set = {(symbol, _RTYPE_MAP[bp]) for symbol, bp in subscriptions}

        params: list = [self._publisher_id, self.symbol_type]
        params.extend(symbols)
        params.extend(rtypes)
        if self.start_ts is not None:
            params.append(self.start_ts)
        if self.end_ts is not None:
            params.append(self.end_ts)

        query = f"""
            SELECT s.symbol, o.rtype, o.ts_event, o.open, o.high, o.low, o.close, o.volume
            FROM ohlcv o
            JOIN instruments i ON i.instrument_id = o.instrument_id
            JOIN symbology s
              ON s.publisher_ref = i.publisher_ref
             AND s.source_instrument_id = i.source_instrument_id
             AND date(o.ts_event / 1000000000, 'unixepoch') >= s.start_date
             AND date(o.ts_event / 1000000000, 'unixepoch') < s.end_date
            WHERE i.publisher_ref = ?
              AND s.symbol_type = ?
              AND s.symbol IN ({",".join("?" * len(symbols))})
              AND o.rtype IN ({",".join("?" * len(rtypes))})
              {"AND o.ts_event >= ?" if self.start_ts is not None else ""}
              {"AND o.ts_event <= ?" if self.end_ts is not None else ""}
            ORDER BY o.ts_event, s.symbol
        """

        rows = self._connection.execute(query, params)

        def to_bar(row):
            symbol, rtype, ts_event, open_, high, low, close, volume = row
            if (symbol, rtype) not in subscription_set:
                return None
            return events.market.BarReceived(
                ts_event_ns=ts_event,
                symbol=symbol,
                bar_period=_RTYPE_TO_BAR_PERIOD[rtype],
                open=open_ / self.price_scale,
                high=high / self.price_scale,
                low=low / self.price_scale,
                close=close / self.price_scale,
                volume=volume,
            )

        for _, group in itertools.groupby(rows, key=lambda r: r[2]):
            if self._stop_event.is_set():
                return
            for bar in filter(None, map(to_bar, group)):
                self._publish(bar)
            self._event_bus.wait_until_system_idle()
