from __future__ import annotations

import dataclasses

from onesecondtrader import events, models


@dataclasses.dataclass(kw_only=True, frozen=True)
class BarReceived(events.EventBase):
    """
    Event representing the reception of a completed market data bar.

    This event represents a time-aggregated bar as received from a market data source or produced by a resampling process.

    | Field           | Type                     | Semantics                                                                   |
    |-----------------|--------------------------|-----------------------------------------------------------------------------|
    | `ts_event_ns`   | `int`                    | Time at which the bar was observed by the system, as UTC epoch nanoseconds. |
    | `ts_created_ns` | `int`                    | Time at which the event object was created, as UTC epoch nanoseconds.       |
    | `symbol`        | `str`                    | Identifier of the traded instrument.                                        |
    | `bar_period`    | `models.data.BarPeriod`  | Time interval represented by the bar.                                       |
    | `open`          | `float`                  | Opening price of the bar period.                                            |
    | `high`          | `float`                  | Highest traded price during the bar period.                                 |
    | `low`           | `float`                  | Lowest traded price during the bar period.                                  |
    | `close`         | `float`                  | Closing price of the bar period.                                            |
    | `volume`        | `int` or `None`          | Traded volume during the bar period, if available.                          |
    """

    symbol: str
    bar_period: models.BarPeriod
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None
