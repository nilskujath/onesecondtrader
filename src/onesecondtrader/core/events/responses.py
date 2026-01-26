from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader.core import models
from . import bases


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderSubmissionAccepted(bases.BrokerResponseEvent):
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderSubmissionRejected(bases.BrokerResponseEvent):
    reason: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderModificationAccepted(bases.BrokerResponseEvent):
    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderModificationRejected(bases.BrokerResponseEvent):
    reason: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderCancellationAccepted(bases.BrokerResponseEvent):
    pass


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderCancellationRejected(bases.BrokerResponseEvent):
    reason: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderFilled(bases.BrokerResponseEvent):
    fill_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    broker_fill_id: str | None = None
    symbol: str
    side: models.orders.OrderSide
    quantity_filled: float
    fill_price: float
    commission: float
    exchange: str = "SIMULATED"


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderExpired(bases.BrokerResponseEvent):
    pass
