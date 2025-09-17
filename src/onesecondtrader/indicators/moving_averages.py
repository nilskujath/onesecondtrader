"""
This module provides various moving average indicators.
"""

import numpy as np
import collections
from onesecondtrader.indicators import base_indicator
from onesecondtrader.core import models
from onesecondtrader.monitoring import console


class SimpleMovingAverage(base_indicator.BaseIndicator):
    """
    Simple Moving Average (SMA) indicator for different OHLC-data related time series,
     the possible modes for the SMA calculation are indicated in the
     `core.models.XMAMode` enum (currently: `open`, `high`, `low`, `close`,
     `typical_price`, `weighted close`).

    Examples:
        >>> from onesecondtrader.indicators import moving_averages
        >>> from onesecondtrader.core import models
        >>> sma = moving_averages.SimpleMovingAverage(
        ...     period=3, mode=models.XMAMode.CLOSE
        ... )
        >>> bar1 = models.Bar(
        ...     open=100.0, high=101.0, low=99.0, close=100.0, volume=1000
        ... )
        >>> sma.update(bar1)
        >>> import numpy as np
        >>> np.isnan(sma.latest)
        True
        >>> bar2 = models.Bar(
        ...     open=100.0, high=102.0, low=100.0, close=101.0, volume=1500
        ... )
        >>> sma.update(bar2)
        >>> np.isnan(sma.latest)
        True
        >>> bar3 = models.Bar(
        ...     open=101.0, high=103.0, low=101.0, close=102.0, volume=2000
        ... )
        >>> sma.update(bar3)
        >>> np.isnan(sma.latest)
        False
        >>> sma.latest
        101.0
    """

    def __init__(
        self,
        period: int,
        mode: models.XMAMode = models.XMAMode.CLOSE,
        max_history: int = 100,
    ) -> None:
        """
        Initialize the indicator with a period and a mode.

        Args:
            period (int): Period of the moving average. Will be set to 1 if < 1.
            mode (models.XMAMode): Mode of the moving average. Defaults to `CLOSE`.
            max_history (int): Maximum lookback history length. Defaults to 100.

        Attributes:
            self.period (int): Period of the moving average.
            self.mode (models.XMAMode): Mode of the moving average.
        """
        if period < 1:
            console.logger.warning(
                f"Period must be >= 1, got {period}; defaulting to 1"
            )
            period = 1

        super().__init__(max_history=max_history)
        self.period: int = period
        self.mode: models.XMAMode = mode
        self._window: collections.deque[float] = collections.deque(maxlen=self.period)

    @property
    def name(self) -> str:
        return f"SMA_{self.period}_{self.mode.name}"

    def _compute_indicator(self, incoming_bar: models.Bar) -> float:
        """
        Compute the specified simple moving average based on the incoming bar.

        Args:
            incoming_bar (models.Bar): Incoming bar with OHLCV data.

        Returns:
            float: Simple moving average value, or np.nan if insufficient data or
                errors occur.
        """
        try:
            mode = self.mode
            if mode is models.XMAMode.OPEN:
                current_value = incoming_bar.open
            elif mode is models.XMAMode.HIGH:
                current_value = incoming_bar.high
            elif mode is models.XMAMode.LOW:
                current_value = incoming_bar.low
            elif mode is models.XMAMode.CLOSE:
                current_value = incoming_bar.close
            elif mode is models.XMAMode.TYPICAL_PRICE:
                current_value = (
                    incoming_bar.high + incoming_bar.low + incoming_bar.close
                ) / 3.0
            elif mode is models.XMAMode.WEIGHTED_CLOSE:
                current_value = (
                    incoming_bar.high + incoming_bar.low + 2.0 * incoming_bar.close
                ) / 4.0
            else:
                console.logger.warning(
                    f"Unsupported XMAMode: {mode}; using close price"
                )
                current_value = incoming_bar.close

            if not np.isfinite(current_value):
                console.logger.warning(
                    f"Invalid value extracted: {current_value} (mode={mode.name}); "
                    f"using np.nan"
                )
                return np.nan

            with self._lock:
                self._window.append(current_value)
                if len(self._window) < self.period:
                    return np.nan
                sma_value = sum(self._window) / self.period
            return sma_value

        except Exception as e:
            console.logger.warning(f"SMA calculation failed: {e}; returning np.nan")
            return np.nan
