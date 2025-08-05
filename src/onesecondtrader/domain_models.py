"""
Domain models for trading infrastructure.

This module defines the core domain models used across the trading infrastructure.
 The design follows Domain-Driven Design (DDD) principles to structure domain logic
 into semantically cohesive and type-safe groupings. The models reflect foundational
 concepts such as orders, execution states, and position lifecycles. This establishes a
 ubiquitous language that is shared across modules, interfaces, and system components.

Using enums to define these domain models provides the following benefits:

1. **Type Safety** – Prevents invalid states (e.g., avoids `"buy"` vs `"BUY"` bugs)
2. **Compile-Time Validation** – Enables early detection of missing cases (e.g., in match statements)
3. **Semantic Precision** – Improves self-documentation and system comprehensibility
4. **Refactor Robustness** – Reduces breakage when business rules evolve
5. **Performance** – More efficient than string comparisons at runtime
6. **Domain Vocabulary** – Aligns code with trading terminology
(e.g., `OrderType.LIMIT`)

All enums use `enum.auto()` to delegate value assignment unless interoperability with
 external systems requires explicit values. This minimizes maintenance overhead and
 ensures uniqueness without manual management.

The domain models are grouped into the following classes:

- **MarketData** – Market data feeds, aggregated bars, record metadata
- **PositionManagement** – Orders, execution states, trade lifecycle controls
"""

import collections
import enum


class MarketData:
    """
    Domain model for market data representation.

    This namespace defines core data structures and enums related to market data,
    such as aggregated price bars and data record types.
    """

    OHLCV = collections.namedtuple("OHLCV", ["open", "high", "low", "close", "volume"])

    class RecordType(enum.Enum):
        """
        Market data record type identifiers using Databento rtype integers.

        The `MarketData.RecordType` enum preserves compatibility with format by using
         their specified `rtype` integer assignments. This allows tight integration with
         Databento data streams while remaining agnostic to any specific vendor.

        Values:
            - OHLCV_1S (32): 1-second bars
            - OHLCV_1M (33): 1-minute bars
            - OHLCV_1H (34): 1-hour bars
            - OHLCV_1D (35): Daily bars
        """

        OHLCV_1S = 32
        OHLCV_1M = 33
        OHLCV_1H = 34
        OHLCV_1D = 35

        @classmethod
        def to_string(cls, rtype: int) -> str:
            """Convert record type integer to human-readable description."""
            match rtype:
                case cls.OHLCV_1S.value:
                    return "1-second bars"
                case cls.OHLCV_1M.value:
                    return "1-minute bars"
                case cls.OHLCV_1H.value:
                    return "1-hour bars"
                case cls.OHLCV_1D.value:
                    return "daily bars"
                case _:
                    return f"unknown ({rtype})"


class PositionManagement:
    """
    Trading domain concepts for managing orders and positions.

    This namespace defines core abstractions related to the lifecycle of orders.
    """

    class OrderType(enum.Enum):
        """
        Order execution types.

        Values:
            - MARKET: Execute immediately at best available price
            - LIMIT: Execute only at specified price or better
            - STOP: Becomes market order when trigger price is reached
            - STOP_LIMIT: Becomes limit order when trigger price is reached
        """

        MARKET = enum.auto()
        LIMIT = enum.auto()
        STOP = enum.auto()
        STOP_LIMIT = enum.auto()

    class OrderState(enum.Enum):
        """
        Order lifecycle states from creation to completion.

        Values:
            - NEW: Created but not submitted
            - SUBMITTED: Sent to broker/exchange
            - ACTIVE: Live in market
            - PARTIALLY_FILLED: Partially executed
            - FILLED: Completely executed
            - CANCELLED: Cancelled before first fill
            - CANCELLED_AT_PARTIAL_FILL: Cancelled after partial fill
            - REJECTED: Rejected by broker/exchange
            - EXPIRED: Expired due to time-in-force constraints
        """

        NEW = enum.auto()
        SUBMITTED = enum.auto()
        ACTIVE = enum.auto()
        PARTIALLY_FILLED = enum.auto()
        FILLED = enum.auto()
        CANCELLED = enum.auto()
        CANCELLED_AT_PARTIAL_FILL = enum.auto()
        REJECTED = enum.auto()
        EXPIRED = enum.auto()

    class Side(enum.Enum):
        """
        Order direction - buy or sell.

        Values:
            - BUY: Buy the financial instrument
            - SELL: Sell the financial instrument
        """

        BUY = enum.auto()
        SELL = enum.auto()

    class TimeInForce(enum.Enum):
        """
        Order time-in-force specifications.

        Values:
            - DAY: Valid until end of trading day
            - FOK: Fill entire order immediately or cancel (Fill-or-Kill)
            - GTC: Active until explicitly cancelled (Good-Till-Cancelled)
            - GTD: Active until specified date (Good-Till-Date)
            - IOC: Execute available quantity immediately, cancel rest (Immediate-or-Cancel)
        """

        DAY = enum.auto()
        FOK = enum.auto()
        GTC = enum.auto()
        GTD = enum.auto()
        IOC = enum.auto()
