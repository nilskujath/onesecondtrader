from __future__ import annotations

import enum


class PlotStyle(enum.Enum):
    """
    Enumeration of indicator plot styles.

    | Value       | Semantics                          |
    |-------------|------------------------------------|
    | `LINE`      | Continuous line plot.              |
    | `HISTOGRAM` | Vertical bar histogram.            |
    | `DOTS`      | Scatter plot with dots.            |
    """

    LINE = enum.auto()
    HISTOGRAM = enum.auto()
    DOTS = enum.auto()
