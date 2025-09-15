"""
This module provides the base class for all indicators.
"""

import abc
import collections
import threading

import numpy as np
from onesecondtrader.core import models
from onesecondtrader.monitoring import console


class BaseIndicator(abc.ABC):
    """
    Base class for all indicators.

    If new market data is received, the indicator is updated by calling the
    `update(incoming_bar)` method.
    When programming a new indicator, only the `name` property and the
    `_compute_indicator()` method need to be implemented.

    Examples:
        >>> from onesecondtrader.indicators import base_indicator
        >>> from onesecondtrader.core import models
        >>> class DummyCloseIndicator(base_indicator.BaseIndicator):
        ...     @property
        ...     def name(self) -> str:
        ...         return "dummy_close_indicator"
        ...     def _compute_indicator(self, incoming_bar: models.Bar):
        ...         return incoming_bar.close
        ...
        >>> dummy_close_indicator = DummyCloseIndicator(max_history=10)
        >>> incoming_bar = models.Bar(
        ...     open=100.0, high=101.0, low=99.0, close=100.5, volume=10000
        ... )
        >>> dummy_close_indicator.update(incoming_bar)
        >>> dummy_close_indicator[0]
        100.5
        >>> dummy_close_indicator[-1]
        nan
        >>> next_incoming_bar = models.Bar(
        ...     open=100.0, high=101.0, low=99.0, close=101.0, volume=10000
        ... )
        >>> dummy_close_indicator.update(next_incoming_bar)
        >>> dummy_close_indicator[0]
        101.0
        >>> dummy_close_indicator[-1]
        100.5
    """

    def __init__(self, max_history: int = 100) -> None:
        """
        Initialize the indicator with a maximum lookback history length.

        Args:
            max_history (int): Maximum lookback history length as number of periods.
            Defaults to 100.

        Attributes:
            self._lock (threading.Lock): Lock to protect concurrent access to the
                indicator's state.
            self._history (collections.deque): Deque to store the lookback history.
        """
        if max_history < 1:
            console.logger.warning(
                f"max_history must be >= 1, got {max_history}; defaulting to 1"
            )
            max_history = 1
        self._lock: threading.Lock = threading.Lock()

        self._history: collections.deque[float] = collections.deque(maxlen=max_history)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Name of the indicator.
        This property must be implemented by subclasses.

        Returns:
            str: Name of the indicator.
        """
        pass

    @property
    def latest(self) -> float:
        """
        The latest (most recent) indicator value.

        Equivalent to self[0]. Returns numpy.nan when no value is available yet.
        """
        return self[0]

    def update(self, incoming_bar: models.Bar) -> None:
        """
        Updates the indicator based on an incoming closed bar by calling
        `self._compute_indicator()`.
        """
        new_value = self._compute_indicator(incoming_bar)
        with self._lock:
            self._history.append(new_value)

    @abc.abstractmethod
    def _compute_indicator(self, incoming_bar: models.Bar) -> float:
        """
        Computes the new indicator value based on an incoming closed bar.
        This method must be implemented by subclasses.
        """
        pass

    def __getitem__(self, index: int) -> float:
        """
        Return the indicator value at the given index with tolerant indexing.

        Indexing rules:

        - `0` returns the current (most recent) value
        - `-1` returns the previous value, `-2` two periods back, and so on
        - For convenience, a positive `k` behaves like `-k` (e.g., `1 == -1`,
          `2 == -2`)
        - Out-of-range indices return `np.nan` instead of raising an `IndexError`.
        """
        normalized: int
        if index == 0:
            normalized = -1
        elif index > 0:
            normalized = -(index + 1)
        else:
            normalized = index - 1

        with self._lock:
            try:
                return self._history[normalized]
            except IndexError:
                return np.nan
