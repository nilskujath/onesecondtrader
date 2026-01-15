import dataclasses
import threading
import time
import uuid

import pandas as pd
import pytest

from onesecondtrader.core.domain_models import BarPeriod, OrderSide, OrderType
from onesecondtrader.core.event_bus import EventBus
from onesecondtrader.core.event_messages import (
    AcceptedOrderSubmission,
    ConfirmedOrderFilled,
    EventBase,
    NewBar,
    RequestOrderSubmission,
)
from onesecondtrader.core.event_publisher import EventPublisher
from onesecondtrader.core.event_subscriber import EventSubscriber


@dataclasses.dataclass(kw_only=True, frozen=True)
class _TestEvent(EventBase):
    value: int = 0


@dataclasses.dataclass(kw_only=True, frozen=True)
class _AnotherTestEvent(EventBase):
    data: str = ""


class _TestSubscriber(EventSubscriber):
    def __init__(self, event_bus: EventBus) -> None:
        self.received_events: list[EventBase] = []
        self.cleanup_called = False
        super().__init__(event_bus)

    def _on_event(self, event: EventBase) -> None:
        self.received_events.append(event)

    def _cleanup(self) -> None:
        self.cleanup_called = True


class _FailingSubscriber(EventSubscriber):
    def __init__(self, event_bus: EventBus) -> None:
        super().__init__(event_bus)
        self._subscribe(_TestEvent)

    def _on_event(self, event: EventBase) -> None:
        raise ValueError("Intentional failure")


class TestDomainModels:
    def test_order_type_values_exist(self) -> None:
        assert OrderType.LIMIT
        assert OrderType.MARKET
        assert OrderType.STOP
        assert OrderType.STOP_LIMIT

    def test_order_side_values_exist(self) -> None:
        assert OrderSide.BUY
        assert OrderSide.SELL

    def test_bar_period_values_exist(self) -> None:
        assert BarPeriod.SECOND
        assert BarPeriod.MINUTE
        assert BarPeriod.HOUR
        assert BarPeriod.DAY


class TestEventMessages:
    def test_event_base_ts_created_auto_generates(self) -> None:
        before = pd.Timestamp.now(tz="UTC")
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"))
        after = pd.Timestamp.now(tz="UTC")
        assert before <= event.ts_created <= after

    def test_event_base_is_frozen(self) -> None:
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=42)
        with pytest.raises(dataclasses.FrozenInstanceError):
            event.value = 100  # type: ignore[misc]

    def test_new_bar_fields(self) -> None:
        ts = pd.Timestamp.now(tz="UTC")
        bar = NewBar(
            ts_event=ts,
            symbol="AAPL",
            bar_period=BarPeriod.MINUTE,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1000,
        )
        assert bar.symbol == "AAPL"
        assert bar.volume == 1000

    def test_new_bar_volume_optional(self) -> None:
        ts = pd.Timestamp.now(tz="UTC")
        bar = NewBar(
            ts_event=ts,
            symbol="AAPL",
            bar_period=BarPeriod.MINUTE,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
        )
        assert bar.volume is None

    def test_broker_response_requires_ts_broker(self) -> None:
        ts = pd.Timestamp.now(tz="UTC")
        event = AcceptedOrderSubmission(
            ts_event=ts,
            ts_broker=ts,
            order_id=uuid.uuid4(),
        )
        assert event.ts_broker == ts

    def test_request_order_submission_generates_order_id(self) -> None:
        ts = pd.Timestamp.now(tz="UTC")
        event = RequestOrderSubmission(
            ts_event=ts,
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=100,
        )
        assert event.order_id is not None

    def test_confirmed_order_filled_generates_fill_id(self) -> None:
        ts = pd.Timestamp.now(tz="UTC")
        event = ConfirmedOrderFilled(
            ts_event=ts,
            ts_broker=ts,
            associated_order_id=uuid.uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity_filled=100,
            fill_price=150.0,
            commission=1.0,
        )
        assert event.fill_id is not None
        assert event.exchange == "SIMULATED"


