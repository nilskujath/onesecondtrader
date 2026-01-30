from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderCancellationRequest(events.EventBase):
    """
    Event representing a request to cancel an existing order.

    | Field             | Type        | Semantics                                                           |
    |-------------------|-------------|---------------------------------------------------------------------|
    | `ts_event_ns`     | `int`       | Time at which the cancellation request was issued, as UTC epoch ns. |
    | `ts_created_ns`   | `int`       | Time at which the event object was created, as UTC epoch ns.        |
    | `system_order_id` | `uuid.UUID` | System-assigned identifier of the order to be cancelled.            |
    | `symbol`          | `str`       | Identifier of the traded instrument.                                |
    """

    system_order_id: uuid.UUID
    symbol: str
