from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader.core import models
from . import bases


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderSubmission(bases.BrokerRequestEvent):
    system_order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    symbol: str
    order_type: models.orders.OrderType
    side: models.orders.OrderSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
    action: models.orders.ActionType | None = None
    signal: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderCancellation(bases.BrokerRequestEvent):
    symbol: str


@dataclasses.dataclass(kw_only=True, frozen=True)
class OrderModification(bases.BrokerRequestEvent):
    symbol: str
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