class TestEventBus:
    def test_subscribe_and_publish(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=42)
        bus.publish(event)
        bus.wait_until_system_idle()
        sub.shutdown()
        assert len(sub.received_events) == 1
        assert sub.received_events[0] == event

    def test_multiple_subscribers_receive_same_event(self) -> None:
        bus = EventBus()
        sub1 = _TestSubscriber(bus)
        sub2 = _TestSubscriber(bus)
        sub1._subscribe(_TestEvent)
        sub2._subscribe(_TestEvent)
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=42)
        bus.publish(event)
        bus.wait_until_system_idle()
        sub1.shutdown()
        sub2.shutdown()
        assert len(sub1.received_events) == 1
        assert len(sub2.received_events) == 1

    def test_unsubscribe_stops_receiving(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        event1 = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=1)
        bus.publish(event1)
        bus.wait_until_system_idle()
        bus.unsubscribe(sub)
        event2 = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=2)
        bus.publish(event2)
        time.sleep(0.01)
        sub.shutdown()
        assert len(sub.received_events) == 1
        assert sub.received_events[0] == event1

    def test_exact_type_matching(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        other_event = _AnotherTestEvent(ts_event=pd.Timestamp.now(tz="UTC"), data="x")
        bus.publish(other_event)
        bus.wait_until_system_idle()
        sub.shutdown()
        assert len(sub.received_events) == 0

    def test_subscribe_to_multiple_event_types(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent, _AnotherTestEvent)
        event1 = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=1)
        event2 = _AnotherTestEvent(ts_event=pd.Timestamp.now(tz="UTC"), data="x")
        bus.publish(event1)
        bus.publish(event2)
        bus.wait_until_system_idle()
        sub.shutdown()
        assert len(sub.received_events) == 2


class TestEventSubscriber:
    def test_cleanup_called_on_shutdown(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        sub.shutdown()
        assert sub.cleanup_called

    def test_wait_until_idle_returns_immediately_after_shutdown(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        sub.shutdown()
        waiter = threading.Thread(target=sub.wait_until_idle)
        waiter.start()
        waiter.join(timeout=0.5)
        assert not waiter.is_alive()

    def test_exception_in_on_event_does_not_hang_wait_until_idle(self) -> None:
        bus = EventBus()
        sub = _FailingSubscriber(bus)
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"))
        bus.publish(event)

        def wait_with_timeout() -> bool:
            try:
                bus.wait_until_system_idle()
                return True
            except Exception:
                return False

        waiter = threading.Thread(target=wait_with_timeout)
        waiter.start()
        waiter.join(timeout=1.0)
        assert not waiter.is_alive()
        sub.shutdown()

    def test_shutdown_is_idempotent(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        sub.shutdown()
        sub.shutdown()

    def test_receive_after_shutdown_does_not_deadlock_wait_until_idle(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)

        def _shutdown() -> None:
            sub.shutdown()

        t = threading.Thread(target=_shutdown)
        t.start()
        t.join(timeout=2)
        assert not t.is_alive()

        sub.receive(_TestEvent(ts_event=pd.Timestamp.now(tz="UTC")))

        waiter = threading.Thread(target=sub.wait_until_idle)
        waiter.start()
        waiter.join(timeout=0.5)
        assert not waiter.is_alive()


class TestEventPublisher:
    def test_publish_sends_to_bus(self) -> None:
        bus = EventBus()
        sub = _TestSubscriber(bus)
        sub._subscribe(_TestEvent)
        publisher = EventPublisher(bus)
        event = _TestEvent(ts_event=pd.Timestamp.now(tz="UTC"), value=99)
        publisher._publish(event)
        bus.wait_until_system_idle()
        sub.shutdown()
        assert len(sub.received_events) == 1
        assert sub.received_events[0] == event
