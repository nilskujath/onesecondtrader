"""
This module provides the event messages used for decoupled communication between the
 trading infrastructure's components.
Events are organized into namespaces (`Market`, `Request`, `Response`, and `System`)
 to provide clear semantic groupings.
Base event messages used for structure inheritance are grouped under the
 `Base` namespace.
Dataclass field validation logic is grouped under the `_Validate` namespace.

???+ note "Module Overview: `events.py`"
    ```mermaid
    ---
    config:
      themeVariables:
        fontSize: "11px"
    ---
    graph LR

    R[events.Base.Event]
    R1[events.Base.Market]
    R2[events.Base.Request]
    R21[events.Base.OrderRequest]
    R22[events.Base.CancelRequest]
    R3[events.Base.Response]
    R4[events.Base.System]

    R --> R1
    R --> R2
    R --> R3
    R --> R4

    R2 --> R21
    R2 --> R22

    A1[events.Market.IncomingBar]

    R1 --> A1

    style A1 fill:#6F42C1,fill-opacity:0.3

    B1[events.Request.MarketOrder]
    B2[events.Request.LimitOrder]
    B3[events.Request.StopOrder]
    B4[events.Request.StopLimitOrder]
    B5[events.Request.CancelOrder]
    B6[events.Request.FlushSymbol]
    B7[events.Request.FlushAll]

    R21 --> B1
    R21 --> B2
    R21 --> B3
    R21 --> B4
    R22 --> B5
    R22 --> B6
    R22 --> B7

    style B1 fill:#6F42C1,fill-opacity:0.3
    style B2 fill:#6F42C1,fill-opacity:0.3
    style B3 fill:#6F42C1,fill-opacity:0.3
    style B4 fill:#6F42C1,fill-opacity:0.3
    style B5 fill:#6F42C1,fill-opacity:0.3
    style B6 fill:#6F42C1,fill-opacity:0.3
    style B7 fill:#6F42C1,fill-opacity:0.3

    C1[events.Response.OrderSubmitted]
    C2[events.Response.OrderFilled]
    C3[events.Response.OrderCancelled]
    C4[events.Response.OrderRejected]

    R3 --> C1
    R3 --> C2
    R3 --> C3
    R3 --> C4

    style C1 fill:#6F42C1,fill-opacity:0.3
    style C2 fill:#6F42C1,fill-opacity:0.3
    style C3 fill:#6F42C1,fill-opacity:0.3
    style C4 fill:#6F42C1,fill-opacity:0.3

    D1[events.System.Shutdown]

    R4 --> D1

    style D1 fill:#6F42C1,fill-opacity:0.3


    subgraph Market ["Market Update Event Messages"]
        R1
        A1

        subgraph MarketNamespace ["events.Market Namespace"]
            A1
        end

    end


    subgraph Request ["Broker Request Event Messages"]
        R2
        R21
        R22
        B1
        B2
        B3
        B4
        B5
        B6
        B7

        subgraph RequestNamespace ["events.Request Namespace"]
            B1
            B2
            B3
            B4
            B5
            B6
            B7
        end

    end

    subgraph Response ["Broker Response Event Messages"]
        R3
        C1
        C2
        C3
        C4

        subgraph ResponseNamespace ["events.Response Namespace"]
            C1
            C2
            C3
            C4
        end

    end

    subgraph System ["System-Internal Event Messages"]
        R4
        D1

        subgraph SystemNamespace ["events.System Namespace"]
            D1
        end

    end
    ```
"""

import dataclasses
import pandas as pd
import re
import uuid
from onesecondtrader.core import models
from onesecondtrader.monitoring import console


