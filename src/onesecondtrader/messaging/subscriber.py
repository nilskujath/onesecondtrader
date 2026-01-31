import abc
import queue
import threading

from onesecondtrader import events, messaging


class Subscriber(abc.ABC):
    """
    Abstract base class for event bus subscribers.

    A subscriber receives events from an event bus and processes them asynchronously in a dedicated worker thread.
    Incoming events are queued and handled sequentially.

    Subclasses implement `_on_event` to define event-specific behavior.
    """

    def __init__(self, event_bus: messaging.EventBus) -> None:
        """
        Initialize the subscriber and start its event-processing thread.

        Parameters:
            event_bus:
                Event bus used for subscribing to and publishing events.
        """
        self._event_bus = event_bus
        self._queue: queue.Queue[events.EventBase | None] = queue.Queue()

        self._running: threading.Event = threading.Event()
        self._running.set()

        self._thread = threading.Thread(
            target=self._event_loop, name=self.__class__.__name__
        )
        self._thread.start()

    def receive(self, event: events.EventBase) -> None:
        """
        Receive an event from the event bus.

        The event is enqueued for asynchronous processing if the subscriber is running.

        Parameters:
            event:
                Event instance delivered by the event bus.
        """
        if self._running.is_set():
            self._queue.put(event)

    def wait_until_idle(self) -> None:
        """
        Block until all queued events have been processed.

        If the subscriber is not running, this method returns immediately.
        """
        if not self._running.is_set():
            return

        self._queue.join()

    def shutdown(self) -> None:
        """
        Shut down the subscriber and stop event processing.

        The subscriber is unsubscribed from the event bus, its worker thread is signaled to terminate, and all pending events are processed before shutdown completes.
        """
        if not self._running.is_set():
            return

        self._event_bus.unsubscribe(self)
        self._running.clear()
        self._queue.put(None)

        if threading.current_thread() is not self._thread:
            self._thread.join()

    def _subscribe(self, *event_types: type[events.EventBase]) -> None:
        """
        Subscribe this subscriber to one or more event types.

        Parameters:
            *event_types:
                Concrete event classes to subscribe to.
        """
        for event_type in event_types:
            self._event_bus.subscribe(self, event_type)

    def _publish(self, event: events.EventBase) -> None:
        """
        Publish an event to the event bus.

        Parameters:
            event:
                Event instance to publish.
        """
        self._event_bus.publish(event)

    def _event_loop(self) -> None:
        """
        Internal worker loop for processing queued events.

        This method runs in a dedicated thread and should not be called directly.
        """
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
        """
        Handle an exception raised during event processing.

        Subclasses may override this method to implement logging or recovery behavior.
        The default implementation ignores the exception.

        Parameters:
            exc:
                Exception raised while processing an event.
        """
        pass

    def _cleanup(self) -> None:
        """
        Perform cleanup after the event loop terminates.

        Subclasses may override this method to release resources or emit shutdown notifications.
        """
        pass

    @abc.abstractmethod
    def _on_event(self, event: events.EventBase) -> None:
        """
        Handle a single event.

        This method is invoked sequentially for each event received by the subscriber.
        Implementations must not block indefinitely, as `wait_until_idle` relies on timely completion.

        Parameters:
            event:
                Event instance to handle.
        """
        ...
