import dataclasses
import time

from onesecondtrader import events, messaging


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class DummyEvent(events.EventBase):
    value: int


class RecordingSubscriber(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.received: list[events.EventBase] = []
        self.cleanup_called = False
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        self.received.append(event)

    def _cleanup(self) -> None:
        self.cleanup_called = True


class ExceptionSubscriber(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.exceptions: list[Exception] = []
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        raise ValueError("test error")

    def _on_exception(self, exc: Exception) -> None:
        self.exceptions.append(exc)


class PublishingSubscriber(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.received: list[events.EventBase] = []
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        self.received.append(event)
        if isinstance(event, DummyEvent) and event.value < 3:
            self._publish(DummyEvent(ts_event_ns=time.time_ns(), value=event.value + 1))


def test_subscriber_starts_worker_thread_on_init() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    assert sub._thread.is_alive()
    sub.shutdown()


def test_receive_enqueues_events_for_processing() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    event = DummyEvent(ts_event_ns=time.time_ns(), value=42)
    sub.receive(event)
    sub.wait_until_idle()

    assert len(sub.received) == 1
    assert sub.received[0] is event
    sub.shutdown()


def test_on_event_is_called_for_each_received_event() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    for i in range(5):
        sub.receive(DummyEvent(ts_event_ns=time.time_ns(), value=i))
    sub.wait_until_idle()

    assert len(sub.received) == 5
    values = [e.value for e in sub.received if isinstance(e, DummyEvent)]
    assert values == [0, 1, 2, 3, 4]
    sub.shutdown()


def test_wait_until_idle_blocks_until_queue_empty() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    for i in range(10):
        sub.receive(DummyEvent(ts_event_ns=time.time_ns(), value=i))

    sub.wait_until_idle()

    assert len(sub.received) == 10
    sub.shutdown()


def test_shutdown_stops_worker_thread() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    sub.shutdown()

    assert not sub._thread.is_alive()


def test_shutdown_unsubscribes_from_event_bus() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(DummyEvent)

    sub.shutdown()

    bus.publish(DummyEvent(ts_event_ns=time.time_ns(), value=99))

    assert len(sub.received) == 0


def test_subscribe_registers_for_event_types() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(DummyEvent)

    bus.publish(DummyEvent(ts_event_ns=time.time_ns(), value=1))
    bus.wait_until_system_idle()

    assert len(sub.received) == 1
    sub.shutdown()


def test_publish_publishes_events_to_bus() -> None:
    bus = messaging.EventBus()
    sub1 = PublishingSubscriber(bus)
    sub2 = RecordingSubscriber(bus)
    sub1._subscribe(DummyEvent)
    sub2._subscribe(DummyEvent)

    bus.publish(DummyEvent(ts_event_ns=time.time_ns(), value=1))
    bus.wait_until_system_idle()

    assert len(sub2.received) >= 3
    sub1.shutdown()
    sub2.shutdown()


def test_on_exception_is_called_when_on_event_raises() -> None:
    bus = messaging.EventBus()
    sub = ExceptionSubscriber(bus)

    sub.receive(DummyEvent(ts_event_ns=time.time_ns(), value=1))
    sub.wait_until_idle()

    assert len(sub.exceptions) == 1
    assert isinstance(sub.exceptions[0], ValueError)
    sub.shutdown()


def test_cleanup_is_called_after_event_loop_terminates() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    sub.shutdown()

    assert sub.cleanup_called


def test_events_not_enqueued_after_running_cleared() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)

    sub._running.clear()
    sub.receive(DummyEvent(ts_event_ns=time.time_ns(), value=99))

    assert sub._queue.empty()
    sub._running.set()
    sub.shutdown()