class Base:
    """
    Namespace for event base dataclasses.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Event:
        """
        Base event message dataclass.
        This dataclass cannot be instantiated directly.

        Attributes:
            ts_event (pd.Timestamp): Timestamp of the event in pandas Timestamp format.
                (Must be timezone-aware.)
            event_bus_sequence_number (int | None): Auto-generated Sequence number of
                 the event.
                This will be assigned as soon as the event enters the event bus via
                 `messaging.EventBus.publish(<event>)`.
        """

        ts_event: pd.Timestamp
        event_bus_sequence_number: int | None = dataclasses.field(
            default=None, init=False
        )

        def __new__(cls, *args, **kwargs):
            if cls is Base.Event:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

        def __post_init__(self) -> None:
            _Validate.timezone_aware(self.ts_event, "ts_event", "Event")

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Market(Event):
        """
        Base event message dataclass for market events.
        Inherits from `Base.Event`.
        Each market event message is associated with a specific financial instrument via
         the `symbol` field.
        This dataclass cannot be instantiated directly.

        Attributes:
            symbol (str): Symbol of the financial instrument.
        """

        symbol: str

        def __new__(cls, *args, **kwargs):
            if cls is Base.Market:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

        def __post_init__(self) -> None:
            super().__post_init__()
            _Validate.symbol(self.symbol, "Market event")

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Request(Event):
        """
        Base event message dataclass for broker requests.
        This dataclass cannot be instantiated directly.
        `ts_event` is auto-generated by default.

        Attributes:
            ts_event: Timestamp of the event. (defaults to current UTC time;
                auto-generated)
        """

        ts_event: pd.Timestamp = dataclasses.field(
            default_factory=lambda: pd.Timestamp.now(tz="UTC")
        )

        def __new__(cls, *args, **kwargs):
            if cls is Base.Request:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderRequest(Request):
        """
        Base event message dataclass for order requests.
        Inherits from `Base.Request`.
        This dataclass cannot be instantiated directly.

        Attributes:
            symbol (str): Symbol of the financial instrument.
            side (models.Side): Side of the order.
            quantity (float): Quantity of the order.
            time_in_force (models.TimeInForce): Time in force of the order.
            order_expiration (pd.Timestamp | None): Expiration timestamp of the order
                (optional).
                Only relevant if `time_in_force` is `models.TimeInForce.GTD`.
            order_id (uuid.UUID): Unique ID of the order. (auto-generated)
        """

        symbol: str
        side: models.Side
        quantity: float
        time_in_force: models.TimeInForce
        order_expiration: pd.Timestamp | None = None
        order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)

        def __new__(cls, *args, **kwargs):
            if cls is Base.OrderRequest:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

        def __post_init__(self) -> None:
            super().__post_init__()
            _Validate.symbol(self.symbol, f"Order {self.order_id}")

            _Validate.timezone_aware(
                self.order_expiration, "order_expiration", f"Order {self.order_id}"
            )
            _Validate.quantity(self.quantity, f"Order {self.order_id}")

            if self.time_in_force.value == 4:
                if self.order_expiration is None:
                    console.logger.error(
                        f"Order {self.order_id}: GTD order missing expiration "
                        f"timestamp."
                    )
                elif self.order_expiration <= self.ts_event:
                    console.logger.error(
                        f"Order {self.order_id}: GTD expiration "
                        f"{self.order_expiration} "
                        f"is not after event timestamp {self.ts_event}."
                    )

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class CancelRequest(Request):
        """
        Base event message dataclass for order cancellation requests.
        Inherits from `Base.Request`.
        This dataclass cannot be instantiated directly.
        """

        def __new__(cls, *args, **kwargs):
            if cls is Base.CancelRequest:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Response(Event):
        """
        Base event message dataclass for broker responses.
        This dataclass cannot be instantiated directly.
        """

        def __new__(cls, *args, **kwargs):
            if cls is Base.Response:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class System(Event):
        """
        Base event message dataclass for system-internal messages.
        This dataclass cannot be instantiated directly.
        `ts_event` is auto-generated by default.

        Attributes:
            ts_event: Timestamp of the event. (defaults to current UTC time;
                auto-generated)
        """

        ts_event: pd.Timestamp = dataclasses.field(
            default_factory=lambda: pd.Timestamp.now(tz="UTC")
        )

        def __new__(cls, *args, **kwargs):
            if cls is Base.System:
                console.logger.error(
                    f"Cannot instantiate abstract class '{cls.__name__}' directly"
                )
            return super().__new__(cls)


class Market:
    """
    Namespace for market update event messages.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class IncomingBar(Base.Market):
        """
        Event message dataclass for incoming market data bars.
        Inherits from `Base.Market`.

        Attributes:
            bar (models.Bar): Bar of market data.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> from onesecondtrader.core import models
            >>> event = events.Market.IncomingBar(
            ...     ts_event=pd.Timestamp("2023-01-01 00:00:00", tz="UTC"),
            ...     symbol="AAPL",
            ...     bar=models.Bar(
            ...         open=100.0,
            ...         high=101.0,
            ...         low=99.0,
            ...         close=100.5,
            ...         volume=10000,
            ...     ),
            ... )
            ```
        """

        bar: models.Bar


