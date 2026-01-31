import time
import uuid

from onesecondtrader import events, messaging, models
from onesecondtrader.brokers.simulated import SimulatedBroker


class ResponseRecorder(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.responses: list[events.EventBase] = []
        super().__init__(event_bus)

    def _on_event(self, event: events.EventBase) -> None:
        self.responses.append(event)


def make_bar(
    symbol: str, open_: float, high: float, low: float, close: float
) -> events.market.BarReceived:
    return events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        bar_period=models.BarPeriod.MINUTE,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1000,
    )


def make_market_order(
    symbol: str = "AAPL",
    side: models.TradeSide = models.TradeSide.BUY,
    quantity: float = 100.0,
) -> events.requests.OrderSubmissionRequest:
    return events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        order_type=models.OrderType.MARKET,
        side=side,
        quantity=quantity,
    )


def make_limit_order(
    symbol: str = "AAPL",
    side: models.TradeSide = models.TradeSide.BUY,
    quantity: float = 100.0,
    limit_price: float = 100.0,
) -> events.requests.OrderSubmissionRequest:
    return events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        order_type=models.OrderType.LIMIT,
        side=side,
        quantity=quantity,
        limit_price=limit_price,
    )


def make_stop_order(
    symbol: str = "AAPL",
    side: models.TradeSide = models.TradeSide.BUY,
    quantity: float = 100.0,
    stop_price: float = 100.0,
) -> events.requests.OrderSubmissionRequest:
    return events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        order_type=models.OrderType.STOP,
        side=side,
        quantity=quantity,
        stop_price=stop_price,
    )


def make_stop_limit_order(
    symbol: str = "AAPL",
    side: models.TradeSide = models.TradeSide.BUY,
    quantity: float = 100.0,
    stop_price: float = 100.0,
    limit_price: float = 100.0,
) -> events.requests.OrderSubmissionRequest:
    return events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        order_type=models.OrderType.STOP_LIMIT,
        side=side,
        quantity=quantity,
        stop_price=stop_price,
        limit_price=limit_price,
    )


def setup_broker_and_recorder():
    bus = messaging.EventBus()
    broker = SimulatedBroker(bus)
    recorder = ResponseRecorder(bus)
    recorder._subscribe(
        events.responses.OrderAccepted,
        events.responses.OrderRejected,
        events.responses.CancellationAccepted,
        events.responses.CancellationRejected,
        events.responses.ModificationAccepted,
        events.responses.ModificationRejected,
        events.orders.FillEvent,
    )
    return bus, broker, recorder


def wait_for_events(bus: messaging.EventBus) -> None:
    bus.wait_until_system_idle()
    bus.wait_until_system_idle()


def test_connect_is_noop() -> None:
    bus = messaging.EventBus()
    broker = SimulatedBroker(bus)
    broker.connect()
    broker.shutdown()


def test_market_order_accepted() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_market_order()
    bus.publish(order)
    wait_for_events(bus)

    accepted = [
        r for r in recorder.responses if isinstance(r, events.responses.OrderAccepted)
    ]
    assert len(accepted) == 1
    assert accepted[0].associated_order_id == order.system_order_id
    broker.shutdown()
    recorder.shutdown()


def test_market_order_fills_on_next_bar() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_market_order(symbol="AAPL", quantity=50.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=110.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].associated_order_id == order.system_order_id
    assert fills[0].fill_price == 105.0
    assert fills[0].quantity_filled == 50.0
    broker.shutdown()
    recorder.shutdown()


