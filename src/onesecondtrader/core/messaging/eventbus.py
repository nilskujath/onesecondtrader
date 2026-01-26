from __future__ import annotations

import collections
import threading
import typing

from onesecondtrader.core import events

if typing.TYPE_CHECKING:
    from .subscriber import Subscriber


class EventBus:
    def __init__(self) -> None:
        self._per_event_subscriptions: collections.defaultdict[
            type[events.bases.EventBase], set[Subscriber]
        ] = collections.defaultdict(set)
        self._subscribers: set[Subscriber] = set()
        self._lock: threading.Lock = threading.Lock()

    def subscribe(
        self,
        subscriber: Subscriber,
        event_type: type[events.bases.EventBase],
    ) -> None:
        with self._lock:
            self._subscribers.add(subscriber)
            self._per_event_subscriptions[event_type].add(subscriber)

    def unsubscribe(self, subscriber: Subscriber) -> None:
        with self._lock:
            for set_of_event_subscribers in self._per_event_subscriptions.values():
                set_of_event_subscribers.discard(subscriber)
            self._subscribers.discard(subscriber)

    def publish(self, event: events.bases.EventBase) -> None:
        # Intentionally matches exact event types only, not parent classes
        with self._lock:
            subscribers = self._per_event_subscriptions[type(event)].copy()
        for subscriber in subscribers:
            subscriber.receive(event)

    def wait_until_system_idle(self) -> None:
        with self._lock:
            subscribers = self._subscribers.copy()
        for subscriber in subscribers:
            subscriber.wait_until_idle()
