from __future__ import annotations

import enum


class PlotWidth(enum.Enum):
    """
    Enumeration of indicator plot widths.

    | Value          | Semantics                          |
    |----------------|------------------------------------|
    | `THIN`         | Thin line / small dots.            |
    | `NORMAL`       | Normal line / default dots.        |
    | `THICK`        | Thick line / large dots.           |
    | `EXTRA_THICK`  | Extra thick line / extra large dots.|
    """

    THIN = enum.auto()
    NORMAL = enum.auto()
    THICK = enum.auto()
    EXTRA_THICK = enum.auto()
