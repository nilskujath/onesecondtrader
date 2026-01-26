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
