"""
---
This module provides core domain models used throughout the system.

Domain models are enumerations that define the vocabulary and valid values for key
concepts in the trading system. These models are used across all components to ensure
type safety and consistency when representing domain-specific concepts.
---
"""

import enum


class BarPeriod(enum.Enum):
    """
    Time period for aggregating market data into bars.

    Defines the standard time intervals used for OHLCV bar data.
    Each bar represents market activity aggregated over the specified period.
    """

    SECOND = 32
    MINUTE = 33
    HOUR = 34
    DAY = 35


class OrderType(enum.Enum):
    """
    Type of order to submit to the broker.

    Defines the execution behavior for an order.
    Market orders execute immediately at current market price.
    Limit orders execute only at a specified price or better.
    Stop orders become market orders when a trigger price is reached.
    Stop-limit orders become limit orders when a trigger price is reached.
    """

    MARKET = enum.auto()
    LIMIT = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()


class OrderSide(enum.Enum):
    """
    Direction of an order or position.

    Indicates whether an order is buying or selling a security.
    """

    BUY = enum.auto()
    SELL = enum.auto()


class InputSource(enum.Enum):
    """
    Source field from bar data to use as input for indicators.

    Specifies which component of OHLCV bar data should be used when calculating
    technical indicators.
    For example, many indicators use CLOSE prices per default, but could also be
    calculated based on other fields.
    """

    OPEN = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()
    CLOSE = enum.auto()
    VOLUME = enum.auto()
