"""
This module defines the core domain models for trading infrastructure.
 These models are organised into namespaces to provide clear semantic groupings
 (e.g.: `PositionManagement.OrderType.MARKET`).
"""

import collections
import enum


class MarketData:
    """
    Domain model namespace for market data related concepts.

    ???+ note "Market Data Record Types"

        ```mermaid
        ---
        config:
          themeVariables:
            fontSize: "11px"
        ---
        graph LR
            A0[MarketData]
            A[MarketData.OHLCV]
            B[MarketData.RecordType]
            A0 --> A
            A0 --> B

        ```
    """

    OHLCV = collections.namedtuple("OHLCV", ["open", "high", "low", "close", "volume"])

    class RecordType(enum.Enum):
        """
        Market data record type identifiers that preserve compatibility with Databento's
         rtype integers identifiers:

        quote:
            - `OHLCV_1S` (`32`): 1-second bars
            - `OHLCV_1M` (`33`): 1-minute bars
            - `OHLCV_1H` (`34`): 1-hour bars
            - `OHLCV_1D` (`35`): Daily bars
        """

        OHLCV_1S = 32
        OHLCV_1M = 33
        OHLCV_1H = 34
        OHLCV_1D = 35

        @classmethod
        def to_string(cls, record_type: int) -> str:
            """Convert record type integer to human-readable description."""
            match record_type:
                case cls.OHLCV_1S.value:
                    return "1-second bars"
                case cls.OHLCV_1M.value:
                    return "1-minute bars"
                case cls.OHLCV_1H.value:
                    return "1-hour bars"
                case cls.OHLCV_1D.value:
                    return "daily bars"
                case _:
                    return f"unknown ({record_type})"


class PositionManagement:
    """
    Domain model namespace for position management related concepts.

    ???+ note "Position Management Concepts"

        ```mermaid
        ---
        config:
          themeVariables:
            fontSize: "11px"
        ---
        graph LR
            A0[PositionManagement]
            A[PositionManagement.OrderType]
            B[PositionManagement.OrderState]
            C[PositionManagement.Side]
            D[PositionManagement.TimeInForce]
            E[PositionManagement.CancelReason]
            A0 --> A
            A0 --> B
            A0 --> C
            A0 --> D
            A0 --> E
        ```
    """

    class OrderType(enum.Enum):
        """
        Order execution types.

        quote:
            - `MARKET`: Execute immediately at best available price
            - `LIMIT`: Execute only at specified price or better
            - `STOP`: Becomes market order when trigger price is reached
            - `STOP_LIMIT`: Becomes limit order when trigger price is reached
        """

        MARKET = enum.auto()
        LIMIT = enum.auto()
        STOP = enum.auto()
        STOP_LIMIT = enum.auto()

    class OrderState(enum.Enum):
        """
        Order lifecycle states.

        quote:
            - `NEW`: Created but not submitted
            - `SUBMITTED`: Sent to broker/exchange
            - `ACTIVE`: Live in market
            - `PARTIALLY_FILLED`: Partially executed
            - `FILLED`: Completely executed
            - `CANCELLED`: Cancelled before first fill
            - `CANCELLED_AT_PARTIAL_FILL`: Cancelled after partial fill
            - `REJECTED`: Rejected by broker/exchange
            - `EXPIRED`: Expired due to time-in-force constraints
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

        quote:
            - `BUY`: Buy the financial instrument
            - `SELL`: Sell the financial instrument
        """

        BUY = enum.auto()
        SELL = enum.auto()

    class TimeInForce(enum.Enum):
        """
        Order time-in-force specifications.

        quote:
            - `DAY`: Valid until end of trading day
            - `FOK`: Fill entire order immediately or cancel (Fill-or-Kill)
            - `GTC`: Active until explicitly cancelled (Good-Till-Cancelled)
            - `GTD`: Active until specified date (Good-Till-Date)
            - `IOC`: Execute available quantity immediately, cancel rest
            (Immediate-or-Cancel)
        """

        DAY = enum.auto()
        FOK = enum.auto()
        GTC = enum.auto()
        GTD = enum.auto()
        IOC = enum.auto()

    class CancelReason(enum.Enum):
        """
        Reasons for order cancellation.

        quote:
            - `CLIENT_REQUEST`: Order cancelled by client/trader request
            - `EXPIRED_TIME_IN_FORCE`: Order expired due to time-in-force constraints
            - `BROKER_REJECTED_AT_SUBMISSION`: Broker rejected order during submission
            - `BROKER_FORCED_CANCEL`: Broker cancelled order due to risk or other constraints
            - `UNKNOWN`: Cancellation reason not specified or unknown
        """

        CLIENT_REQUEST = enum.auto()
        EXPIRED_TIME_IN_FORCE = enum.auto()
        BROKER_REJECTED_AT_SUBMISSION = enum.auto()
        BROKER_FORCED_CANCEL = enum.auto()
        UNKNOWN = enum.auto()


class SystemManagement:
    """
    Domain model namespace for system management related concepts.

    ???+ note "System Management Concepts"

        ```mermaid
        ---
        config:
          themeVariables:
            fontSize: "11px"
        ---
        graph LR
            A0[SystemManagement]
            A[SystemManagement.StopReason]
            A0 --> A
        ```
    """

    class StopReason(enum.Enum):
        """
        Reasons for system or component shutdown.

        quote:
            - `SYSTEM_SHUTDOWN`: Coordinated shutdown of entire system
            - `COMPONENT_DISCONNECT`: Single component disconnect
        """

        SYSTEM_SHUTDOWN = enum.auto()
        COMPONENT_DISCONNECT = enum.auto()
