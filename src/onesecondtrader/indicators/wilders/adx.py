from __future__ import annotations

import numpy as np

from onesecondtrader import events, indicators, models


def _true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _directional_movement(
    high: float, low: float, prev_high: float, prev_low: float
) -> tuple[float, float]:
    up_move = high - prev_high
    down_move = prev_low - low
    plus_dm = up_move if up_move > down_move and up_move > 0.0 else 0.0
    minus_dm = down_move if down_move > up_move and down_move > 0.0 else 0.0
    return plus_dm, minus_dm


class ADX(indicators.IndicatorBase):
    """
    Average Directional Index (ADX) indicator.

    Computes both +DI and -DI internally, derives DX, then Wilder-smooths DX
    to produce the ADX. One scalar value in the range 0-100 is produced per
    incoming bar and stored per symbol.

    The rolling state is maintained independently for each symbol.
    Until enough bars are received, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 14,
        max_history: int = 100,
        plot_at: int = 1,
        plot_as: models.PlotStyle = models.PlotStyle.LINE,
        plot_color: models.PlotColor = models.PlotColor.BLACK,
    ) -> None:
        """
        Parameters:
            period:
                Lookback period for the ADX calculation.
            max_history:
                Maximum number of computed indicator values retained per symbol.
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

        self._prev_high: dict[str, float] = {}
        self._prev_low: dict[str, float] = {}
        self._prev_close: dict[str, float] = {}
        self._count: dict[str, int] = {}
        self._plus_dm_sum: dict[str, float] = {}
        self._minus_dm_sum: dict[str, float] = {}
        self._tr_sum: dict[str, float] = {}
        self._smoothed_plus_dm: dict[str, float] = {}
        self._smoothed_minus_dm: dict[str, float] = {}
        self._smoothed_tr: dict[str, float] = {}
        self._dx_sum: dict[str, float] = {}
        self._dx_count: dict[str, int] = {}
        self._adx_value: dict[str, float] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier encoding all configuration parameters.
        """
        return f"ADX_{self.period}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the ADX value for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            ADX value (0-100), or `numpy.nan` if not enough data is available.
        """
        symbol = incoming_bar.symbol
        high = incoming_bar.high
        low = incoming_bar.low
        close = incoming_bar.close

        if symbol not in self._prev_close:
            self._prev_high[symbol] = high
            self._prev_low[symbol] = low
            self._prev_close[symbol] = close
            self._count[symbol] = 0
            self._plus_dm_sum[symbol] = 0.0
            self._minus_dm_sum[symbol] = 0.0
            self._tr_sum[symbol] = 0.0
            self._smoothed_plus_dm[symbol] = 0.0
            self._smoothed_minus_dm[symbol] = 0.0
            self._smoothed_tr[symbol] = 0.0
            self._dx_sum[symbol] = 0.0
            self._dx_count[symbol] = 0
            self._adx_value[symbol] = 0.0
            return np.nan

        tr = _true_range(high, low, self._prev_close[symbol])
        plus_dm, minus_dm = _directional_movement(
            high, low, self._prev_high[symbol], self._prev_low[symbol]
        )

        self._prev_high[symbol] = high
        self._prev_low[symbol] = low
        self._prev_close[symbol] = close

        self._count[symbol] += 1
        count = self._count[symbol]

        # Phase 1: accumulate raw sums for the first period
        if count < self.period:
            self._plus_dm_sum[symbol] += plus_dm
            self._minus_dm_sum[symbol] += minus_dm
            self._tr_sum[symbol] += tr
            return np.nan

        # Phase 2: compute smoothed DI values
        if count == self.period:
            self._smoothed_plus_dm[symbol] = self._plus_dm_sum[symbol] + plus_dm
            self._smoothed_minus_dm[symbol] = self._minus_dm_sum[symbol] + minus_dm
            self._smoothed_tr[symbol] = self._tr_sum[symbol] + tr
        else:
            self._smoothed_plus_dm[symbol] = (
                self._smoothed_plus_dm[symbol]
                - self._smoothed_plus_dm[symbol] / self.period
                + plus_dm
            )
            self._smoothed_minus_dm[symbol] = (
                self._smoothed_minus_dm[symbol]
                - self._smoothed_minus_dm[symbol] / self.period
                + minus_dm
            )
            self._smoothed_tr[symbol] = (
                self._smoothed_tr[symbol] - self._smoothed_tr[symbol] / self.period + tr
            )

        smoothed_tr = self._smoothed_tr[symbol]
        if smoothed_tr <= 1e-12:
            plus_di = 0.0
            minus_di = 0.0
        else:
            plus_di = 100.0 * self._smoothed_plus_dm[symbol] / smoothed_tr
            minus_di = 100.0 * self._smoothed_minus_dm[symbol] / smoothed_tr

        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100.0 if di_sum > 1e-12 else 0.0

        # Phase 3: accumulate DX values for ADX
        self._dx_count[symbol] += 1
        dx_count = self._dx_count[symbol]

        if dx_count < self.period:
            self._dx_sum[symbol] += dx
            return np.nan

        if dx_count == self.period:
            self._adx_value[symbol] = (self._dx_sum[symbol] + dx) / self.period
            return self._adx_value[symbol]

        self._adx_value[symbol] = (
            self._adx_value[symbol] * (self.period - 1) + dx
        ) / self.period
        return self._adx_value[symbol]
