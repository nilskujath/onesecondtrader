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
    | `DASH1`     | Short/dense dashed line.           |
    | `DASH2`     | Medium dashed line.                |
    | `DASH3`     | Long/sparse dashed line.           |
    """

    LINE = enum.auto()
    HISTOGRAM = enum.auto()
    DOTS = enum.auto()
    DASH1 = enum.auto()
    DASH2 = enum.auto()
    DASH3 = enum.auto()
