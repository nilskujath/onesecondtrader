from __future__ import annotations

import dataclasses
import time


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class EventBase:
    """
    Base class for immutable event message objects, using Unix epoch nanoseconds.

    | Field           | Type   | Semantics                                                              |
    |-----------------|--------|------------------------------------------------------------------------|
    | `ts_event_ns`   | `int`  | Time at which the represented fact occurred, as UTC epoch nanoseconds. |
    | `ts_created_ns` | `int`  | Time at which the event object was created, as UTC epoch nanoseconds.  |

    If not provided, `ts_created_ns` is assigned automatically at object creation.
    """

    ts_event_ns: int
    ts_created_ns: int = dataclasses.field(default_factory=time.time_ns)
