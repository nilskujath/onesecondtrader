"""
This module provides the base class for datafeeds.
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
        Initializes the datafeed with the provided event bus.

        Args:
            event_bus (eventbus.EventBus): The event bus to publish events to.

        Attributes:
            self.event_bus (eventbus.EventBus): The event bus to publish events to.
            self._lock (threading.Lock): Lock for thread safety.
            self._is_connected (bool): Whether the datafeed is connected. `True` if
                  connected, `False` otherwise.
            self._streamed_symbols (set[tuple[str, models.TimeFrame]]): Set of symbols
                 and timeframes that are currently being streamed.
        """
        self.event_bus = event_bus

        self._lock = threading.Lock()
        self._is_connected = False
        self._streamed_symbols: set[tuple[str, models.TimeFrame]] = set()

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
        Clears the set of streamed symbols.

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
                    self._streamed_symbols.clear()
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
                self._streamed_symbols.clear()
                return False

    @abc.abstractmethod
    def _disconnect(self) -> bool:
        """
        Implement disconnection logic for the specific datafeed.

        Returns:
            bool: True if disconnection successful, False otherwise.
        """
        pass

    def start_streaming_for_symbols(
        self, symbols: list[tuple[str, models.TimeFrame]]
    ) -> bool:
        """
        Start streaming market data for the specified symbols and timeframes.

        Args:
            symbols: List of (symbol, timeframe) tuples to start streaming.

        Returns:
            bool: True if streaming started successfully, False otherwise.
        """
        if not symbols:
            console.logger.warning("No symbols provided for streaming")
            return True

        with self._lock:
            if not self._is_connected:
                console.logger.error("Cannot start streaming: datafeed not connected")
                return False

            new_symbols = set(symbols) - self._streamed_symbols
            if not new_symbols:
                console.logger.info("All requested symbols are already being streamed")
                return True

            try:
                success = self._start_streaming_for_symbols(list(new_symbols))
                if success:
                    self._streamed_symbols.update(new_symbols)
                    console.logger.info(
                        f"Successfully started streaming for {len(new_symbols)} symbols"
                    )
                    return True
                else:
                    console.logger.error("Failed to start streaming for symbols")
                    return False
            except Exception as e:
                console.logger.error(f"Exception while starting streaming: {e}")
                return False

    @abc.abstractmethod
    def _start_streaming_for_symbols(
        self, symbols: list[tuple[str, models.TimeFrame]]
    ) -> bool:
        """
        Implement streaming startup logic for the specific datafeed.

        Args:
            symbols: List of (symbol, timeframe) tuples to start streaming.
                    These are guaranteed to be new symbols not already being streamed.

        Returns:
            bool: True if streaming started successfully, False otherwise.
        """
        pass

    def stop_streaming_for_symbols(
        self, symbols: list[tuple[str, models.TimeFrame]]
    ) -> bool:
        """
        Stop streaming market data for the specified symbols and timeframes.

        Args:
            symbols: List of (symbol, timeframe) tuples to stop streaming.

        Returns:
            bool: True if streaming stopped successfully, False otherwise.
        """
        if not symbols:
            console.logger.warning("No symbols provided for stopping streaming")
            return True

        with self._lock:
            if not self._is_connected:
                console.logger.warning(
                    "Datafeed not connected, but removing symbols from tracking"
                )
                self._streamed_symbols.difference_update(symbols)
                return True

            symbols_to_stop = set(symbols) & self._streamed_symbols
            if not symbols_to_stop:
                console.logger.info(
                    "None of the requested symbols are currently being streamed"
                )
                return True

            console.logger.info(
                f"Stopping streaming for {len(symbols_to_stop)} symbols"
            )
            try:
                success = self._stop_streaming_for_symbols(list(symbols_to_stop))
                if success:
                    self._streamed_symbols.difference_update(symbols_to_stop)
                    console.logger.info(
                        f"Successfully stopped streaming for {len(symbols_to_stop)} "
                        f"symbols"
                    )
                    return True
                else:
                    console.logger.error("Failed to stop streaming for symbols")
                    return False
            except Exception as e:
                console.logger.error(f"Exception while stopping streaming: {e}")
                self._streamed_symbols.difference_update(symbols_to_stop)
                return False

    @abc.abstractmethod
    def _stop_streaming_for_symbols(
        self, symbols: list[tuple[str, models.TimeFrame]]
    ) -> bool:
        """
        Implement streaming shutdown logic for the specific datafeed.

        Args:
            symbols: List of (symbol, timeframe) tuples to stop streaming.
                    These are guaranteed to be symbols currently being streamed.

        Returns:
            bool: True if streaming stopped successfully, False otherwise.
        """
        pass

    @abc.abstractmethod
    def preload_bars(
        self, preload_list: list[tuple[str, models.TimeFrame, int]]
    ) -> None:
        """
        Preload historical bars for the specified symbols, timeframes, and counts.

        Args:
            preload_list: List of (symbol, timeframe, count) tuples specifying
                         what historical data to preload.
        """
        pass
