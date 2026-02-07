from __future__ import annotations

import collections
import numpy as np

from onesecondtrader import events, indicators, models


class DetrendOscillator(indicators.IndicatorBase):
    """
    Detrend Oscillator indicator.

    Measures the spread between two smoothed price estimates (short and long horizon moving averages):
    Detrend(t) = SMA_short(t) - SMA_long(t)

    This construction removes the slow-moving trend component and leaves a zero-centered oscillation.

    The rolling windows are maintained independently for each symbol.
    Until both windows are fully populated, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        short_period: int = 3,
        long_period: int = 7,
        max_history: int = 100,
        bar_field: models.BarField = models.BarField.CLOSE,
    ) -> None:
        """
        Parameters:
            short_period:
                Window size for the short-horizon moving average.
            long_period:
                Window size for the long-horizon moving average.
            max_history:
                Maximum number of computed indicator values retained per symbol.
            bar_field:
                Bar field used as the input series.
        """
        super().__init__(max_history=max_history)

        self.short_period: int = max(1, int(short_period))
        self.long_period: int = max(1, int(long_period))
        self.bar_field: models.BarField = bar_field
        self._short_window: dict[str, collections.deque[float]] = {}
        self._long_window: dict[str, collections.deque[float]] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier for the Detrend Oscillator.
        """
        return f"DETREND({self.short_period},{self.long_period})"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the detrend oscillator for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            Detrend oscillator value, or `numpy.nan` if the rolling windows are not yet fully populated.
        """
        symbol = incoming_bar.symbol
        if symbol not in self._short_window:
            self._short_window[symbol] = collections.deque(maxlen=self.short_period)
        if symbol not in self._long_window:
            self._long_window[symbol] = collections.deque(maxlen=self.long_period)

        value = self._extract_field(incoming_bar)
        self._short_window[symbol].append(value)
        self._long_window[symbol].append(value)

        if len(self._short_window[symbol]) < self.short_period:
            return np.nan
        if len(self._long_window[symbol]) < self.long_period:
            return np.nan

        sma_short = sum(self._short_window[symbol]) / self.short_period
        sma_long = sum(self._long_window[symbol]) / self.long_period

        return sma_short - sma_long

    def _extract_field(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Extract the configured bar field from an incoming bar.

        Parameters:
            incoming_bar:
                Market bar providing the input data.

        Returns:
            Extracted field value, or `numpy.nan` if unavailable.
        """
        match self.bar_field:
            case models.BarField.OPEN:
                return incoming_bar.open
            case models.BarField.HIGH:
                return incoming_bar.high
            case models.BarField.LOW:
                return incoming_bar.low
            case models.BarField.CLOSE:
                return incoming_bar.close
            case models.BarField.VOLUME:
                return (
                    float(incoming_bar.volume)
                    if incoming_bar.volume is not None
                    else np.nan
                )
            case _:
                return incoming_bar.close
