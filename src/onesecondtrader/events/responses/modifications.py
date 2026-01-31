from __future__ import annotations

import dataclasses

from onesecondtrader import models
from onesecondtrader.events.responses.base import ResponseBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class ModificationAccepted(ResponseBase):
    """
    Event indicating that the requested modification has been acknowledged by
    the brokers and that the updated order parameters are active at the execution venue.

    | Field                 | Type            | Semantics                                                                              |
    |-----------------------|-----------------|----------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`           | Time at which the acceptance was observed by the system, as UTC epoch nanoseconds.     |
    | `ts_created_ns`       | `int`           | Time at which the event object was created, as UTC epoch nanoseconds.                  |
    | `ts_broker_ns`        | `int`           | Time reported by the brokers for the modification acceptance, as UTC epoch nanoseconds. |
    | `associated_order_id` | `uuid.UUID`     | Identifier of the modified order.                                                      |
    | `broker_order_id`     | `str` or `None` | Broker-assigned identifier of the order after modification, if reported.               |
    """

    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class ModificationRejected(ResponseBase):
    """
    Event indicating that the requested modification has been rejected by the brokers.

    | Field                 | Type                                 | Semantics                                                                          |
    |-----------------------|--------------------------------------|------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`                                | Time at which the rejection was observed by the system, as UTC epoch nanoseconds.  |
    | `ts_created_ns`       | `int`                                | Time at which the event object was created, as UTC epoch nanoseconds.              |
    | `ts_broker_ns`        | `int`                                | Time reported by the brokers for the rejection, as UTC epoch nanoseconds.           |
    | `associated_order_id` | `uuid.UUID`                          | Identifier of the order associated with the rejected modification.                 |
    | `rejection_reason`    | `models.ModificationRejectionReason` | Canonical classification of the modification rejection cause.                      |
    | `rejection_message`   | `str`                                | Human-readable explanation provided by the brokers.                                 |
    """

    rejection_reason: models.ModificationRejectionReason
    rejection_message: str
