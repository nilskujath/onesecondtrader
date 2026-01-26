from __future__ import annotations

import abc
import collections
import threading

import numpy as np

from onesecondtrader.core import events


class Indicator(abc.ABC):
    def __init__(self, max_history: int = 100, plot_at: int = 99) -> None:
        self._lock = threading.Lock()
        self._max_history = max(1, int(max_history))
        self._current_symbol: str = ""
        self._history_data: dict[str, collections.deque[float]] = {}
        self._plot_at = plot_at

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        pass

    def update(self, incoming_bar: events.BarReceived) -> None:
        symbol = incoming_bar.symbol
        self._current_symbol = symbol
        value = self._compute_indicator(incoming_bar)
        with self._lock:
            if symbol not in self._history_data:
                self._history_data[symbol] = collections.deque(maxlen=self._max_history)
            self._history_data[symbol].append(value)

    @property
    def latest(self) -> float:
        with self._lock:
            h = self._history_data.get(self._current_symbol, collections.deque())
            return h[-1] if h else np.nan

    @property
    def history(self) -> collections.deque[float]:
        with self._lock:
            h = self._history_data.get(self._current_symbol, collections.deque())
            return collections.deque(h, maxlen=self._max_history)

    def __getitem__(self, index: int) -> float:
        # Returns np.nan on out-of-bounds access. Since np.nan comparisons always
        # return False, strategies can skip explicit length checks.
        try:
            return self.history[index]
        except IndexError:
            return np.nan

    @property
    def plot_at(self) -> int:
        return self._plot_at