def test_market_order_does_not_fill_on_different_symbol() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_market_order(symbol="AAPL")
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("MSFT", open_=105.0, high=110.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 0
    broker.shutdown()
    recorder.shutdown()


def test_invalid_market_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_market_order(quantity=0.0)
    bus.publish(order)
    wait_for_events(bus)

    rejected = [
        r for r in recorder.responses if isinstance(r, events.responses.OrderRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_limit_buy_fills_when_low_touches_limit() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(
        symbol="AAPL", side=models.TradeSide.BUY, limit_price=100.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=110.0, low=99.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 100.0
    broker.shutdown()
    recorder.shutdown()


def test_limit_buy_fills_at_open_when_open_below_limit() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(
        symbol="AAPL", side=models.TradeSide.BUY, limit_price=110.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_limit_buy_does_not_fill_when_low_above_limit() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", side=models.TradeSide.BUY, limit_price=90.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=110.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 0
    broker.shutdown()
    recorder.shutdown()


def test_limit_sell_fills_when_high_touches_limit() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(
        symbol="AAPL", side=models.TradeSide.SELL, limit_price=110.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 110.0
    broker.shutdown()
    recorder.shutdown()


def test_limit_sell_fills_at_open_when_open_above_limit() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(
        symbol="AAPL", side=models.TradeSide.SELL, limit_price=100.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_invalid_limit_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(limit_price=0.0)
    bus.publish(order)
    wait_for_events(bus)

    rejected = [
        r for r in recorder.responses if isinstance(r, events.responses.OrderRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_stop_buy_triggers_when_high_reaches_stop() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(symbol="AAPL", side=models.TradeSide.BUY, stop_price=110.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 110.0
    broker.shutdown()
    recorder.shutdown()


def test_stop_buy_fills_at_open_when_open_above_stop() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(symbol="AAPL", side=models.TradeSide.BUY, stop_price=100.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_stop_buy_does_not_trigger_when_high_below_stop() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(symbol="AAPL", side=models.TradeSide.BUY, stop_price=120.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 0
    broker.shutdown()
    recorder.shutdown()


def test_stop_sell_triggers_when_low_reaches_stop() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(symbol="AAPL", side=models.TradeSide.SELL, stop_price=100.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=95.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 100.0
    broker.shutdown()
    recorder.shutdown()


def test_stop_sell_fills_at_open_when_open_below_stop() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(symbol="AAPL", side=models.TradeSide.SELL, stop_price=110.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_invalid_stop_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_order(stop_price=0.0)
    bus.publish(order)
    wait_for_events(bus)

    rejected = [
        r for r in recorder.responses if isinstance(r, events.responses.OrderRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_stop_limit_buy_converts_to_limit_when_triggered() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_limit_order(
        symbol="AAPL", side=models.TradeSide.BUY, stop_price=110.0, limit_price=112.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar1 = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar1)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_stop_limit_sell_converts_to_limit_when_triggered() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_limit_order(
        symbol="AAPL", side=models.TradeSide.SELL, stop_price=100.0, limit_price=98.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar1 = make_bar("AAPL", open_=105.0, high=115.0, low=95.0, close=107.0)
    bus.publish(bar1)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].fill_price == 105.0
    broker.shutdown()
    recorder.shutdown()


def test_stop_limit_does_not_trigger_before_stop_reached() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_limit_order(
        symbol="AAPL", side=models.TradeSide.BUY, stop_price=120.0, limit_price=122.0
    )
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=105.0, high=115.0, low=100.0, close=107.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 0
    broker.shutdown()
    recorder.shutdown()


def test_invalid_stop_limit_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_stop_limit_order(stop_price=0.0, limit_price=100.0)
    bus.publish(order)
    wait_for_events(bus)

    rejected = [
        r for r in recorder.responses if isinstance(r, events.responses.OrderRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_cancel_pending_order_accepted() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", limit_price=90.0)
    bus.publish(order)
    wait_for_events(bus)

    cancel = events.requests.OrderCancellationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order.system_order_id,
        symbol="AAPL",
    )
    bus.publish(cancel)
    wait_for_events(bus)

    accepted = [
        r
        for r in recorder.responses
        if isinstance(r, events.responses.CancellationAccepted)
    ]
    assert len(accepted) == 1
    assert accepted[0].associated_order_id == order.system_order_id
    broker.shutdown()
    recorder.shutdown()


def test_cancel_nonexistent_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    cancel = events.requests.OrderCancellationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=uuid.uuid4(),
        symbol="AAPL",
    )
    bus.publish(cancel)
    wait_for_events(bus)

    rejected = [
        r
        for r in recorder.responses
        if isinstance(r, events.responses.CancellationRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_cancelled_order_does_not_fill() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", limit_price=100.0)
    bus.publish(order)
    wait_for_events(bus)

    cancel = events.requests.OrderCancellationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order.system_order_id,
        symbol="AAPL",
    )
    bus.publish(cancel)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=95.0, high=110.0, low=90.0, close=100.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 0
    broker.shutdown()
    recorder.shutdown()


def test_modify_pending_order_accepted() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", limit_price=90.0, quantity=100.0)
    bus.publish(order)
    wait_for_events(bus)

    modify = events.requests.OrderModificationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order.system_order_id,
        symbol="AAPL",
        quantity=50.0,
    )
    bus.publish(modify)
    wait_for_events(bus)

    accepted = [
        r
        for r in recorder.responses
        if isinstance(r, events.responses.ModificationAccepted)
    ]
    assert len(accepted) == 1
    assert accepted[0].associated_order_id == order.system_order_id
    broker.shutdown()
    recorder.shutdown()


def test_modify_nonexistent_order_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    modify = events.requests.OrderModificationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=uuid.uuid4(),
        symbol="AAPL",
        quantity=50.0,
    )
    bus.publish(modify)
    wait_for_events(bus)

    rejected = [
        r
        for r in recorder.responses
        if isinstance(r, events.responses.ModificationRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_invalid_modification_rejected() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", limit_price=90.0)
    bus.publish(order)
    wait_for_events(bus)

    modify = events.requests.OrderModificationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order.system_order_id,
        symbol="AAPL",
        quantity=-10.0,
    )
    bus.publish(modify)
    wait_for_events(bus)

    rejected = [
        r
        for r in recorder.responses
        if isinstance(r, events.responses.ModificationRejected)
    ]
    assert len(rejected) == 1
    broker.shutdown()
    recorder.shutdown()


def test_modified_order_uses_new_quantity() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_limit_order(symbol="AAPL", limit_price=100.0, quantity=100.0)
    bus.publish(order)
    wait_for_events(bus)

    modify = events.requests.OrderModificationRequest(
        ts_event_ns=time.time_ns(),
        system_order_id=order.system_order_id,
        symbol="AAPL",
        quantity=25.0,
    )
    bus.publish(modify)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=95.0, high=110.0, low=90.0, close=100.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].quantity_filled == 25.0
    broker.shutdown()
    recorder.shutdown()


def test_commission_per_unit_applied() -> None:
    bus = messaging.EventBus()
    broker = SimulatedBroker(bus)
    broker.commission_per_unit = 0.01
    recorder = ResponseRecorder(bus)
    recorder._subscribe(events.orders.FillEvent)

    order = make_market_order(symbol="AAPL", quantity=100.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=100.0, high=105.0, low=95.0, close=100.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].commission == 1.0
    broker.shutdown()
    recorder.shutdown()


def test_minimum_commission_applied() -> None:
    bus = messaging.EventBus()
    broker = SimulatedBroker(bus)
    broker.commission_per_unit = 0.001
    broker.minimum_commission_per_order = 5.0
    recorder = ResponseRecorder(bus)
    recorder._subscribe(events.orders.FillEvent)

    order = make_market_order(symbol="AAPL", quantity=10.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=100.0, high=105.0, low=95.0, close=100.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].commission == 5.0
    broker.shutdown()
    recorder.shutdown()


def test_zero_commission_by_default() -> None:
    bus, broker, recorder = setup_broker_and_recorder()

    order = make_market_order(symbol="AAPL", quantity=100.0)
    bus.publish(order)
    wait_for_events(bus)

    bar = make_bar("AAPL", open_=100.0, high=105.0, low=95.0, close=100.0)
    bus.publish(bar)
    wait_for_events(bus)

    fills = [r for r in recorder.responses if isinstance(r, events.orders.FillEvent)]
    assert len(fills) == 1
    assert fills[0].commission == 0.0
    broker.shutdown()
    recorder.shutdown()
