"""
Container module for non-component-specific domain models.

This module provides the non-component-specific domain models used across the
trading infrastructure.
"""

import collections
import enum


class DomainModel:
    """
    Container class for non-component-specific domain models.
    Domain models are organised into namespaces to provide clear semantic groupings
    (e.g.: `PositionManagement.OrderType.MARKET`).
    Note that the namespace prefix `DomainModel` can be omitted when accessing
    the domain models, i.e.: `DomainModel.MarketData.OHLCV` can be aliased as
    `MarketData.OHLCV`.

    ???+ note "Domain Model Hierarchy"

        ```mermaid
        ---
        config:
          themeVariables:
            fontSize: "11px"
        ---
        graph LR

            A0[DomainModels]

            A01[MarketData]
            A02[PositionManagement]
            A03[SystemManagement]

            A0 --> A01
            A0 --> A02
            A0 --> A03

            A1["**MarketData.OHLCV**"]
            A2["**MarketData.RecordType**"]
            A01 --> A1
            A01 --> A2

            B1["**PositionManagement.OrderType**"]
            B2["**PositionManagement.OrderState**"]
            B3["**PositionManagement.Side**"]
            B4["**PositionManagement.TimeInForce**"]
            B5["**PositionManagement.CancelReason**"]
            A02 --> B1
            A02 --> B2
            A02 --> B3
            A02 --> B4
            A02 --> B5

            C1["**SystemManagement.StopReason**"]
            A03 --> C1

            subgraph MarketData ["Market Data Domain Models"]
            A1
            A2
            end

            subgraph PositionManagement ["Position Management Domain Models"]
            B1
            B2
            B3
            B4
            B5
            end

            subgraph SystemManagement ["System Management Domain Models"]
            C1
            end

            subgraph DomainModelNamespaces ["Domain Model Namespaces"]
            A0
            A01
            A02
            A03
            end
        ```
    """

    # ----------------------------------------------------------------------------------
    # SYSTEM MANAGEMENT DOMAIN MODEL NAMESPACE
    # ----------------------------------------------------------------------------------

    class SystemManagement:
        """
        Domain model namespace for system management related concepts.

        ???+ note "Domain Model Hierarchy"

            ```mermaid
            ---
            config:
              themeVariables:
                fontSize: "11px"
            ---
            graph LR

                A0[DomainModels]

                A01[MarketData]
                A02[PositionManagement]
                A03[SystemManagement]

                A0 --> A01
                A0 --> A02
                A0 --> A03

                A1["**MarketData.OHLCV**"]
                A2["**MarketData.RecordType**"]
                A01 --> A1
                A01 --> A2

                B1["**PositionManagement.OrderType**"]
                B2["**PositionManagement.OrderState**"]
                B3["**PositionManagement.Side**"]
                B4["**PositionManagement.TimeInForce**"]
                B5["**PositionManagement.CancelReason**"]
                A02 --> B1
                A02 --> B2
                A02 --> B3
                A02 --> B4
                A02 --> B5

                C1["**SystemManagement.StopReason**"]
                A03 --> C1

                subgraph MarketData ["Market Data Domain Models"]
                A1
                A2
                end

                subgraph PositionManagement ["Position Management Domain Models"]
                B1
                B2
                B3
                B4
                B5
                end

                subgraph SystemManagement ["System Management Domain Models"]
                C1
                end

                subgraph DomainModelNamespaces ["Domain Model Namespaces"]
                A0
                A01
                A02
                A03
                end

                style SystemManagement fill:#6F42C1,fill-opacity:0.3
            ```
        """

        class StopReason(enum.Enum):
            """
            Reasons for system or component shutdown.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `SYSTEM_SHUTDOWN` | `enum.auto()` | Coordinated shutdown of entire system |
            | `COMPONENT_DISCONNECT` | `enum.auto()` | Single component disconnect |
            """

            SYSTEM_SHUTDOWN = enum.auto()
            COMPONENT_DISCONNECT = enum.auto()

    # ----------------------------------------------------------------------------------
    # POSITION MANAGEMENT DOMAIN MODEL NAMESPACE
    # ----------------------------------------------------------------------------------

    class PositionManagement:
        """
        ???+ note "Domain Model Hierarchy"

            ```mermaid
            ---
            config:
              themeVariables:
                fontSize: "11px"
            ---
            graph LR

                A0[DomainModels]

                A01[MarketData]
                A02[PositionManagement]
                A03[SystemManagement]

                A0 --> A01
                A0 --> A02
                A0 --> A03

                A1["**MarketData.OHLCV**"]
                A2["**MarketData.RecordType**"]
                A01 --> A1
                A01 --> A2

                B1["**PositionManagement.OrderType**"]
                B2["**PositionManagement.OrderState**"]
                B3["**PositionManagement.Side**"]
                B4["**PositionManagement.TimeInForce**"]
                B5["**PositionManagement.CancelReason**"]
                A02 --> B1
                A02 --> B2
                A02 --> B3
                A02 --> B4
                A02 --> B5

                C1["**SystemManagement.StopReason**"]
                A03 --> C1

                subgraph MarketData ["Market Data Domain Models"]
                A1
                A2
                end

                subgraph PositionManagement ["Position Management Domain Models"]
                B1
                B2
                B3
                B4
                B5
                end

                subgraph SystemManagement ["System Management Domain Models"]
                C1
                end

                subgraph DomainModelNamespaces ["Domain Model Namespaces"]
                A0
                A01
                A02
                A03
                end

                style PositionManagement fill:#6F42C1,fill-opacity:0.3
            ```
        """

        # ------------------------------------------------------------------------------
        # ORDER TYPE

        class OrderType(enum.Enum):
            """
            Order execution types.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `MARKET` | `enum.auto()` | Execute immediately at best available price |
            | `LIMIT` | `enum.auto()` | Execute only at specified price or better |
            | `STOP` | `enum.auto()` | Becomes market order when trigger price is reached |
            | `STOP_LIMIT` | `enum.auto()` | Becomes limit order when trigger price is reached |
            """

            MARKET = enum.auto()
            LIMIT = enum.auto()
            STOP = enum.auto()
            STOP_LIMIT = enum.auto()

        # ------------------------------------------------------------------------------
        # ORDER STATE

        class OrderState(enum.Enum):
            """
            Order lifecycle states.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `NEW` | `enum.auto()` | Created but not submitted |
            | `SUBMITTED` | `enum.auto()` | Sent to broker/exchange |
            | `ACTIVE` | `enum.auto()` | Live in market |
            | `PARTIALLY_FILLED` | `enum.auto()` | Partially executed |
            | `FILLED` | `enum.auto()` | Completely executed |
            | `CANCELLED` | `enum.auto()` | Cancelled before first fill |
            | `CANCELLED_AT_PARTIAL_FILL` | `enum.auto()` | Cancelled after partial fill |
            | `REJECTED` | `enum.auto()` | Rejected by broker/exchange |
            | `EXPIRED` | `enum.auto()` | Expired due to time-in-force constraints |

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

        # ------------------------------------------------------------------------------
        # SIDE
        class Side(enum.Enum):
            """
            Order direction - buy or sell.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `BUY` | `enum.auto()` | Buy the financial instrument |
            | `SELL` | `enum.auto()` | Sell the financial instrument |

            """

            BUY = enum.auto()
            SELL = enum.auto()

        # ------------------------------------------------------------------------------
        # TIME IN FORCE
        class TimeInForce(enum.Enum):
            """
            Order time-in-force specifications.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `DAY` | `enum.auto()` | Valid until end of trading day |
            | `FOK` | `enum.auto()` | Fill entire order immediately or cancel (Fill-or-Kill) |
            | `GTC` | `enum.auto()` | Active until explicitly cancelled (Good-Till-Cancelled) |
            | `GTD` | `enum.auto()` | Active until specified date (Good-Till-Date) |
            | `IOC` | `enum.auto()` | Execute available quantity immediately, cancel rest (Immediate-or-Cancel) |
            """

            DAY = enum.auto()
            FOK = enum.auto()
            GTC = enum.auto()
            GTD = enum.auto()
            IOC = enum.auto()

        # ------------------------------------------------------------------------------
        # CANCEL REASON
        class CancelReason(enum.Enum):
            """
            Reasons for order cancellation.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `CLIENT_REQUEST` | `enum.auto()` | Order cancelled by client/trader request |
            | `EXPIRED_TIME_IN_FORCE` | `enum.auto()` | Order expired due to time-in-force constraints |
            | `BROKER_REJECTED_AT_SUBMISSION` | `enum.auto()` | Broker rejected order during submission |
            | `BROKER_FORCED_CANCEL` | `enum.auto()` | Broker cancelled order due to risk or other constraints |
            | `UNKNOWN` | `enum.auto()` | Cancellation reason not specified or unknown |
            """

            CLIENT_REQUEST = enum.auto()
            EXPIRED_TIME_IN_FORCE = enum.auto()
            BROKER_REJECTED_AT_SUBMISSION = enum.auto()
            BROKER_FORCED_CANCEL = enum.auto()
            UNKNOWN = enum.auto()

    # ----------------------------------------------------------------------------------
    # MARKET DATA DOMAIN MODEL NAMESPACE
    # ----------------------------------------------------------------------------------

    class MarketData:
        """
        Domain model namespace for market data related concepts.
         (Can be aliased as `MarketData` for convenience.)

        ???+ note "Domain Model Hierarchy"

            ```mermaid
            ---
            config:
              themeVariables:
                fontSize: "11px"
            ---
            graph LR

                A0[DomainModels]

                A01[MarketData]
                A02[PositionManagement]
                A03[SystemManagement]

                A0 --> A01
                A0 --> A02
                A0 --> A03

                A1["**MarketData.OHLCV**"]
                A2["**MarketData.RecordType**"]
                A01 --> A1
                A01 --> A2

                B1["**PositionManagement.OrderType**"]
                B2["**PositionManagement.OrderState**"]
                B3["**PositionManagement.Side**"]
                B4["**PositionManagement.TimeInForce**"]
                B5["**PositionManagement.CancelReason**"]
                A02 --> B1
                A02 --> B2
                A02 --> B3
                A02 --> B4
                A02 --> B5

                C1["**SystemManagement.StopReason**"]
                A03 --> C1

                subgraph MarketData ["Market Data Domain Models"]
                A1
                A2
                end

                subgraph PositionManagement ["Position Management Domain Models"]
                B1
                B2
                B3
                B4
                B5
                end

                subgraph SystemManagement ["System Management Domain Models"]
                C1
                end

                subgraph DomainModelNamespaces ["Domain Model Namespaces"]
                A0
                A01
                A02
                A03
                end

                style MarketData fill:#6F42C1,fill-opacity:0.3
            ```
        """

        # ------------------------------------------------------------------------------
        # OHLCV

        OHLCV = collections.namedtuple(
            "OHLCV", ["open", "high", "low", "close", "volume"]
        )
        """
        Simple data class for Open-High-Low-Close-Volume (OHLCV) bar data.

        Attributes:
            open (float): Open price
            high (float): High price
            low (float): Low price
            close (float): Close price
            volume (int | float): Volume

        Examples:
            >>> from onesecondtrader.domain.models import MarketData
            >>> bar = MarketData.OHLCV(12.34, 13.74, 11.26, 12.32, 56789)
            >>> bar.open
            12.34
            >>> bar.high
            13.74
        """

        # ------------------------------------------------------------------------------
        # RECORD TYPE

        class RecordType(enum.Enum):
            """
            Market data record type identifiers that preserve compatibility with
             Databento's rtype integer identifiers.

            **Attributes:**

            | Enum | Value | Description |
            |------|-------|-------------|
            | `OHLCV_1S` | `32` | 1-second bars |
            | `OHLCV_1M` | `33` | 1-minute bars |
            | `OHLCV_1H` | `34` | 1-hour bars |
            | `OHLCV_1D` | `35` | Daily bars |


            Examples:
                >>> from onesecondtrader.domain.models import MarketData
                >>> MarketData.RecordType.OHLCV_1S
                <MarketData.RecordType.OHLCV_1S: 32>
                >>> MarketData.RecordType.OHLCV_1S.value
                32
                >>> MarketData.RecordType.to_string(32)
                '1-second bars'
                >>> MarketData.RecordType.to_string(99)
                'unknown (99)'
            """

            OHLCV_1S = 32
            OHLCV_1M = 33
            OHLCV_1H = 34
            OHLCV_1D = 35

            @classmethod
            def to_string(cls, record_type: int) -> str:
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


# --------------------------------------------------------------------------------------
# ALIASES
# --------------------------------------------------------------------------------------


MarketData = DomainModel.MarketData
PositionManagement = DomainModel.PositionManagement
SystemManagement = DomainModel.SystemManagement
