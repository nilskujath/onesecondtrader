from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderModificationRequest(events.EventBase):
    """
    Event representing a request to modify an existing order.

    | Field             | Type              | Semantics                                                                    |
    |-------------------|-------------------|------------------------------------------------------------------------------|
    | `ts_event_ns`     | `int`             | Time at which the modification request was issued, as UTC epoch nanoseconds. |
    | `ts_created_ns`   | `int`             | Time at which the event object was created, as UTC epoch nanoseconds.        |
    | `system_order_id` | `uuid.UUID`       | System-assigned identifier of the order to be modified.                      |
    | `symbol`          | `str`             | Identifier of the traded instrument.                                         |
    | `quantity`        | `float` or `None` | Updated order quantity, if modified.                                         |
    | `limit_price`     | `float` or `None` | Updated limit price, if modified.                                            |
    | `stop_price`      | `float` or `None` | Updated stop price, if modified.                                             |
    """

    system_order_id: uuid.UUID
    symbol: str
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
