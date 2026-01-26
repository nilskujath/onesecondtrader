from __future__ import annotations

import dataclasses
import pandas as pd
import uuid


@dataclasses.dataclass(kw_only=True, frozen=True)
class EventBase:
    ts_event: pd.Timestamp
    ts_created: pd.Timestamp = dataclasses.field(
        default_factory=lambda: pd.Timestamp.now(tz="UTC")
    )


@dataclasses.dataclass(kw_only=True, frozen=True)
class MarketEvent(EventBase):
    pass


@dataclasses.dataclass(kw_only=True, frozen=True)
class BrokerRequestEvent(EventBase):
    system_order_id: uuid.UUID


@dataclasses.dataclass(kw_only=True, frozen=True)
class BrokerResponseEvent(EventBase):
    ts_broker: pd.Timestamp
    associated_order_id: uuid.UUID
