from __future__ import annotations

import enum


class OrderType(enum.Enum):
    LIMIT = enum.auto()
    MARKET = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()


class OrderSide(enum.Enum):
    BUY = enum.auto()
    SELL = enum.auto()


class ActionType(enum.Enum):
    ENTRY = enum.auto()
    ENTRY_LONG = enum.auto()
    ENTRY_SHORT = enum.auto()
    EXIT = enum.auto()
    EXIT_LONG = enum.auto()
    EXIT_SHORT = enum.auto()
    ADD = enum.auto()
    REDUCE = enum.auto()
    REVERSE = enum.auto()
