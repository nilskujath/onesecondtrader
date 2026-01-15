"""
Read first: [Event Bus](./event_bus.md), [Event Messages](./event_messages.md).

---
This module defines the base class for components that publish events.

EventPublisher provides a minimal interface for publishing events to the event bus.
Components that only publish events inherit from this class directly.
Components that both subscribe and publish inherit from both EventSubscriber and
EventPublisher.
---
"""

from .event_bus import EventBus
from .event_messages import EventBase


class EventPublisher:
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    def _publish(self, event: EventBase) -> None:
        self._event_bus.publish(event)
