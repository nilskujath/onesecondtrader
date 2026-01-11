"""
Read first: [`models.py`](./models.md).

---
This module provides all event message classes used in the system.

In an event-driven system, components communicate by sending event messages to each
other. An event message is an immutable object that contains all information relevant
to a specific occurrence, such as incoming market data, order submissions, fills, or
other domain-specific events.
---
"""

import dataclasses
import uuid

import pandas as pd

from .models import BarPeriod, OrderType, OrderSide


@dataclasses.dataclass(kw_only=True, frozen=True)
class Event:
    """
    Base class for all event messages in the system.

    All events include a timestamp indicating when the event was created or received.
    Subclasses define specific event types with additional fields relevant to that
    event.
    """

    ts_event: pd.Timestamp = dataclasses.field(
        default_factory=lambda: pd.Timestamp.now(tz="UTC")
    )


@dataclasses.dataclass(kw_only=True, frozen=True)
class ReceivedNewBar(Event):
    """
    Event indicating a new bar of market data has been received.

    Contains OHLCV data for a specific symbol and bar period. This event is typically
    emitted by data feed components when new market data arrives.
    """

    ts_event: pd.Timestamp
    symbol: str
    bar_period: BarPeriod
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class ProcessedBar(Event):
    """
    Event indicating a bar has been processed and enriched with indicator values.

    Contains the same OHLCV data as ReceivedNewBar, plus a dictionary of computed
    indicator values. This event is typically emitted after strategies or other
    components have calculated technical indicators for the bar.
    """

    ts_event: pd.Timestamp
    symbol: str
    bar_period: BarPeriod
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None
    indicators: dict[str, float] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderSubmission(Event):
    """
    Event requesting submission of a new order with the broker.

    Contains all parameters needed to submit an order, including symbol, order type,
    side, quantity, and optional limit/stop prices. A unique order_id is automatically
    generated if not provided.
    """

    order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderModification(Event):
    """
    Event requesting modification of an existing order.

    Identifies the order to modify by order_id and symbol. Any of quantity, limit_price,
    or stop_price can be updated by providing new values.
    """

    symbol: str
    order_id: uuid.UUID
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderCancellation(Event):
    """
    Event requesting cancellation of an existing order.

    Identifies the order to cancel by order_id and symbol.
    """

    symbol: str
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderSubmission(Event):
    """
    Event indicating the broker has accepted an order submission.

    Contains the system's order_id and optionally the broker's order_id if provided
    by the broker.
    """

    order_id: uuid.UUID
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderModification(Event):
    """
    Event indicating the broker has accepted an order modification.

    Contains the system's order_id and optionally the broker's order_id if provided
    by the broker.
    """

    order_id: uuid.UUID
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderCancellation(Event):
    """
    Event indicating the broker has accepted an order cancellation.

    Contains the system's order_id for the cancelled order.
    """

    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderSubmission(Event):
    """
    Event indicating the broker has rejected an order submission.

    Contains the system's order_id for the rejected order.
    """

    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderModification(Event):
    """
    Event indicating the broker has rejected an order modification.

    Contains the system's order_id for the order that could not be modified.
    """

    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderCancellation(Event):
    """
    Event indicating the broker has rejected an order cancellation.

    Contains the system's order_id for the order that could not be cancelled.
    """

    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderFilled(Event):
    """
    Event indicating an order has been filled (fully or partially).

    Contains details about the fill including quantity, price, commission, and the
    associated order. A unique fill_id is automatically generated if not provided.
    The broker may optionally provide a broker_fill_id.
    """

    fill_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    broker_fill_id: str | None = None
    associated_order_id: uuid.UUID
    symbol: str
    side: OrderSide
    quantity_filled: float
    fill_price: float
    commission: float
    exchange: str = "SIMULATED"


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderExpired(Event):
    """
    Event indicating an order has expired without being filled.

    Contains the system's order_id for the expired order. This typically occurs for
    time-limited orders that were not filled before their expiration time.
    """

    order_id: uuid.UUID
