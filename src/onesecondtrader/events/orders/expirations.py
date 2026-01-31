from __future__ import annotations

import dataclasses

from onesecondtrader.events.orders.base import OrderBase


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderExpired(OrderBase):
    """
    Event indicating that the order is no longer active at the venue due to expiration according to brokers- or venue-specific rules (e.g. time-in-force constraints).

    | Field                 | Type            | Semantics                                                                          |
    |-----------------------|-----------------|------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`           | Time at which the expiration was observed by the system, as UTC epoch nanoseconds. |
    | `ts_created_ns`       | `int`           | Time at which the event object was created, as UTC epoch nanoseconds.              |
    | `ts_broker_ns`        | `int`           | Time reported by the brokers for the expiration, as UTC epoch nanoseconds.          |
    | `associated_order_id` | `uuid.UUID`     | Identifier of the expired order.                                                   |
    | `broker_order_id`     | `str` or `None` | Broker-assigned identifier of the expired order, if reported.                      |
    | `symbol`              | `str`           | Identifier of the traded instrument.                                               |
    """

    pass
