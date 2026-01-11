"""
Read first: [`events.py`](./events.md), [`component.py`](./component.md).

---
This module defines the `EventBus` class.

The event bus provides a publish–subscribe mechanism for event-driven systems.
It maintains subscriptions between event types and components and delivers
published events to all subscribed components in a thread-safe manner.
---
"""

import collections
import threading

from .component import Component
from .events import Event


class EventBus:
    """
    Central event-dispatch mechanism for the system.

    The event bus manages subscriptions between event types and components and
    forwards published events to all subscribed components.
    """

    def __init__(self) -> None:
        """
        Initialize the event bus.

        Sets up internal data structures for managing subscriptions and registered
        components and initializes a lock to ensure thread-safe access.
        """
        self._subscriptions: collections.defaultdict[type[Event], set[Component]] = (
            collections.defaultdict(set)
        )
        self._components: set[Component] = set()
        self._lock: threading.Lock = threading.Lock()

    def subscribe(self, subscriber: Component, *event_types: type[Event]) -> None:
        """
        Subscribe a component to one or more event types.

        The subscriber will receive all future events whose type matches one of the
        specified event types.
        """
        with self._lock:
            self._components.add(subscriber)
            for event_type in event_types:
                self._subscriptions[event_type].add(subscriber)

    def unsubscribe(self, subscriber: Component) -> None:
        """
        Remove a component from all event subscriptions.

        After unsubscription, the component will no longer receive published events.
        """
        with self._lock:
            for component_set in self._subscriptions.values():
                component_set.discard(subscriber)
            self._components.discard(subscriber)

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribed components.

        The event is delivered to each subscriber by invoking its `receive()` method.
        """
        with self._lock:
            components = self._subscriptions[type(event)].copy()
        for component in components:
            component.receive(event)

    def wait_until_idle(self) -> None:
        """
        Block until all components have processed their queued events.

        This method is primarily used in backtesting to enforce deterministic,
        system-wide synchronization.
        """
        with self._lock:
            components = self._components.copy()
        for component in components:
            component.join_queue()
