from __future__ import annotations

import typing

from onesecondtrader import events


@typing.runtime_checkable
class EventSubscriberLike(typing.Protocol):
    def receive(self, event: events.bases.EventBase) -> None: ...
    def wait_until_idle(self) -> None: ...
