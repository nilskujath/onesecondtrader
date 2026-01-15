"""
Read first: [Domain Models](./domain_models.md).

---
This module defines the event messages used throughout the system.

Event messages are immutable dataclasses used for communication between system
components
They are semantically grouped into market, broker request, and broker
response events via inheritance from dedicated base classes.
---
"""

import dataclasses
import pandas as pd
import uuid

from .domain_models import BarPeriod, OrderSide, OrderType


@dataclasses.dataclass(kw_only=True, frozen=True)
class EventBase:
    ts_event: pd.Timestamp
    ts_created: pd.Timestamp = dataclasses.field(
        default_factory=lambda: pd.Timestamp.now(tz="UTC")
    )


@dataclasses.dataclass(kw_only=True, frozen=True)
class MarketEventBase(EventBase):
    pass


@dataclasses.dataclass(kw_only=True, frozen=True)
class BrokerRequestEventBase(EventBase):
    pass


@dataclasses.dataclass(kw_only=True, frozen=True)
class BrokerResponseEventBase(EventBase):
    ts_broker: pd.Timestamp


@dataclasses.dataclass(kw_only=True, frozen=True)
class NewBar(MarketEventBase):
    symbol: str
    bar_period: BarPeriod
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderSubmission(BrokerRequestEventBase):
    order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderCancellation(BrokerRequestEventBase):
    symbol: str
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RequestOrderModification(BrokerRequestEventBase):
    symbol: str
    order_id: uuid.UUID
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderSubmission(BrokerResponseEventBase):
    order_id: uuid.UUID
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderModification(BrokerResponseEventBase):
    order_id: uuid.UUID
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class AcceptedOrderCancellation(BrokerResponseEventBase):
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderSubmission(BrokerResponseEventBase):
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderModification(BrokerResponseEventBase):
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class RejectedOrderCancellation(BrokerResponseEventBase):
    order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class ConfirmedOrderFilled(BrokerResponseEventBase):
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
class ConfirmedOrderExpired(BrokerResponseEventBase):
    order_id: uuid.UUID
