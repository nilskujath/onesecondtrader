from __future__ import annotations

import dataclasses

from onesecondtrader.events.market.bar_received import BarReceived


@dataclasses.dataclass(kw_only=True, frozen=True)
class BarProcessed(BarReceived):
    """
    Event representing a market data bar with computed indicator values.

    This event extends `BarReceived` by attaching indicator values derived from the bar data.

    | Field           | Type                    | Semantics                                                                  |
    |-----------------|-------------------------|----------------------------------------------------------------------------|
    | `ts_event_ns`   | `int`                   | Time at which the bar was observed by the system, as UTC epoch nanoseconds.|
    | `ts_created_ns` | `int`                   | Time at which the event object was created, as UTC epoch nanoseconds.      |
    | `symbol`        | `str`                   | Identifier of the traded instrument.                                       |
    | `bar_period`    | `models.data.BarPeriod` | Time interval represented by the bar.                                      |
    | `open`          | `float`                 | Opening price of the bar period.                                           |
    | `high`          | `float`                 | Highest traded price during the bar period.                                |
    | `low`           | `float`                 | Lowest traded price during the bar period.                                 |
    | `close`         | `float`                 | Closing price of the bar period.                                           |
    | `volume`        | `int` or `None`         | Traded volume during the bar period, if available.                         |
    | `indicators`    | `dict[str, float]`      | Mapping of indicator names to computed indicator values.                   |
    """

    indicators: dict[str, float] = dataclasses.field(default_factory=dict)
