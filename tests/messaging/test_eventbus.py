import dataclasses
import threading
import time

from onesecondtrader import events, messaging


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class EventA(events.EventBase):
    value: int


@dataclasses.dataclass(kw_only=True, frozen=True, slots=True)
class EventB(events.EventBase):
    value: str


class RecordingSubscriber(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.received: list[events.EventBase] = []
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        self.received.append(event)


def test_subscribe_registers_subscriber_for_event_type() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(EventA)

    event = EventA(ts_event_ns=time.time_ns(), value=42)
    bus.publish(event)
    bus.wait_until_system_idle()

    assert len(sub.received) == 1
    assert sub.received[0] is event
    sub.shutdown()


def test_unsubscribe_removes_subscriber_from_all_subscriptions() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(EventA, EventB)

    bus.unsubscribe(sub)

    bus.publish(EventA(ts_event_ns=time.time_ns(), value=1))
    bus.publish(EventB(ts_event_ns=time.time_ns(), value="x"))
    bus.wait_until_system_idle()

    assert len(sub.received) == 0
    sub.shutdown()


def test_publish_delivers_events_to_subscribed_listeners() -> None:
    bus = messaging.EventBus()
    sub1 = RecordingSubscriber(bus)
    sub2 = RecordingSubscriber(bus)
    sub1._subscribe(EventA)
    sub2._subscribe(EventA)

    event = EventA(ts_event_ns=time.time_ns(), value=99)
    bus.publish(event)
    bus.wait_until_system_idle()

    assert len(sub1.received) == 1
    assert len(sub2.received) == 1
    assert sub1.received[0] is event
    assert sub2.received[0] is event
    sub1.shutdown()
    sub2.shutdown()


def test_publish_matches_exact_event_type_only() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(EventA)

    bus.publish(EventB(ts_event_ns=time.time_ns(), value="ignored"))
    bus.wait_until_system_idle()

    assert len(sub.received) == 0
    sub.shutdown()


def test_multiple_event_types_per_subscriber() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(EventA, EventB)

    event_a = EventA(ts_event_ns=time.time_ns(), value=1)
    event_b = EventB(ts_event_ns=time.time_ns(), value="hello")
    bus.publish(event_a)
    bus.publish(event_b)
    bus.wait_until_system_idle()

    assert len(sub.received) == 2
    assert event_a in sub.received
    assert event_b in sub.received
    sub.shutdown()


def test_wait_until_system_idle_blocks_until_all_idle() -> None:
    bus = messaging.EventBus()
    sub = RecordingSubscriber(bus)
    sub._subscribe(EventA)

    for i in range(10):
        bus.publish(EventA(ts_event_ns=time.time_ns(), value=i))

    bus.wait_until_system_idle()

    assert len(sub.received) == 10
    sub.shutdown()


def test_thread_safety_of_subscribe_and_publish() -> None:
    bus = messaging.EventBus()
    subscribers: list[RecordingSubscriber] = []
    errors: list[Exception] = []

    def create_and_subscribe() -> None:
        try:
            sub = RecordingSubscriber(bus)
            sub._subscribe(EventA)
            subscribers.append(sub)
        except Exception as e:
            errors.append(e)

    def publish_events() -> None:
        try:
            for i in range(20):
                bus.publish(EventA(ts_event_ns=time.time_ns(), value=i))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=create_and_subscribe) for _ in range(5)] + [
        threading.Thread(target=publish_events) for _ in range(3)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    bus.wait_until_system_idle()

    assert len(errors) == 0
    for sub in subscribers:
        sub.shutdown()
