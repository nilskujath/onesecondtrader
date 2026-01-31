from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class OrderBase(events.EventBase):
    """
    Base class for brokers-originated order events.

    Order events are brokers-originated facts about the state or execution of an order.
    Each order event is correlated to a system order identifier via `associated_order_id`.

    | Field                 | Type            | Semantics                                                                             |
    |-----------------------|-----------------|---------------------------------------------------------------------------------------|
    | `ts_event_ns`         | `int`           | Time at which the response event was observed by the system, as UTC epoch nanoseconds.|
    | `ts_created_ns`       | `int`           | Time at which the event object was created, as UTC epoch nanoseconds.                 |
    | `ts_broker_ns`        | `int`           | Time reported by the brokers for the response, as UTC epoch nanoseconds.               |
    | `associated_order_id` | `uuid.UUID`.    | Identifier of the order associated with the brokers response.                          |
    | `broker_order_id`     | `str` or `None` | Broker-assigned identifier of the order, if reported.                                 |
    | `symbol`              | `str`           | Identifier of the traded instrument.                                                  |
    """

    ts_broker_ns: int
    associated_order_id: uuid.UUID
    broker_order_id: str | None = None
    symbol: str
