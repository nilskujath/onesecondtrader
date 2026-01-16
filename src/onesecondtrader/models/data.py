from __future__ import annotations

import enum


class BarPeriod(enum.Enum):
    SECOND = enum.auto()
    MINUTE = enum.auto()
    HOUR = enum.auto()
    DAY = enum.auto()
