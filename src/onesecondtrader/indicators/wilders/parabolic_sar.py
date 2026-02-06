from __future__ import annotations

import collections
import dataclasses

import numpy as np

from onesecondtrader import events, indicators, models


@dataclasses.dataclass
class _SARState:
    """Per-symbol mutable state for the Parabolic SAR computation."""

    count: int = 0
    is_long: bool = True
    sar: float = 0.0
    ep: float = 0.0
    af: float = 0.0
    high_buffer: collections.deque[float] = dataclasses.field(
        default_factory=lambda: collections.deque(maxlen=2)
    )
    low_buffer: collections.deque[float] = dataclasses.field(
        default_factory=lambda: collections.deque(maxlen=2)
    )


class ParabolicSAR(indicators.IndicatorBase):
    """
    Parabolic Stop and Reverse (SAR) indicator.

    Computes the Parabolic SAR as described by J. Welles Wilder Jr. One scalar
    value is produced per incoming bar and stored per symbol.

    The rolling state is maintained independently for each symbol.
    Until enough bars are received to initialise, the indicator yields `numpy.nan`.
    """

    def __init__(
        self,
        af_start: float = 0.02,
        af_step: float = 0.02,
        af_max: float = 0.20,
        max_history: int = 100,
        plot_at: int = 0,
        plot_as: models.PlotStyle = models.PlotStyle.DOTS,
        plot_color: models.PlotColor = models.PlotColor.BLACK,
    ) -> None:
        """
        Parameters:
            af_start:
                Initial acceleration factor.
            af_step:
                Acceleration factor increment when a new extreme point is reached.
            af_max:
                Maximum acceleration factor.
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

        self.af_start: float = af_start
        self.af_step: float = af_step
        self.af_max: float = af_max

        self._state: dict[str, _SARState] = {}

    @property
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier encoding all configuration parameters.
        """
        return f"PSAR_{self.af_start}_{self.af_step}_{self.af_max}"

    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the Parabolic SAR value for a single received bar.

        Parameters:
            incoming_bar:
                Market bar used as input for the computation.

        Returns:
            SAR value, or `numpy.nan` if not enough data is available.
        """
        symbol = incoming_bar.symbol
        high = incoming_bar.high
        low = incoming_bar.low

        if symbol not in self._state:
            self._state[symbol] = _SARState()

        s = self._state[symbol]
        s.count += 1

        if s.count == 1:
            s.high_buffer.append(high)
            s.low_buffer.append(low)
            return np.nan

        if s.count == 2:
            prev_high = s.high_buffer[-1]
            prev_low = s.low_buffer[-1]
            s.high_buffer.append(high)
            s.low_buffer.append(low)

            if high >= prev_high:
                s.is_long = True
                s.sar = prev_low
                s.ep = high
            else:
                s.is_long = False
                s.sar = prev_high
                s.ep = low

            s.af = self.af_start
            return s.sar

        # Advance SAR
        sar = s.sar + s.af * (s.ep - s.sar)

        # Clamp SAR against prior two bars' extremes
        if s.is_long:
            sar = min(sar, min(s.low_buffer))
            if low < sar:
                # Reversal to short
                s.is_long = False
                sar = s.ep
                s.ep = low
                s.af = self.af_start
            else:
                if high > s.ep:
                    s.ep = high
                    s.af = min(s.af + self.af_step, self.af_max)
        else:
            sar = max(sar, max(s.high_buffer))
            if high > sar:
                # Reversal to long
                s.is_long = True
                sar = s.ep
                s.ep = high
                s.af = self.af_start
            else:
                if low < s.ep:
                    s.ep = low
                    s.af = min(s.af + self.af_step, self.af_max)

        s.sar = sar
        s.high_buffer.append(high)
        s.low_buffer.append(low)

        return sar