class Request:
    """
    Namespace for broker request event messages.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class MarketOrder(Base.OrderRequest):
        """
        Event message dataclass for submitting a market order to the broker.

        Attributes:
            order_type (models.OrderType): Type of the order (automatically set to
            models.OrderType.MARKET).

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.MarketOrder(
            ...     symbol="AAPL",
            ...     side=models.Side.BUY,
            ...     quantity=100.0,
            ...     time_in_force=models.TimeInForce.DAY,
            ... )
        """

        order_type: models.OrderType = dataclasses.field(
            init=False, default=models.OrderType.MARKET
        )

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class LimitOrder(Base.OrderRequest):
        """
        Event message dataclass for submitting a limit order to the broker.

        Attributes:
            order_type (models.OrderType): Type of the order (automatically set to
            models.OrderType.LIMIT).
            limit_price (float): Limit price of the order.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.LimitOrder(
            ...     symbol="AAPL",
            ...     side=models.Side.BUY,
            ...     quantity=100.0,
            ...     time_in_force=models.TimeInForce.DAY,
            ...     limit_price=100.0,
            ... )
        """

        order_type: models.OrderType = dataclasses.field(
            init=False, default=models.OrderType.LIMIT
        )
        limit_price: float

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class StopOrder(Base.OrderRequest):
        """
        Event message dataclass for submitting a stop order to the broker.

        Attributes:
            order_type (models.OrderType): Type of the order (automatically set to
            models.OrderType.STOP).
            stop_price (float): Stop price of the order.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.StopOrder(
            ...     symbol="AAPL",
            ...     side=models.Side.BUY,
            ...     quantity=100.0,
            ...     time_in_force=models.TimeInForce.DAY,
            ...     stop_price=100.0,
            ... )
        """

        order_type: models.OrderType = dataclasses.field(
            init=False, default=models.OrderType.STOP
        )
        stop_price: float

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class StopLimitOrder(Base.OrderRequest):
        """
        Event message dataclass for submitting a stop-limit order to the broker.

        Attributes:
            order_type (models.OrderType): Type of the order (automatically set to
            models.OrderType.STOP_LIMIT).
            stop_price (float): Stop price of the order.
            limit_price (float): Limit price of the order.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.StopLimitOrder(
            ...     symbol="AAPL",
            ...     side=models.Side.BUY,
            ...     quantity=100.0,
            ...     time_in_force=models.TimeInForce.DAY,
            ...     stop_price=100.0,
            ...     limit_price=100.0,
            ... )
        """

        order_type: models.OrderType = dataclasses.field(
            init=False, default=models.OrderType.STOP_LIMIT
        )
        stop_price: float
        limit_price: float

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class CancelOrder(Base.CancelRequest):
        """
        Event message dataclass for cancelling an order.

        Attributes:
            order_id (uuid.UUID): Unique ID of the order to cancel.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.CancelOrder(
            ...     order_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
            ... )
        """

        order_id: uuid.UUID

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class FlushSymbol(Base.Request):
        """
        Event message dataclass for flushing all orders for a symbol.

        Attributes:
            symbol (str): Symbol to flush.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.FlushSymbol(
            ...     symbol="AAPL",
            ... )
        """

        symbol: str

        def __post_init__(self) -> None:
            super().__post_init__()
            _Validate.symbol(self.symbol, "Flush request")

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class FlushAll(Base.Request):
        """
        Event message dataclass for flushing all orders for all symbols.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.Request.FlushAll()
        """

        pass


class Response:
    """
    Namespace for broker response event messages.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderSubmitted(Base.Response):
        """
        Event message dataclass for order submission confirmation from the broker.

        Attributes:
            order_submitted_id (uuid.UUID): Unique ID of the submitted order.
            associated_request_id (uuid.UUID): Unique ID of the request that triggered
                the order submission.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> import pandas as pd
            >>> import uuid
            >>> event = events.Response.OrderSubmitted(
            ...     ts_event=pd.Timestamp(
            ...         "2023-01-01 00:00:00", tz="UTC"),
            ...     order_submitted_id=uuid.UUID(
            ...         "12345678-1234-5678-1234-567812345678"),
            ...     associated_request_id=uuid.UUID(
            ...         "12345678-1234-5678-1234-567812345678"
            ...     ),
            ... )
        """

        order_submitted_id: uuid.UUID
        associated_request_id: uuid.UUID

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderFilled(Base.Response):
        """
        Event message dataclass for order fill confirmation from the broker.

        Attributes:
            fill_id (uuid.UUID): Unique ID of the fill. (auto-generated)
            associated_order_submitted_id (uuid.UUID): Unique ID of the submitted order
                that triggered the fill.
            side (models.Side): Side of the fill.
            quantity_filled (float): Quantity filled.
            filled_at_price (float): Price at which the fill was executed.
            commission_and_fees (float): Commission and fees for the fill.
            net_fill_value (float): Net fill value (auto-generated).
            exchange (str | None): Exchange on which the fill was executed. (optional;
                defaults to "SIMULATED")

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> from onesecondtrader.core import models
            >>> import pandas as pd
            >>> import uuid
            >>> event = events.Response.OrderFilled(
            ...     ts_event=pd.Timestamp("2023-01-01 00:00:00", tz="UTC"),
            ...     associated_order_submitted_id=uuid.UUID(
            ...         "12345678-1234-5678-1234-567812345678"
            ...     ),
            ...     side=models.Side.BUY,
            ...     quantity_filled=100.0,
            ...     filled_at_price=100.0,
            ...     commission_and_fees=1.0,
            ... )
        """

        fill_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
        associated_order_submitted_id: uuid.UUID
        side: models.Side
        quantity_filled: float
        filled_at_price: float
        commission_and_fees: float
        net_fill_value: float = dataclasses.field(init=False)
        exchange: str | None = None

        def __post_init__(self):
            object.__setattr__(self, "fill_id", self.fill_id or uuid.uuid4())

            gross_value = self.filled_at_price * self.quantity_filled

            if self.side.value == 1:
                net_value = gross_value + self.commission_and_fees
            else:
                net_value = gross_value - self.commission_and_fees

            object.__setattr__(self, "net_fill_value", net_value)

            object.__setattr__(self, "exchange", self.exchange or "SIMULATED")

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderCancelled(Base.Response):
        """
        Event message dataclass for order cancellation confirmation from the broker.

        Attributes:
            associated_order_submitted_id (uuid.UUID): Unique ID of the submitted order
                that was cancelled.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> import pandas as pd
            >>> import uuid
            >>> event = events.Response.OrderCancelled(
            ...     ts_event=pd.Timestamp("2023-01-01 00:00:00", tz="UTC"),
            ...     associated_order_submitted_id=uuid.UUID(
            ...         "12345678-1234-5678-1234-567812345678"
            ...     ),
            ... )
        """

        associated_order_submitted_id: uuid.UUID

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderRejected(Base.Response):
        """
        Event message dataclass for order rejection confirmation from the broker.

        Attributes:
            associated_order_submitted_id (uuid.UUID): Unique ID of the submitted order
                that was rejected.
            reason (models.OrderRejectionReason): Reason for the rejection.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> from onesecondtrader.core import models
            >>> import pandas as pd
            >>> import uuid
            >>> event = events.Response.OrderRejected(
            ...     ts_event=pd.Timestamp("2023-01-01 00:00:00", tz="UTC"),
            ...     associated_order_submitted_id=uuid.UUID(
            ...         "12345678-1234-5678-1234-567812345678"
            ...     ),
            ...     reason=models.OrderRejectionReason.NEGATIVE_QUANTITY,
            ... )
        """

        associated_order_submitted_id: uuid.UUID
        reason: models.OrderRejectionReason


