from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class RequestBase(events.EventBase):
    """
    Base class for request events.

    This class defines attributes common to all requests issued to a broker.

    | Field             | Type        | Semantics                                                                  |
    |-------------------|-------------|----------------------------------------------------------------------------|
    | `ts_event_ns`     | `int`       | Time at which the request was issued, as UTC epoch nanoseconds.            |
    | `ts_created_ns`   | `int`       | Time at which the event object was created, as UTC epoch nanoseconds.      |
    | `system_order_id` | `uuid.UUID` | System-assigned identifier of the order associated with the request.       |
    | `symbol`          | `str`       | Identifier of the traded instrument.                                       |
    """

    system_order_id: uuid.UUID
    symbol: str
