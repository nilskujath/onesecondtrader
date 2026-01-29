from __future__ import annotations

import dataclasses
import uuid

import pandas as pd

from . import orders


@dataclasses.dataclass
class OrderRecord:
    order_id: uuid.UUID
    symbol: str
    order_type: orders.OrderType
    side: orders.OrderSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
    action: orders.ActionType | None = None
    signal: str | None = None
    filled_quantity: float = 0.0


@dataclasses.dataclass
class FillRecord:
    fill_id: uuid.UUID
    order_id: uuid.UUID
    symbol: str
    side: orders.OrderSide
    quantity: float
    price: float
    commission: float
    ts_event: pd.Timestamp
