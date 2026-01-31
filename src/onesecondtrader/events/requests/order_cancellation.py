from __future__ import annotations

import dataclasses

from onesecondtrader.events.requests.base import RequestBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderCancellationRequest(RequestBase):
    """
    Event representing a request to cancel an existing order.

    | Field             | Type        | Semantics                                                                    |
    |-------------------|-------------|------------------------------------------------------------------------------|
    | `ts_event_ns`     | `int`       | Time at which the cancellation request was issued, as UTC epoch nanoseconds. |
    | `ts_created_ns`   | `int`       | Time at which the event object was created, as UTC epoch nanoseconds.        |
    | `system_order_id` | `uuid.UUID` | System-assigned identifier of the order to be cancelled.                     |
    | `symbol`          | `str`       | Identifier of the traded instrument.                                         |
    """

    pass
