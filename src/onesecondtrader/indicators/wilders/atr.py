from __future__ import annotations

import collections

import numpy as np

from onesecondtrader import events, indicators


def _true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


class ATR(indicators.IndicatorBase):
    """
    Average True Range (ATR) indicator.

    Computes the ATR using Wilder's smoothing method. One scalar value is
    produced per incoming bar and stored per symbol.

    The rolling state is maintained independently for each symbol.
    Until enough bars are received to compute the initial average, the
    indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 14,
        max_history: int = 100,
    ) -> None:
        """
        Parameters:
            period:
                Lookback period for the ATR calculation.
            max_history:
                Maximum number of computed indicator values retained per symbol.
        """
        super().__init__(max_history=max_history)

        self.period: int = max(1, int(period))

        self._prev_close: dict[str, float] = {}
        self._count: dict[str, int] = {}
        self._tr_buffer: dict[str, collections.deque[float]] = {}
        self._atr_value: dict[str, float] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier encoding all configuration parameters.
        """
        return f"ATR_{self.period}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the ATR value for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            ATR value, or `numpy.nan` if not enough data is available.
        """
        symbol = incoming_bar.symbol
        high = incoming_bar.high
        low = incoming_bar.low
        close = incoming_bar.close

        if symbol not in self._prev_close:
            self._prev_close[symbol] = close
            self._count[symbol] = 0
            self._tr_buffer[symbol] = collections.deque()
            self._atr_value[symbol] = 0.0
            return np.nan

        tr = _true_range(high, low, self._prev_close[symbol])
        self._prev_close[symbol] = close

        self._count[symbol] += 1
        count = self._count[symbol]

        if count < self.period:
            self._tr_buffer[symbol].append(tr)
            return np.nan

        if count == self.period:
            self._tr_buffer[symbol].append(tr)
            self._atr_value[symbol] = sum(self._tr_buffer[symbol]) / self.period
            self._tr_buffer[symbol].clear()
            return self._atr_value[symbol]

        self._atr_value[symbol] = (
            self._atr_value[symbol] * (self.period - 1) + tr
        ) / self.period
        return self._atr_value[symbol]
