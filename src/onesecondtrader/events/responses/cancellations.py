from __future__ import annotations

import dataclasses

from onesecondtrader import models
from onesecondtrader.events.responses.base import ResponseBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class CancellationAccepted(ResponseBase):
    """
    Event indicating that the order cancellation has been acknowledged by the brokers and the order is no longer active at the execution venue.

    | Field                 | Type            | Semantics                                                                              |
    |-----------------------|-----------------|----------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`           | Time at which the cancellation was observed by the system, as UTC epoch nanoseconds.   |
    | `ts_created_ns`       | `int`           | Time at which the event object was created, as UTC epoch nanoseconds.                  |
    | `ts_broker_ns`        | `int`           | Time reported by the brokers for the cancellation, as UTC epoch nanoseconds.            |
    | `associated_order_id` | `uuid.UUID`     | Identifier of the cancelled order.                                                     |
    | `broker_order_id`     | `str` or `None` | Broker-assigned identifier of the cancelled order, if reported.                        |
    """

    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class CancellationRejected(ResponseBase):
    """
    Event indicating that the order cancellation has been rejected by the brokers.

    | Field                 | Type                                 | Semantics                                                                          |
    |-----------------------|--------------------------------------|------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`                                | Time at which the rejection was observed by the system, as UTC epoch nanoseconds.  |
    | `ts_created_ns`       | `int`                                | Time at which the event object was created, as UTC epoch nanoseconds.              |
    | `ts_broker_ns`        | `int`                                | Time reported by the brokers for the rejection, as UTC epoch nanoseconds.           |
    | `associated_order_id` | `uuid.UUID`                          | Identifier of the order associated with the rejected cancellation.                 |
    | `rejection_reason`    | `models.CancellationRejectionReason` | Canonical classification of the cancellation rejection cause.                      |
    | `rejection_message`   | `str`                                | Human-readable explanation provided by the brokers.                                 |
    """

    rejection_reason: models.CancellationRejectionReason
    rejection_message: str
