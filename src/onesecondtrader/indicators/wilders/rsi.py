from __future__ import annotations

import numpy as np

from onesecondtrader import events, indicators, models


class RSI(indicators.IndicatorBase):
    """
    Relative Strength Index (RSI) indicator.

    This indicator computes the RSI using Wilder's smoothing method with $\\alpha = 1 / period$.
    One scalar value in the range 0-100 is produced per incoming bar and stored per symbol.

    The rolling state is maintained independently for each symbol.
    Until enough bars are received to compute the initial average, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        period: int = 14,
        max_history: int = 100,
        bar_field: models.BarField = models.BarField.CLOSE,
    ) -> None:
        """
        Parameters:
            period:
                Lookback period for the RSI calculation.
            max_history:
                Maximum number of computed indicator values retained per symbol.
            bar_field:
                Bar field used as the input series.
        """
        super().__init__(max_history=max_history)

        self.period: int = max(1, int(period))
        self.bar_field: models.BarField = bar_field

        self._prev_price: dict[str, float] = {}
        self._count: dict[str, int] = {}
        self._avg_gain: dict[str, float] = {}
        self._avg_loss: dict[str, float] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier encoding all configuration parameters.
        """
        return f"RSI_{self.period}_{self.bar_field.name}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the RSI value for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            RSI value (0-100), or `numpy.nan` if not enough data is available.
        """
        symbol = incoming_bar.symbol
        price = self._extract_field(incoming_bar)

        if not np.isfinite(price):
            return np.nan

        if symbol not in self._prev_price:
            self._prev_price[symbol] = price
            self._count[symbol] = 0
            self._avg_gain[symbol] = 0.0
            self._avg_loss[symbol] = 0.0
            return np.nan

        change = price - self._prev_price[symbol]
        self._prev_price[symbol] = price

        gain = change if change > 0.0 else 0.0
        loss = -change if change < 0.0 else 0.0

        self._count[symbol] += 1
        count = self._count[symbol]

        if count < self.period:
            self._avg_gain[symbol] += gain
            self._avg_loss[symbol] += loss
            return np.nan

        if count == self.period:
            self._avg_gain[symbol] = (self._avg_gain[symbol] + gain) / self.period
            self._avg_loss[symbol] = (self._avg_loss[symbol] + loss) / self.period
        else:
            alpha = 1.0 / self.period
            self._avg_gain[symbol] = (1.0 - alpha) * self._avg_gain[
                symbol
            ] + alpha * gain
            self._avg_loss[symbol] = (1.0 - alpha) * self._avg_loss[
                symbol
            ] + alpha * loss

        avg_gain = self._avg_gain[symbol]
        avg_loss = self._avg_loss[symbol]

        eps = 1e-12
        if avg_loss <= eps:
            return 100.0 if avg_gain > eps else 50.0

        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

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
