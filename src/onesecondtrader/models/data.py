from __future__ import annotations

import enum


class BarPeriod(enum.Enum):
    SECOND = enum.auto()
    MINUTE = enum.auto()
    HOUR = enum.auto()
    DAY = enum.auto()


class InputSource(enum.Enum):
    OPEN = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()
    CLOSE = enum.auto()
    VOLUME = enum.auto()
