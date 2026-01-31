from __future__ import annotations

import dataclasses

from onesecondtrader import models
from onesecondtrader.events.responses.base import ResponseBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderAccepted(ResponseBase):
    """
    Event indicating that the order has been accepted by the brokers and is active at the execution venue.

    | Field                 | Type            | Semantics                                                                          |
    |-----------------------|-----------------|------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`           | Time at which the acceptance was observed by the system, as UTC epoch nanoseconds. |
    | `ts_created_ns`       | `int`           | Time at which the event object was created, as UTC epoch nanoseconds.              |
    | `ts_broker_ns`        | `int`           | Time reported by the brokers for the acceptance, as UTC epoch nanoseconds.          |
    | `associated_order_id` | `uuid.UUID`     | Identifier of the accepted order.                                                  |
    | `broker_order_id`     | `str` or `None` | Broker-assigned identifier of the accepted order.                                  |
    """

    broker_order_id: str | None = None


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderRejected(ResponseBase):
    """
    Event indicating that the order has been rejected by the brokers.

    | Field                 | Type                          | Semantics                                                                          |
    |-----------------------|-------------------------------|------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`                         | Time at which the rejection was observed by the system, as UTC epoch nanoseconds.  |
    | `ts_created_ns`       | `int`                         | Time at which the event object was created, as UTC epoch nanoseconds.              |
    | `ts_broker_ns`        | `int`                         | Time reported by the brokers for the rejection, as UTC epoch nanoseconds.           |
    | `associated_order_id` | `uuid.UUID`                   | Identifier of the rejected order.                                                  |
    | `rejection_reason`    | `models.OrderRejectionReason` | Canonical classification of the rejection cause.                                   |
    | `rejection_message`   | `str`                         | Human-readable explanation provided by the brokers.                                 |
    """

    rejection_reason: models.OrderRejectionReason
    rejection_message: str
