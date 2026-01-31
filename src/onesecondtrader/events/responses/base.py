from __future__ import annotations

import dataclasses
import uuid


from onesecondtrader import events


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class ResponseBase(events.EventBase):
    """
    Base class for broker response events.

    This class defines attributes common to all responses received from a broker in reaction to previously issued requests.

    | Field                 | Type        | Semantics                                                                             |
    |-----------------------|-------------|---------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`       | Time at which the response event was observed by the system, as UTC epoch nanoseconds.|
    | `ts_created_ns`       | `int`       | Time at which the event object was created, as UTC epoch nanoseconds.                 |
    | `ts_broker_ns`        | `int`       | Time reported by the broker for the response, as UTC epoch nanoseconds.               |
    | `associated_order_id` | `uuid.UUID` | Identifier of the order associated with the broker response.                          |
    """

    ts_broker_ns: int
    associated_order_id: uuid.UUID