class System:
    """
    Namespace for system-internal event messages.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Shutdown(Base.System):
        """
        Event message dataclass for system shutdown.

        Examples:
            >>> from onesecondtrader.messaging import events
            >>> event = events.System.Shutdown()
        """

        pass


class _Validate:
    """Internal validation utilities for events."""

    @staticmethod
    def symbol(symbol: str, context: str = "") -> None:
        """Validate symbol format and log errors."""
        if not symbol or not symbol.strip():
            console.logger.error(f"{context}: Symbol cannot be empty or whitespace")
            return

        if not re.fullmatch(r"[A-Z0-9._-]+", symbol):
            console.logger.error(f"{context}: Invalid symbol format: {symbol}")

    @staticmethod
    def quantity(quantity: float, context: str = "") -> None:
        """Validate quantity values and log errors."""
        if (
            quantity != quantity
            or quantity == float("inf")
            or quantity == float("-inf")
        ):
            console.logger.error(f"{context}: quantity cannot be NaN or infinite")
            return

        if quantity <= 0:
            console.logger.error(
                f"{context}: quantity must be positive, got {quantity}"
            )

        if quantity > 1e9:
            console.logger.error(f"{context}: quantity too large: {quantity}")

    @staticmethod
    def timezone_aware(
        timestamp: pd.Timestamp | None, field_name: str, context: str = ""
    ) -> None:
        """Validate that timestamp is timezone-aware and log errors."""
        if timestamp is not None and timestamp.tz is None:
            console.logger.error(
                f"{context}: {field_name} must be timezone-aware, got {timestamp}"
            )
