from __future__ import annotations

import enum


class BarPeriod(enum.Enum):
    """
    Enumeration of bar aggregation periods.

    | Value  | Semantics            |
    |--------|----------------------|
    | SECOND | Duration of 1 second.|
    | MINUTE | Duration of 1 minute.|
    | HOUR   | Duration of 1 hour.  |
    | DAY    | Duration of 1 day.   |
    """

    SECOND = enum.auto()
    MINUTE = enum.auto()
    HOUR = enum.auto()
    DAY = enum.auto()
