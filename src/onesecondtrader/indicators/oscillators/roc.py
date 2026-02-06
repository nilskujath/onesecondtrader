from __future__ import annotations

import collections
import numpy as np

from onesecondtrader import events, indicators, models


class ROC(indicators.IndicatorBase):
    """
    Rate of Change (ROC) indicator.

    Computes the percentage change between the current value and the value $n$ periods ago:
    ROC = ((current - previous) / previous) * 100

    The rolling window is maintained independently for each symbol.
    Until the window is fully populated, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 14,
        max_history: int = 100,
        bar_field: models.BarField = models.BarField.CLOSE,
        plot_at: int = 99,
        plot_as: models.PlotStyle = models.PlotStyle.LINE,
        plot_color: models.PlotColor = models.PlotColor.BLACK,
    ) -> None:
        """
        Parameters:
            period:
                Number of periods to look back for the rate of change calculation.
            max_history:
                Maximum number of computed indicator values retained per symbol.
            bar_field:
                Bar field used as the input series.
            plot_at:
                Opaque plotting identifier forwarded to the charting backend.
            plot_as:
                Visual style used to render the indicator.
            plot_color:
                Color used to render the indicator.
        """
        super().__init__(
            max_history=max_history,
            plot_at=plot_at,
            plot_as=plot_as,
            plot_color=plot_color,
        )

        self.period: int = max(1, int(period))
        self.bar_field: models.BarField = bar_field
        self._window: dict[str, collections.deque[float]] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier for the ROC indicator.
        """
        return f"ROC({self.period})"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the rate of change for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            Rate of change value as a percentage, or `numpy.nan` if the rolling window is not yet fully populated.
        """
        symbol = incoming_bar.symbol
        if symbol not in self._window:
            self._window[symbol] = collections.deque(maxlen=self.period + 1)

        window = self._window[symbol]
        value = self._extract_field(incoming_bar)
        window.append(value)

        if len(window) < self.period + 1:
            return np.nan

        previous = window[0]
        if previous == 0:
            return np.nan

        return ((value - previous) / previous) * 100

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
