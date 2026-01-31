from __future__ import annotations

import collections
import numpy as np

from onesecondtrader import events, indicators, models


class SimpleMovingAverage(indicators.IndicatorBase):
    """
    Simple Moving Average (SMA) indicator.

    This indicator computes the arithmetic mean of a selected bar field over a fixed rolling window.
    One scalar value is produced per incoming bar and stored per symbol.

    The rolling window is maintained independently for each symbol.
    Until the window is fully populated, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 200,
        max_history: int = 100,
        bar_field: models.BarField = models.BarField.CLOSE,
        plot_at: int = 0,
    ) -> None:
        """
        Parameters:
            period:
                Window size used to compute the moving average.
            max_history:
                Maximum number of computed indicator values retained per symbol.
            bar_field:
                Bar field used as the input series.
            plot_at:
                Opaque plotting identifier forwarded to the charting backend.
        """
        super().__init__(max_history=max_history, plot_at=plot_at)

        self.period: int = max(1, int(period))
        self.bar_field: models.BarField = bar_field
        self._window: dict[str, collections.deque[float]] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Identifier encoding the indicator type, period, and bar field.
        """
        return f"SMA_{self.period}_{self.bar_field.name}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the simple moving average for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            Simple moving average value, or `numpy.nan` if the rolling window is not yet fully populated.
        """
        symbol = incoming_bar.symbol
        if symbol not in self._window:
            self._window[symbol] = collections.deque(maxlen=self.period)

        window = self._window[symbol]
        value = self._extract_field(incoming_bar)
        window.append(value)

        if len(window) < self.period:
            return np.nan
        return sum(window) / self.period

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
