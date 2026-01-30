from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events, models


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderSubmissionRequest(events.EventBase):
    """
    Event representing a request to submit a new order to a broker.

    | Field             | Type                     | Semantics                                                                  |
    |-------------------|--------------------------|----------------------------------------------------------------------------|
    | `ts_event_ns`     | `int`                    | Time at which the submission request was issued, as UTC epoch nanoseconds. |
    | `ts_created_ns`   | `int`                    | Time at which the event object was created, as UTC epoch nanoseconds.      |
    | `system_order_id` | `uuid.UUID`            | System-assigned unique identifier for the order submission.                  |
    | `symbol`          | `str`                    | Identifier of the traded instrument.                                       |
    | `order_type`      | `models.OrderType`       | Execution constraint of the order.                                         |
    | `side`            | `models.TradeSide`       | Direction of the trade.                                                    |
    | `quantity`        | `float`                  | Requested order quantity.                                                  |
    | `limit_price`     | `float` or `None`        | Limit price, if applicable to the order type.                              |
    | `stop_price`      | `float` or `None`        | Stop price, if applicable to the order type.                               |
    """

    system_order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
    symbol: str
    order_type: models.OrderType
    side: models.TradeSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
