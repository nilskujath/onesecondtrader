import abc
import queue
import threading

from onesecondtrader.core import events
from .eventbus import EventBus


class Subscriber(abc.ABC):
    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._queue: queue.Queue[events.bases.EventBase | None] = queue.Queue()
        self._running: threading.Event = threading.Event()
        self._running.set()
        self._thread = threading.Thread(
            target=self._event_loop, name=self.__class__.__name__
        )
        self._thread.start()

    def receive(self, event: events.bases.EventBase) -> None:
        if self._running.is_set():
            self._queue.put(event)

    def wait_until_idle(self) -> None:
        if not self._running.is_set():
            return
        self._queue.join()

    def shutdown(self) -> None:
        if not self._running.is_set():
            return
        self._event_bus.unsubscribe(self)
        self._running.clear()
        self._queue.put(None)
        if threading.current_thread() is not self._thread:
            self._thread.join()

    def _subscribe(self, *event_types: type[events.bases.EventBase]) -> None:
        for event_type in event_types:
            self._event_bus.subscribe(self, event_type)

    def _publish(self, event: events.bases.EventBase) -> None:
        self._event_bus.publish(event)

    def _event_loop(self) -> None:
        while True:
            event = self._queue.get()
            if event is None:
                self._queue.task_done()
                break
            try:
                self._on_event(event)
            except Exception as exc:
                self._on_exception(exc)
            finally:
                self._queue.task_done()
        self._cleanup()

    def _on_exception(self, exc: Exception) -> None:
        # Override in subclass to log or handle exceptions
        pass

    def _cleanup(self) -> None:
        pass

    @abc.abstractmethod
    def _on_event(self, event: events.bases.EventBase) -> None:
        # Must not block indefinitely; wait_until_idle() has no timeout
        ...
