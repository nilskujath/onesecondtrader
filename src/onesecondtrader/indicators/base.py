from __future__ import annotations

import abc
import collections
import threading

import numpy as np

from onesecondtrader import events


class Indicator(abc.ABC):
    def __init__(self, max_history: int = 100, plot_at: int = 99) -> None:
        self._lock = threading.Lock()
        self._max_history = max(1, int(max_history))
        # Keyed by symbol only - each strategy subscribes to one timeframe, so the indicator only sees bars from that timeframe.
        self._history: dict[str, collections.deque[float]] = {}
        # 0 = main price chart, 1-98 = subcharts, 99 = no plot
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
        value = self._compute_indicator(incoming_bar)
        with self._lock:
            if symbol not in self._history:
                self._history[symbol] = collections.deque(maxlen=self._max_history)
            self._history[symbol].append(value)

    def latest(self, symbol: str) -> float:
        with self._lock:
            history = self._history.get(symbol, collections.deque())
            return history[-1] if history else np.nan

    def history(self, symbol: str) -> collections.deque[float]:
        with self._lock:
            h = self._history.get(symbol, collections.deque())
            return collections.deque(h, maxlen=self._max_history)

    @property
    def plot_at(self) -> int:
        return self._plot_at
