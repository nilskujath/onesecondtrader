from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import threading
import time

from ib_async import Contract, Forex, Future, IB, Option, Stock

_logger = logging.getLogger(__name__)

_INSTRUMENT_CLASS_MAP = {
    "K": "STK",
    "F": "FUT",
    "C": "OPT",
    "P": "OPT",
    "X": "CASH",
}


def make_contract(
    symbol: str, db_connection: sqlite3.Connection | None = None
) -> Contract:
    """
    Resolve a symbol string to an IB Contract.

    Resolution priority:
        1. Explicit format with colons (e.g., ``"AAPL:STK:USD:SMART"``)
        2. Secmaster database lookup (if db_connection provided)
        3. Default: US stock on SMART routing

    Args:
        symbol: Symbol string, either simple (``"AAPL"``) or qualified
            (``"AAPL:STK:USD:SMART"``).
        db_connection: Optional SQLite connection to secmaster database.

    Returns:
        An ib_async Contract object.
    """
    if ":" in symbol:
        return _parse_qualified_symbol(symbol)

    if db_connection:
        row = _query_instrument(symbol, db_connection)
        if row:
            return _row_to_contract(row)

    return Stock(symbol, "SMART", "USD")


def _parse_qualified_symbol(symbol: str) -> Contract:
    parts = symbol.split(":")
    sec_type = parts[1].upper() if len(parts) > 1 else "STK"
    currency = parts[2] if len(parts) > 2 else "USD"
    exchange = parts[3] if len(parts) > 3 else "SMART"

    if sec_type == "STK":
        return Stock(parts[0], exchange, currency)
    elif sec_type == "CASH":
        return Forex(pair=f"{parts[0]}{currency}")
    elif sec_type == "FUT":
        expiry = parts[4] if len(parts) > 4 else ""
        return Future(parts[0], expiry, exchange, currency)
    elif sec_type == "OPT":
        expiry = parts[4] if len(parts) > 4 else ""
        strike = float(parts[5]) if len(parts) > 5 else 0.0
        right = parts[6] if len(parts) > 6 else "C"
        return Option(parts[0], expiry, strike, right, exchange, currency)
    else:
        return Stock(parts[0], exchange, currency)


