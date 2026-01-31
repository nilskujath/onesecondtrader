from __future__ import annotations

import collections
import threading
import typing

from onesecondtrader import events

if typing.TYPE_CHECKING:
    from .subscriber import Subscriber


class EventBus:
    """
    Event dispatch mechanism for propagating event objects to subscribers.

    The event bus maintains subscriptions between subscribers and concrete event types.
    Events published to the bus are synchronously delivered to all subscribers registered for the exact event type.

    Subscription management and event publication are thread-safe.
    Event delivery itself occurs outside the internal lock.
    """

    def __init__(self) -> None:
        """
        Initialize an empty event bus.

        The bus starts with no registered subscribers and no active subscriptions.
        """
        self._per_event_subscriptions: collections.defaultdict[
            type[events.EventBase], set[Subscriber]
        ] = collections.defaultdict(set)
        self._subscribers: set[Subscriber] = set()
        self._lock: threading.Lock = threading.Lock()

    def subscribe(
        self,
        subscriber: Subscriber,
        event_type: type[events.EventBase],
    ) -> None:
        """
        Register a subscriber for a specific event type.

        The subscriber will receive all future events whose concrete type matches `event_type`.

        Parameters:
            subscriber:
                Object receiving published events.
            event_type:
                Concrete event class the subscriber is interested in.
        """
        with self._lock:
            self._subscribers.add(subscriber)
            self._per_event_subscriptions[event_type].add(subscriber)

    def unsubscribe(self, subscriber: Subscriber) -> None:
        """
        Remove a subscriber from all event subscriptions.

        After unsubscription, the subscriber will no longer receive any events published on this bus.

        Parameters:
            subscriber:
                Subscriber to remove.
        """
        with self._lock:
            for set_of_event_subscribers in self._per_event_subscriptions.values():
                set_of_event_subscribers.discard(subscriber)
            self._subscribers.discard(subscriber)

    def publish(self, event: events.EventBase) -> None:
        """
        Publish an event to all subscribed listeners.

        Subscribers are matched strictly by the concrete type of the event.
        Parent classes and inheritance relationships are not considered.

        Parameters:
            event:
                Event instance to dispatch.
        """
        with self._lock:
            subscribers = self._per_event_subscriptions[type(event)].copy()
        for subscriber in subscribers:
            subscriber.receive(event)

    def wait_until_system_idle(self) -> None:
        """
        Block until all subscribers report an idle state.

        This method delegates to each subscriber's `wait_until_idle` method and returns only after all subscribers have completed any pending work.
        """
        with self._lock:
            subscribers = self._subscribers.copy()
        for subscriber in subscribers:
            subscriber.wait_until_idle()
