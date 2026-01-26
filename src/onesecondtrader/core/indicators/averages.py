from __future__ import annotations

import collections

import numpy as np

from onesecondtrader.core import events, models
from .base import Indicator


class SimpleMovingAverage(Indicator):
    def __init__(
        self,
        period: int = 200,
        max_history: int = 100,
        input_source: models.InputSource = models.InputSource.CLOSE,
        plot_at: int = 0,
    ) -> None:
        super().__init__(max_history=max_history, plot_at=plot_at)
        self.period: int = max(1, int(period))
        self.input_source: models.InputSource = input_source
        self._window: dict[str, collections.deque[float]] = {}

    @property
    def name(self) -> str:
        return f"SMA_{self.period}_{self.input_source.name}"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        symbol = incoming_bar.symbol
        if symbol not in self._window:
            self._window[symbol] = collections.deque(maxlen=self.period)
        window = self._window[symbol]
        value = self._extract_input(incoming_bar)
        window.append(value)
        if len(window) < self.period:
            return np.nan
        return sum(window) / self.period

    def _extract_input(self, incoming_bar: events.BarReceived) -> float:
        match self.input_source:
            case models.InputSource.OPEN:
                return incoming_bar.open
            case models.InputSource.HIGH:
                return incoming_bar.high
            case models.InputSource.LOW:
                return incoming_bar.low
            case models.InputSource.CLOSE:
                return incoming_bar.close
            case models.InputSource.VOLUME:
                return (
                    float(incoming_bar.volume)
                    if incoming_bar.volume is not None
                    else np.nan
                )
            case _:
                return incoming_bar.close
