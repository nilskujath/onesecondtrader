from __future__ import annotations

from typing import Any

import numpy as np

from onesecondtrader import events, indicators, models


class PeriodExtreme(indicators.IndicatorBase):
    """
    N-Period Extreme indicator.

    Computes the minimum or maximum value of a source indicator over a rolling window of $n$ periods.
    The source indicator is instantiated internally and updated on each bar.

    Until the window is fully populated, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        source: type[indicators.IndicatorBase],
        period: int = 20,
        extreme_type: models.ExtremeType = models.ExtremeType.MAX,
        max_history: int = 100,
        plot_at: int = 0,
        plot_as: models.PlotStyle = models.PlotStyle.LINE,
        plot_color: models.PlotColor = models.PlotColor.BLACK,
        **source_kwargs: Any,
    ) -> None:
        """
        Parameters:
            source:
                Source indicator class to instantiate.
            period:
                Lookback window size.
            extreme_type:
                Whether to compute the minimum or maximum.
            max_history:
                Maximum number of computed indicator values retained per symbol.
            plot_at:
                Opaque plotting identifier forwarded to the charting backend.
            plot_as:
                Visual style used to render the indicator.
            plot_color:
                Color used to render the indicator.
            **source_kwargs:
                Keyword arguments passed to the source indicator constructor.
        """
        super().__init__(
            max_history=max_history,
            plot_at=plot_at,
            plot_as=plot_as,
            plot_color=plot_color,
        )

        self._source = source(max_history=period, **source_kwargs)
        self.period = max(1, int(period))
        self.extreme_type = extreme_type

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Identifier combining source name, period, and extreme type.
        """
        return f"{self.period}-period {self.extreme_type.name} of {self._source.name}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the n-period extreme for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            N-period min or max value, or `numpy.nan` if insufficient data.
        """
        self._source.update(incoming_bar)
        symbol = incoming_bar.symbol

        values = []
        for i in range(-self.period, 0):
            val = self._source[symbol, i]
            if np.isnan(val):
                return np.nan
            values.append(val)

        if self.extreme_type == models.ExtremeType.MIN:
            return min(values)
        return max(values)
