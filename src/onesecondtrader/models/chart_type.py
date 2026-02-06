from __future__ import annotations

import enum


class ChartType(enum.Enum):
    """
    Enumeration of OHLC chart rendering styles.

    | Value         | Semantics                                                    |
    |---------------|--------------------------------------------------------------|
    | `CANDLESTICK` | Candlestick bars (black if close <= open, white otherwise). |
    | `OC_BARS`     | Bars with tick left for open and tick right for close.      |
    | `C_BARS`      | Bars with tick for close only.                              |
    | `BARS`        | Simple high to low bars.                                    |
    """

    CANDLESTICK = enum.auto()
    OC_BARS = enum.auto()
    C_BARS = enum.auto()
    BARS = enum.auto()
