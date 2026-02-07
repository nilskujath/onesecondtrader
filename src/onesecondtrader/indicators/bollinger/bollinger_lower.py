from __future__ import annotations

import collections
import numpy as np

from onesecondtrader import events, indicators, models


class BollingerLower(indicators.IndicatorBase):
    """
    Bollinger Lower Band indicator.

    Computes the lower Bollinger Band as: SMA - ($k$ * standard deviation)
    where $k$ is the number of standard deviations (default 2).

    The rolling window is maintained independently for each symbol.
    Until the window is fully populated, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 20,
        num_std: float = 2.0,
        max_history: int = 100,
        bar_field: models.BarField = models.BarField.CLOSE,
        plot_at: int = 0,
        plot_as: models.PlotStyle = models.PlotStyle.LINE,
        plot_color: models.PlotColor = models.PlotColor.BLACK,
        plot_width: models.PlotWidth = models.PlotWidth.NORMAL,
    ) -> None:
        """
        Parameters:
            period:
                Window size used to compute the moving average and standard deviation.
            num_std:
                Number of standard deviations for the band offset.
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
            plot_width:
                Width/thickness used to render the indicator.
        """
        super().__init__(
            max_history=max_history,
            plot_at=plot_at,
            plot_as=plot_as,
            plot_color=plot_color,
            plot_width=plot_width,
        )

        self.period: int = max(1, int(period))
        self.num_std: float = float(num_std)
        self.bar_field: models.BarField = bar_field
        self._window: dict[str, collections.deque[float]] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Identifier encoding the indicator type, period, number of standard deviations, and bar field.
        """
        return f"BB_LOWER_{self.period}_{self.num_std}_{self.bar_field.name}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the lower Bollinger Band for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            Lower Bollinger Band value, or `numpy.nan` if the rolling window is not yet fully populated.
        """
        symbol = incoming_bar.symbol
        if symbol not in self._window:
            self._window[symbol] = collections.deque(maxlen=self.period)

        window = self._window[symbol]
        value = self._extract_field(incoming_bar)
        window.append(value)

        if len(window) < self.period:
            return np.nan

        mean = sum(window) / self.period
        variance = sum((x - mean) ** 2 for x in window) / self.period
        std = np.sqrt(variance)

        return mean - (self.num_std * std)

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
