from __future__ import annotations

import abc
import collections
import threading

import numpy as np

from onesecondtrader import events


class IndicatorBase(abc.ABC):
    """
    Base class for scalar technical indicators with per-symbol history.

    The class provides a thread-safe mechanism for storing and retrieving indicator values computed from incoming market bars, keyed by symbol.
    It does not manage input windows or rolling computation state.

    Subclasses define a stable indicator identifier via the `name` property and implement `_compute_indicator`, which computes a single scalar value per incoming bar.
    Indicators with multiple conceptual outputs must be implemented as multiple single-output indicators (e.g. Bollinger Bands must be implemented via three separate indicators `BBUpper`, `BBMiddle`, and `BBLower`).

    The update mechanism is thread-safe.
    Indicator computation is performed outside the internal lock.
    Subclasses that maintain internal state are responsible for ensuring its thread safety and must not access `_history_data`.

    Indicator values are stored per symbol in bounded FIFO buffers.
    Missing data and out-of-bounds access yield `numpy.nan`.

    The `plot_at` attribute is an opaque identifier forwarded to the charting backend and has no intrinsic meaning within the indicator subsystem.
    """

    def __init__(self, max_history: int = 100, plot_at: int = 99) -> None:
        """
        Parameters:
            max_history:
                Maximum number of indicator values retained per symbol.
                Cannot be less than 1.
            plot_at:
                Opaque plotting identifier forwarded to the charting backend.
        """
        self._lock = threading.Lock()
        self._max_history = max(1, int(max_history))
        self._history_data: dict[str, collections.deque[float]] = {}
        self._plot_at = plot_at

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier used for charting and downstream integration.
        """
        pass

    @abc.abstractmethod
    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the indicator value for a single market bar.

        This method is executed outside the internal lock.
        Implementations must not access `_history_data` and must ensure thread safety of any internal computation state.

        Parameters:
            incoming_bar:
                Market bar used as input for indicator computation.

        Returns:
            Computed indicator value.
        """
        pass

    def update(self, incoming_bar: events.market.BarReceived) -> None:
        """
        Update the indicator with a new market bar.

        The computed value is appended to the per-symbol history buffer.

        Parameters:
            incoming_bar:
                Market bar triggering the update.
        """
        symbol = incoming_bar.symbol

        value = self._compute_indicator(incoming_bar)

        with self._lock:
            if symbol not in self._history_data:
                self._history_data[symbol] = collections.deque(maxlen=self._max_history)

            self._history_data[symbol].append(value)

    def latest(self, symbol: str) -> float:
        """
        Return the most recent indicator value for a symbol.

        Parameters:
            symbol:
                Symbol identifier.

        Returns:
            Most recent value, or `numpy.nan` if unavailable.
        """
        return self[symbol, -1]

    def __getitem__(self, key: tuple[str, int]) -> float:
        """
        Retrieve an indicator value by symbol and index.

        Indexing follows standard Python sequence semantics.
        Negative indices refer to positions relative to the most recent value.

        Parameters:
            key:
                `(symbol, index)` pair specifying the symbol and history offset.

        Returns:
            Indicator value at the specified position, or `numpy.nan` if unavailable.
        """
        symbol, index = key

        with self._lock:
            history = self._history_data.get(symbol)

            if history is None:
                return np.nan

            try:
                return history[index]
            except IndexError:
                return np.nan

    @property
    def plot_at(self) -> int:
        """
        Plotting identifier.

        Returns:
            Opaque identifier consumed by the charting backend.
        """
        return self._plot_at
