from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import models
from onesecondtrader.events.orders.base import OrderBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class FillEvent(OrderBase):
    """
    Event representing the execution of a trade resulting in a fill.

    A fill event records the execution of a quantity of an order at a specific price.
    Multiple fill events may be associated with the same order in the case of partial execution.

    | Field                 | Type                | Semantics                                                                       |
    |-----------------------|---------------------|---------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`               | Time at which the fill was observed by the system, as UTC epoch nanoseconds.    |
    | `ts_created_ns`       | `int`               | Time at which the event object was created, as UTC epoch nanoseconds.           |
    | `ts_broker_ns`        | `int`               | Time reported by the broker for the fill, as UTC epoch nanoseconds.             |
    | `associated_order_id` | `uuid.UUID`         | Identifier of the order associated with the fill.                               |
    | `broker_order_id`     | `str` or `None`     | Broker-assigned identifier of the order associated with the fill, if available. |
    | `symbol`              | `str`               | Identifier of the traded instrument.                                            |
    | `fill_id`             | `uuid.UUID`         | System-assigned unique identifier of the fill event.                            |
    | `broker_fill_id`      | `str` or `None`     | Broker-assigned identifier of the execution record, if available.               |
    | `side`                | `models.TradeSide`  | Trade direction of the executed quantity.                                       |
    | `quantity_filled`     | `float`             | Quantity executed in this fill.                                                 |
    | `fill_price`          | `float`             | Execution price of the fill.                                                    |
    | `commission`          | `float`             | Commission or fee associated with the fill.                                     |
    | `exchange`            | `str`               | Identifier of the execution venue.                                              |
    """

    fill_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    broker_fill_id: str | None = None
    side: models.TradeSide
    quantity_filled: float
    fill_price: float
    commission: float
    exchange: str = "SIMULATED"
