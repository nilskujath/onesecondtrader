"""
Read first: [Event Messages](./event_messages.md).

---
This module defines the central event bus for publish-subscribe communication.

EventBus is the core messaging infrastructure that routes events between system
components.
Subscribers register interest in specific event types and receive events when publishers
dispatch them.
Event routing uses exact type matching, so subscribing to a base class will not receive
events of derived types.
---
"""

import collections
import threading
import typing

from .event_messages import EventBase


@typing.runtime_checkable
class EventSubscriberLike(typing.Protocol):
    def receive(self, event: EventBase) -> None: ...
    def wait_until_idle(self) -> None: ...


class EventBus:
    def __init__(self) -> None:
        self._per_event_subscriptions: collections.defaultdict[
            type[EventBase], set[EventSubscriberLike]
        ] = collections.defaultdict(set)
        self._subscribers: set[EventSubscriberLike] = set()
        self._lock: threading.Lock = threading.Lock()

    def subscribe(
        self, subscriber: EventSubscriberLike, event_type: type[EventBase]
    ) -> None:
        with self._lock:
            self._subscribers.add(subscriber)
            self._per_event_subscriptions[event_type].add(subscriber)

    def unsubscribe(self, subscriber: EventSubscriberLike) -> None:
        with self._lock:
            for set_of_event_subscribers in self._per_event_subscriptions.values():
                set_of_event_subscribers.discard(subscriber)
            self._subscribers.discard(subscriber)

    def publish(self, event: EventBase) -> None:
        with self._lock:
            subscribers = self._per_event_subscriptions[type(event)].copy()
        for subscriber in subscribers:
            subscriber.receive(event)

    def wait_until_system_idle(self) -> None:
        with self._lock:
            subscribers = self._subscribers.copy()
        for subscriber in subscribers:
            subscriber.wait_until_idle()
