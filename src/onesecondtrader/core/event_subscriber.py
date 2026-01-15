"""
Read first: [Event Bus](./event_bus.md), [Event Messages](./event_messages.md).

---
This module defines the base class for components that subscribe to events.

EventSubscriber provides a threaded event loop that receives events from the event bus.
Each subscriber runs in its own thread and processes events from its internal queue.
Components that only subscribe inherit from this class directly.
Components that both subscribe and publish inherit from both EventSubscriber and
EventPublisher.
---
"""

import abc
import queue
import threading

from .event_bus import EventBus
from .event_messages import EventBase


class EventSubscriber(abc.ABC):
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._queue: queue.Queue[EventBase | None] = queue.Queue()
        self._running = True
        self._thread = threading.Thread(
            target=self._event_loop, name=self.__class__.__name__
        )
        self._thread.start()

    def receive(self, event: EventBase) -> None:
        if self._running:
            self._queue.put(event)

    def wait_until_idle(self) -> None:
        if not self._running:
            return
        self._queue.join()

    def shutdown(self) -> None:
        if not self._running:
            return
        self._running = False
        self._event_bus.unsubscribe(self)
        self._queue.put(None)
        if threading.current_thread() is not self._thread:
            self._thread.join()

    def _subscribe(self, *event_types: type[EventBase]) -> None:
        for event_type in event_types:
            self._event_bus.subscribe(self, event_type)

    def _event_loop(self) -> None:
        while True:
            event = self._queue.get()
            if event is None:
                self._queue.task_done()
                break
            try:
                self._on_event(event)
            except Exception:
                self._on_exception()
            finally:
                self._queue.task_done()
        self._cleanup()

    def _on_exception(self) -> None:
        pass

    def _cleanup(self) -> None:
        pass

    @abc.abstractmethod
    def _on_event(self, event: EventBase) -> None: ...