def _query_instrument(symbol: str, db_connection: sqlite3.Connection) -> tuple | None:
    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT raw_symbol, instrument_class, currency, exchange,
               expiration, strike_price
        FROM instruments
        WHERE raw_symbol = ?
        ORDER BY expiration DESC
        LIMIT 1
        """,
        (symbol,),
    )
    return cursor.fetchone()


def _row_to_contract(row: tuple) -> Contract:
    raw_symbol, instrument_class, currency, exchange, expiration, strike = row
    currency = currency or "USD"
    exchange = exchange or "SMART"
    sec_type = _INSTRUMENT_CLASS_MAP.get(instrument_class, "STK")

    if sec_type == "STK":
        return Stock(raw_symbol, exchange, currency)
    elif sec_type == "CASH":
        return Forex(pair=f"{raw_symbol}{currency}")
    elif sec_type == "FUT":
        expiry = str(expiration) if expiration else ""
        return Future(raw_symbol, expiry, exchange, currency)
    elif sec_type == "OPT":
        expiry = str(expiration) if expiration else ""
        strike_val = float(strike) / 1e9 if strike else 0.0
        right = "C" if instrument_class == "C" else "P"
        return Option(raw_symbol, expiry, strike_val, right, exchange, currency)
    else:
        return Stock(raw_symbol, exchange, currency)


class IBGateway:
    """
    Shared gateway for IB connectivity with automatic reconnection.

    The gateway manages a single IB connection shared by multiple components
    (datafeed, broker). It handles:

    - Reference counting for connect/disconnect
    - Automatic reconnection on disconnect
    - Running an asyncio event loop in a background thread

    Reconnection Behavior:
        When the connection is lost, the gateway will automatically attempt
        to reconnect after a configurable delay. Components that registered
        reconnect callbacks will be notified after successful reconnection
        so they can restore their subscriptions.

    Environment Variables:
        - ``IB_HOST``: Host address (default: 127.0.0.1)
        - ``IB_PORT``: Port number (default: 4001 for gateway, 7497 for TWS)
        - ``IB_CLIENT_ID``: Client ID (default: 1)
        - ``IB_RECONNECT_DELAY``: Seconds to wait before reconnecting (default: 5)
        - ``IB_MAX_RECONNECT_ATTEMPTS``: Max reconnect attempts, 0=infinite (default: 0)
    """

    def __init__(self) -> None:
        self._host = os.environ.get("IB_HOST", "127.0.0.1")
        self._port = int(os.environ.get("IB_PORT", "4001"))
        self._client_id = int(os.environ.get("IB_CLIENT_ID", "1"))
        self._reconnect_delay = float(os.environ.get("IB_RECONNECT_DELAY", "5"))
        self._max_reconnect_attempts = int(
            os.environ.get("IB_MAX_RECONNECT_ATTEMPTS", "0")
        )
        self._ib = IB()
        self._ref_count = 0
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._reconnect_callbacks: list = []
        self._disconnect_callbacks: list = []
        self._reconnecting = False
        self._should_reconnect = True
        self._reconnect_attempts = 0

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_coro(self, coro):
        if self._loop is None:
            raise RuntimeError("Gateway not connected")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def acquire(self) -> None:
        with self._lock:
            if self._ref_count == 0:
                _logger.info("Connecting to IB at %s:%d", self._host, self._port)
                self._should_reconnect = True
                self._reconnect_attempts = 0
                self._loop_thread = threading.Thread(
                    target=self._run_loop, daemon=True, name="IBGatewayLoop"
                )
                self._loop_thread.start()
                while self._loop is None:
                    time.sleep(0.01)
                self._ib.disconnectedEvent += self._on_disconnected
                self.run_coro(
                    self._ib.connectAsync(
                        self._host, self._port, clientId=self._client_id
                    )
                )
                _logger.info("Connected to IB")
            self._ref_count += 1

    def release(self) -> None:
        with self._lock:
            self._ref_count -= 1
            if self._ref_count == 0:
                _logger.info("Disconnecting from IB")
                self._should_reconnect = False
                self._ib.disconnectedEvent -= self._on_disconnected
                self._ib.disconnect()
                if self._loop:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                if self._loop_thread:
                    self._loop_thread.join()
                self._loop = None
                self._loop_thread = None
                self._reconnect_callbacks.clear()
                self._disconnect_callbacks.clear()
                _logger.info("Disconnected from IB")

    def register_reconnect_callback(self, callback) -> None:
        """
        Register a callback to be called after successful reconnection.

        The callback should restore any subscriptions or state that was lost
        during the disconnect.
        """
        if callback not in self._reconnect_callbacks:
            self._reconnect_callbacks.append(callback)

    def unregister_reconnect_callback(self, callback) -> None:
        if callback in self._reconnect_callbacks:
            self._reconnect_callbacks.remove(callback)

    def register_disconnect_callback(self, callback) -> None:
        """
        Register a callback to be called when disconnection is detected.

        The callback can be used to pause operations or notify the system.
        """
        if callback not in self._disconnect_callbacks:
            self._disconnect_callbacks.append(callback)

    def unregister_disconnect_callback(self, callback) -> None:
        if callback in self._disconnect_callbacks:
            self._disconnect_callbacks.remove(callback)

    def _on_disconnected(self) -> None:
        if not self._should_reconnect or self._reconnecting:
            return

        _logger.warning("IB connection lost")
        for callback in self._disconnect_callbacks:
            try:
                callback()
            except Exception:
                _logger.exception("Error in disconnect callback")

        if self._loop:
            asyncio.run_coroutine_threadsafe(self._reconnect_async(), self._loop)

    async def _reconnect_async(self) -> None:
        if self._reconnecting:
            return
        self._reconnecting = True

        while self._should_reconnect:
            self._reconnect_attempts += 1
            if (
                self._max_reconnect_attempts > 0
                and self._reconnect_attempts > self._max_reconnect_attempts
            ):
                _logger.error(
                    "Max reconnect attempts (%d) reached, giving up",
                    self._max_reconnect_attempts,
                )
                self._reconnecting = False
                return

            _logger.info(
                "Reconnecting to IB (attempt %d) in %.1fs",
                self._reconnect_attempts,
                self._reconnect_delay,
            )
            await asyncio.sleep(self._reconnect_delay)

            if not self._should_reconnect:
                break

            try:
                await self._ib.connectAsync(
                    self._host, self._port, clientId=self._client_id
                )
                _logger.info("Reconnected to IB")
                self._reconnect_attempts = 0
                self._reconnecting = False

                for callback in self._reconnect_callbacks:
                    try:
                        callback()
                    except Exception:
                        _logger.exception("Error in reconnect callback")
                return
            except Exception as e:
                _logger.warning("Reconnect failed: %s", e)
                continue

        self._reconnecting = False

    @property
    def ib(self) -> IB:
        return self._ib

    @property
    def is_connected(self) -> bool:
        return self._ib.isConnected()


_gateway: IBGateway | None = None
_gateway_lock = threading.Lock()


def _get_gateway() -> IBGateway:
    global _gateway
    with _gateway_lock:
        if _gateway is None:
            _gateway = IBGateway()
        return _gateway
