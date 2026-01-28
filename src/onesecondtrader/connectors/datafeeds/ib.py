from __future__ import annotations

import logging
import os
import sqlite3

import pandas as pd
from ib_async import Contract

from onesecondtrader.connectors.gateways.ib import _get_gateway, make_contract
from onesecondtrader.core import events, messaging, models
from onesecondtrader.core.datafeeds import DatafeedBase

_logger = logging.getLogger(__name__)

_BAR_SIZE_MAP = {
    models.BarPeriod.MINUTE: "1 min",
    models.BarPeriod.HOUR: "1 hour",
    models.BarPeriod.DAY: "1 day",
}


class IBDatafeed(DatafeedBase):
    """
    Live market data feed from Interactive Brokers.

    Subscribes to real-time bar data from IB and publishes BarReceived events.

    Symbol Resolution:
        Symbols are resolved to IB Contracts using a priority system:

        1. Explicit format: Use colon-separated qualifiers for full control.
           Format: ``SYMBOL:SECTYPE:CURRENCY:EXCHANGE[:EXPIRY[:STRIKE[:RIGHT]]]``

           Examples:
               - ``"AAPL:STK:USD:SMART"`` - Apple stock
               - ``"EUR:CASH:USD:IDEALPRO"`` - EUR/USD forex
               - ``"ES:FUT:USD:CME:202503"`` - ES futures March 2025
               - ``"AAPL:OPT:USD:SMART:20250321:150:C"`` - AAPL call option

        2. Secmaster lookup: If ``db_path`` is configured and the symbol exists
           in the instruments table, contract details are read from there.

        3. Default: Simple symbols like ``"AAPL"`` are treated as US stocks
           traded on SMART routing with USD currency.

    Bar Periods:
        - ``BarPeriod.SECOND``: Uses tick-by-tick data aggregated into 1-second
          bars. Limited to 5 simultaneous subscriptions by IB.
        - ``BarPeriod.MINUTE``, ``HOUR``, ``DAY``: Uses historical data with
          live updates. Limited to 50 simultaneous subscriptions by IB.

    Attributes:
        db_path: Optional path to secmaster database for symbol resolution.
            If empty, uses SECMASTER_DB_PATH environment variable.
            If neither is set, secmaster lookup is disabled.
    """

    db_path: str = ""

    def __init__(self, event_bus: messaging.EventBus) -> None:
        super().__init__(event_bus)
        self._gateway = _get_gateway()
        self._connected = False
        self._subscriptions: set[tuple[str, models.BarPeriod]] = set()
        self._active_bars: dict[tuple[str, models.BarPeriod], object] = {}
        self._db_connection: sqlite3.Connection | None = None
        self._tick_aggregators: dict[str, _TickAggregator] = {}
        self._lock = __import__("threading").Lock()

    def connect(self) -> None:
        if self._connected:
            return
        _logger.info("Connecting to IB datafeed")
        self._gateway.acquire()
        self._gateway.register_reconnect_callback(self._on_reconnect)
        self._gateway.register_disconnect_callback(self._on_disconnect)
        db_path = self.db_path or os.environ.get("SECMASTER_DB_PATH", "")
        if db_path and os.path.exists(db_path):
            self._db_connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connected = True
        _logger.info("Connected to IB datafeed")

    def disconnect(self) -> None:
        if not self._connected:
            return
        _logger.info("Disconnecting from IB datafeed")
        self._gateway.unregister_reconnect_callback(self._on_reconnect)
        self._gateway.unregister_disconnect_callback(self._on_disconnect)
        with self._lock:
            for symbol, bar_period in list(self._subscriptions):
                self.unsubscribe(symbol, bar_period)
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None
        self._gateway.release()
        self._connected = False
        _logger.info("Disconnected from IB datafeed")

    def _on_disconnect(self) -> None:
        _logger.warning("IB connection lost, clearing stale state")
        with self._lock:
            self._active_bars.clear()
            self._tick_aggregators.clear()

    def _on_reconnect(self) -> None:
        with self._lock:
            subscriptions_to_restore = list(self._subscriptions)
        _logger.info(
            "Restoring %d subscriptions after reconnect", len(subscriptions_to_restore)
        )
        with self._lock:
            self._active_bars.clear()
            self._tick_aggregators.clear()
        for symbol, bar_period in subscriptions_to_restore:
            with self._lock:
                self._subscriptions.discard((symbol, bar_period))
            self.subscribe(symbol, bar_period)

    def subscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        with self._lock:
            if (symbol, bar_period) in self._subscriptions:
                return
            _logger.info("Subscribing to %s %s", symbol, bar_period.name)
            self._subscriptions.add((symbol, bar_period))
        contract = self._make_contract(symbol)

        if bar_period == models.BarPeriod.SECOND:
            self._subscribe_tick(symbol, contract, bar_period)
        else:
            self._subscribe_historical(symbol, contract, bar_period)

    def unsubscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        with self._lock:
            if (symbol, bar_period) not in self._subscriptions:
                return
            _logger.info("Unsubscribing from %s %s", symbol, bar_period.name)
            self._subscriptions.discard((symbol, bar_period))
            bars = self._active_bars.pop((symbol, bar_period), None)
        if bars is None:
            return

        if bar_period == models.BarPeriod.SECOND:
            self._gateway.run_coro(self._cancel_tick_async(bars))
            with self._lock:
                self._tick_aggregators.pop(symbol, None)
        else:
            self._gateway.run_coro(self._cancel_historical_async(bars))

    def _subscribe_historical(
        self, symbol: str, contract: Contract, bar_period: models.BarPeriod
    ) -> None:
        bar_size = _BAR_SIZE_MAP[bar_period]

        async def _subscribe():
            bars = await self._gateway.ib.reqHistoricalDataAsync(
                contract,
                endDateTime="",
                durationStr="1 D",
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=False,
                keepUpToDate=True,
            )
            bars.updateEvent += lambda b, has_new: self._on_historical_update(
                symbol, bar_period, b, has_new
            )
            return bars

        bars = self._gateway.run_coro(_subscribe())
        self._active_bars[(symbol, bar_period)] = bars

    def _subscribe_tick(
        self, symbol: str, contract: Contract, bar_period: models.BarPeriod
    ) -> None:
        aggregator = _TickAggregator(symbol, bar_period, self._publish)
        self._tick_aggregators[symbol] = aggregator

        async def _subscribe():
            ticker = await self._gateway.ib.reqTickByTickDataAsync(
                contract, tickType="AllLast"
            )
            ticker.updateEvent += lambda t: self._on_tick_update(symbol, t)
            return ticker

        ticker = self._gateway.run_coro(_subscribe())
        self._active_bars[(symbol, bar_period)] = ticker

    async def _cancel_historical_async(self, bars) -> None:
        self._gateway.ib.cancelHistoricalData(bars)

    async def _cancel_tick_async(self, ticker) -> None:
        self._gateway.ib.cancelTickByTickData(ticker.contract, "AllLast")

    def _on_historical_update(
        self, symbol: str, bar_period: models.BarPeriod, bars, has_new_bar: bool
    ) -> None:
        if not has_new_bar or not bars:
            return
        bar = bars[-1]
        self._publish(
            events.BarReceived(
                ts_event=pd.Timestamp(bar.date, tz="UTC"),
                symbol=symbol,
                bar_period=bar_period,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=int(bar.volume),
            )
        )

    def _on_tick_update(self, symbol: str, ticker) -> None:
        aggregator = self._tick_aggregators.get(symbol)
        if aggregator is None:
            return
        for tick in ticker.tickByTicks:
            if tick is not None:
                aggregator.on_tick(tick.time, tick.price, tick.size)

    def _make_contract(self, symbol: str):
        return make_contract(symbol, self._db_connection)


