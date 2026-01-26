from __future__ import annotations

import dataclasses

from onesecondtrader.core import models
from . import bases


@dataclasses.dataclass(kw_only=True, frozen=True)
class BarReceived(bases.MarketEvent):
    symbol: str
    bar_period: models.data.BarPeriod
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


@dataclasses.dataclass(kw_only=True, frozen=True)
class BarProcessed(BarReceived):
    indicators: dict[str, float] = dataclasses.field(default_factory=dict)
