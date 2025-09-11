"""
This module provides the base class for all datafeeds.
"""

import abc
import threading
from onesecondtrader.messaging import eventbus
from onesecondtrader.core import models
from onesecondtrader.monitoring import console


class BaseDatafeed(abc.ABC):
    """
    Base class for all datafeeds.
    """

    def __init__(self, event_bus: eventbus.EventBus) -> None:
        """
        Initialize the datafeed with the provided event bus.

        Args:
            event_bus: The event bus to publish events to.

        Attributes:
            self.event_bus: The event bus to publish events to.
            self._lock: Lock for thread safety.
            self._is_connected: Flag indicating if the datafeed is connected.
            self._watched_symbols: Set of symbols currently being watched.
        """
        self.event_bus = event_bus
        self._lock = threading.Lock()
        self._is_connected = False
        self._watched_symbols: set[tuple[str, models.TimeFrame]] = set()

    def connect(self) -> bool:
        """
        Connect to the datafeed.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        with self._lock:
            if self._is_connected:
                console.logger.warning(f"{self.__class__.__name__} already connected")
                return True

            console.logger.info(f"Connecting to {self.__class__.__name__}...")
            try:
                success = self._connect()
                if success:
                    self._is_connected = True
                    console.logger.info(
                        f"Successfully connected to {self.__class__.__name__}"
                    )
                    return True
                else:
                    console.logger.error(
                        f"Failed to connect to {self.__class__.__name__}"
                    )
                    return False
            except Exception as e:
                console.logger.error(
                    f"Connection failed for {self.__class__.__name__}: {e}"
                )
                return False

    @abc.abstractmethod
    def _connect(self) -> bool:
        """
        Implement connection logic for the specific datafeed.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        pass

    def disconnect(self) -> bool:
        """
        Disconnect from the datafeed.

        Returns:
            bool: True if disconnection successful, False otherwise.
        """
        with self._lock:
            if not self._is_connected:
                console.logger.warning(
                    f"{self.__class__.__name__} already disconnected"
                )
                return True

            console.logger.info(f"Disconnecting from {self.__class__.__name__}...")
            try:
                success = self._disconnect()
                if success:
                    self._is_connected = False
                    self._watched_symbols.clear()
                    console.logger.info(
                        f"Successfully disconnected from {self.__class__.__name__}"
                    )
                    return True
                else:
                    console.logger.error(
                        f"Failed to disconnect from {self.__class__.__name__}"
                    )
                    return False
            except Exception as e:
                console.logger.error(
                    f"Disconnection failed for {self.__class__.__name__}: {e}"
                )
                self._is_connected = False
                self._watched_symbols.clear()
                return False

    @abc.abstractmethod
    def _disconnect(self) -> bool:
        """
        Implement disconnection logic for the specific datafeed.

        Returns:
            bool: True if disconnection successful, False otherwise.
        """
        pass

    def watch(self, symbols: list[tuple[str, models.TimeFrame]]) -> bool:
        """
        Start watching market data for the specified symbols and timeframes.

        Args:
            symbols: List of (symbol, timeframe) tuples to start watching.

        Returns:
            bool: True if watching started successfully, False otherwise.
        """
        if not symbols:
            console.logger.warning("No symbols provided for watching")
            return True

        with self._lock:
            if not self._is_connected:
                console.logger.error("Cannot start watching: datafeed not connected")
                return False

            new_symbols = set(symbols) - self._watched_symbols
            if not new_symbols:
                console.logger.info("All requested symbols are already being watched")
                return True

            try:
                success = self._watch(list(new_symbols))
                if success:
                    self._watched_symbols.update(new_symbols)
                    console.logger.info(
                        f"Successfully started watching {len(new_symbols)} symbols"
                    )
                    return True
                else:
                    console.logger.error("Failed to start watching symbols")
                    return False
            except Exception as e:
                console.logger.error(f"Exception while starting watching: {e}")
                return False

    @abc.abstractmethod
    def _watch(self, symbols: list[tuple[str, models.TimeFrame]]) -> bool:
        """
        Implement watching startup logic for the specific datafeed.

        Args:
            symbols: List of (symbol, timeframe) tuples to start watching.
                    These are guaranteed to be new symbols not already being watched.

        Returns:
            bool: True if watching started successfully, False otherwise.
        """
        pass

    def unwatch(self, symbols: list[tuple[str, models.TimeFrame]]) -> bool:
        """
        Stop watching market data for the specified symbols and timeframes.

        Args:
            symbols: List of (symbol, timeframe) tuples to stop watching.

        Returns:
            bool: True if unwatching stopped successfully, False otherwise.
        """
        if not symbols:
            console.logger.warning("No symbols provided for unwatching")
            return True

        with self._lock:
            if not self._is_connected:
                console.logger.warning(
                    "Datafeed not connected, but removing symbols from tracking"
                )
                self._watched_symbols.difference_update(symbols)
                return True

            symbols_to_stop = set(symbols) & self._watched_symbols
            if not symbols_to_stop:
                console.logger.info(
                    "None of the requested symbols are currently being watched"
                )
                return True

            console.logger.info(f"Unwatching {len(symbols_to_stop)} symbols")
            try:
                success = self._unwatch(list(symbols_to_stop))
                if success:
                    self._watched_symbols.difference_update(symbols_to_stop)
                    console.logger.info(
                        f"Successfully unwatched {len(symbols_to_stop)} symbols"
                    )
                    return True
                else:
                    console.logger.error("Failed to unwatch symbols")
                    return False
            except Exception as e:
                console.logger.error(f"Exception while unwatching: {e}")
                self._watched_symbols.difference_update(symbols_to_stop)
                return False

    @abc.abstractmethod
    def _unwatch(self, symbols: list[tuple[str, models.TimeFrame]]) -> bool:
        """
        Implement unwatching logic for the specific datafeed.

        Args:
            symbols: List of (symbol, timeframe) tuples to stop watching.
                    These are guaranteed to be symbols currently being watched.

        Returns:
            bool: True if unwatching stopped successfully, False otherwise.
        """
        pass

    def is_connected(self) -> bool:
        """
        Check if the datafeed is currently connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        with self._lock:
            return self._is_connected

    def get_watched_symbols(self) -> set[tuple[str, models.TimeFrame]]:
        """
        Get the set of currently watched symbols and timeframes.

        Returns:
            set: Set of (symbol, timeframe) tuples currently being watched.
        """
        with self._lock:
            return self._watched_symbols.copy()
