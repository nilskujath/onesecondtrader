import time
import uuid

from onesecondtrader import events, messaging, models
from onesecondtrader.brokers.base import BrokerBase


class RecordingBroker(BrokerBase):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.submit_calls: list[events.requests.OrderSubmissionRequest] = []
        self.cancel_calls: list[events.requests.OrderCancellationRequest] = []
        self.modify_calls: list[events.requests.OrderModificationRequest] = []
        self.connect_called = False
        super().__init__(event_bus)

    def connect(self) -> None:
        self.connect_called = True

    def _on_submit_order(self, event: events.requests.OrderSubmissionRequest) -> None:
        self.submit_calls.append(event)

    def _on_cancel_order(self, event: events.requests.OrderCancellationRequest) -> None:
        self.cancel_calls.append(event)

    def _on_modify_order(self, event: events.requests.OrderModificationRequest) -> None:
        self.modify_calls.append(event)


class ResponseRecorder(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.responses: list[events.EventBase] = []
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        self.responses.append(event)


def make_submission_request(
    symbol: str = "AAPL",
) -> events.requests.OrderSubmissionRequest:
    return events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        order_type=models.OrderType.MARKET,
        side=models.TradeSide.BUY,
        quantity=100.0,
    )


def make_cancellation_request(
    order_id: uuid.UUID, symbol: str = "AAPL"
) -> events.requests.OrderCancellationRequest:
    return events.requests.OrderCancellationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order_id,
        symbol=symbol,
    )


def make_modification_request(
    order_id: uuid.UUID, symbol: str = "AAPL"
) -> events.requests.OrderModificationRequest:
    return events.requests.OrderModificationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order_id,
        symbol=symbol,
        quantity=50.0,
    )


def test_broker_subscribes_to_order_requests() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)

    submit_event = make_submission_request()
    bus.publish(submit_event)
    bus.wait_until_system_idle()

    assert len(broker.submit_calls) == 1
    assert broker.submit_calls[0] is submit_event
    broker.shutdown()


def test_broker_dispatches_cancellation_request() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)

    order_id = uuid.uuid4()
    cancel_event = make_cancellation_request(order_id)
    bus.publish(cancel_event)
    bus.wait_until_system_idle()

    assert len(broker.cancel_calls) == 1
    assert broker.cancel_calls[0] is cancel_event
    broker.shutdown()


def test_broker_dispatches_modification_request() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)

    order_id = uuid.uuid4()
    modify_event = make_modification_request(order_id)
    bus.publish(modify_event)
    bus.wait_until_system_idle()

    assert len(broker.modify_calls) == 1
    assert broker.modify_calls[0] is modify_event
    broker.shutdown()


def test_connect_is_callable() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)

    broker.connect()

    assert broker.connect_called
    broker.shutdown()


def test_disconnect_shuts_down_subscriber() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)

    broker.disconnect()

    assert not broker._thread.is_alive()


def test_respond_publishes_to_event_bus() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)
    recorder = ResponseRecorder(bus)
    recorder._subscribe(events.responses.OrderAccepted)

    response = events.responses.OrderAccepted(
        ts_event_ns=time.time_ns(),
        ts_broker_ns=time.time_ns(),
        associated_order_id=uuid.uuid4(),
    )
    broker._respond(response)
    bus.wait_until_system_idle()

    assert len(recorder.responses) == 1
    assert recorder.responses[0] is response
    broker.shutdown()
    recorder.shutdown()


def test_unhandled_event_is_ignored() -> None:
    bus = messaging.EventBus()
    broker = RecordingBroker(bus)
    broker._subscribe(events.market.BarReceived)

    bar = events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol="AAPL",
        bar_period=models.BarPeriod.MINUTE,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000,
    )
    bus.publish(bar)
    bus.wait_until_system_idle()

    assert len(broker.submit_calls) == 0
    assert len(broker.cancel_calls) == 0
    assert len(broker.modify_calls) == 0
    broker.shutdown()
