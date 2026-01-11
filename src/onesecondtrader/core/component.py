"""
Read first: [`events.py`](./events.md), [`eventbus.py`](./eventbus.md).

---
This module defines the `Component` class.

In an event-driven system, components interact exclusively via event messages.
The `Component` class is an abstract base class that defines a common interface for
publishing and receiving such messages and is intended to be subclassed by all system
components.
---
"""

import abc
import queue
import threading

from .events import Event
from .eventbus import EventBus


class Component(abc.ABC):
    """
    Abstract base class for all system components.

    Incoming events are delivered via `receive()` and stored in an internal queue.
    A dedicated thread runs an event loop that consumes queued events and dispatches
    them to `_process()`, which subclasses must implement.
    For publication, `publish()` forwards events to the event bus.
    The `join_queue()` method is used by the event bus to block until all queued events
    have been processed, which is useful for deterministic, stepwise execution in
    backtesting.
    """

    def __init__(self, eventbus: EventBus) -> None:
        """
        Initialize the component and start its event-loop thread.

        Stores a reference to the event bus, creates an internal queue for incoming
        events, and starts a non-daemon thread for the event loop that runs until
        shutdown.
        """
        self._event_bus = eventbus
        self._incoming_event_queue: queue.Queue[Event | None] = queue.Queue()
        self._thread: threading.Thread = threading.Thread(
            target=self._event_loop,
            name=self.__class__.__name__,
            daemon=False,
        )
        self._thread.start()

    def publish(self, event: Event) -> None:
        """
        Wrapper for the event bus's `publish()` method.

        For convenience, this method can be used by subclasses to publish events via the
        event bus's publication mechanism.
        """
        self._event_bus.publish(event)

    def receive(self, event: Event) -> None:
        """
        Store incoming events in the component's queue.

        This method is typically called by the event bus when an event is published that
        the component has subscribed to.
        It simply puts the event in the queue for processing by the subscribed
        component.
        """
        self._incoming_event_queue.put(event)

    def join_queue(self) -> None:
        """
        Block until all queued events have been processed.

        This method is used by the event bus to block until all queued events have been
        processed.
        This is useful for deterministic, stepwise execution in backtesting.
        """
        self._incoming_event_queue.join()

    def _event_loop(self) -> None:
        """
        Event-processing loop executed in the component’s dedicated thread.

        The loop continuously retrieves events from the `incoming_event_queue`,
        processes each event via `_process()`, and signals completion with
        `task_done()`.
        Execution terminates upon receipt of a `None` sentinel, at which point
        `_shutdown()` is invoked before exiting the thread to ensure proper cleanup.
        """
        while True:
            incoming_event = self._incoming_event_queue.get()
            if incoming_event is None:
                self._shutdown()
                self._incoming_event_queue.task_done()
                break
            self._process(incoming_event)
            self._incoming_event_queue.task_done()

    @abc.abstractmethod
    def _process(self, event: Event) -> None:
        """
        Process a single event.

        This method is invoked by the event loop for each incoming event.
        Subclasses must implement it to define event-handling behavior.
        """
        pass

    def _shutdown(self) -> None:
        """
        Perform cleanup when the component is shutting down.

        Called by `_event_loop()` when a `None` sentinel is received.
        Subclasses may override this method to perform cleanup tasks such as closing
        files or connections before the thread exits.
        """
        pass