class _TickAggregator:
    def __init__(
        self,
        symbol: str,
        bar_period: models.BarPeriod,
        publish_fn,
    ) -> None:
        self._symbol = symbol
        self._bar_period = bar_period
        self._publish = publish_fn
        self._current_second: pd.Timestamp | None = None
        self._open: float = 0.0
        self._high: float = 0.0
        self._low: float = 0.0
        self._close: float = 0.0
        self._volume: int = 0

    def on_tick(self, time: pd.Timestamp, price: float, size: int) -> None:
        tick_second = time.floor("s")

        if self._current_second is None:
            self._start_new_bar(tick_second, price, size)
            return

        if tick_second > self._current_second:
            self._emit_bar()
            self._start_new_bar(tick_second, price, size)
        else:
            self._update_bar(price, size)

    def _start_new_bar(
        self, tick_second: pd.Timestamp, price: float, size: int
    ) -> None:
        self._current_second = tick_second
        self._open = price
        self._high = price
        self._low = price
        self._close = price
        self._volume = size

    def _update_bar(self, price: float, size: int) -> None:
        self._high = max(self._high, price)
        self._low = min(self._low, price)
        self._close = price
        self._volume += size

    def _emit_bar(self) -> None:
        if self._current_second is None:
            return
        self._publish(
            events.BarReceived(
                ts_event=self._current_second,
                symbol=self._symbol,
                bar_period=self._bar_period,
                open=self._open,
                high=self._high,
                low=self._low,
                close=self._close,
                volume=self._volume,
            )
        )
