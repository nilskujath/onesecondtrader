"""
---
This module defines the core domain models used throughout the system.

Domain models are enumerations that define the shared vocabulary of the trading system.
They provide a fixed set of valid values for core concepts and are used across all
system components to ensure consistency and type safety.
---
"""

import enum


class OrderType(enum.Enum):
    LIMIT = enum.auto()
    MARKET = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()


class OrderSide(enum.Enum):
    BUY = enum.auto()
    SELL = enum.auto()


class BarPeriod(enum.Enum):
    SECOND = 32
    MINUTE = 33
    HOUR = 34
    DAY = 35
