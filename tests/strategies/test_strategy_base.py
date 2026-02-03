import uuid

import pandas as pd

from onesecondtrader import events, messaging, models
from onesecondtrader.strategies.base import StrategyBase


class RecordingStrategy(StrategyBase):
    name = "Recording Strategy"
    symbols = ["AAPL"]

    def setup(self) -> None:
        pass

    def on_bar(self, event: events.market.BarReceived) -> None:
        pass


class RequestRecorder(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self.requests: list[events.requests.OrderSubmissionRequest] = []
        super().__init__(event_bus)
        self._subscribe(events.requests.OrderSubmissionRequest)

    def _on_event(self, event: events.EventBase) -> None:
        if isinstance(event, events.requests.OrderSubmissionRequest):
            self.requests.append(event)


class TestSubmitOrder:
    def test_submit_order_publishes_request_with_action_and_signal(self):
        bus = messaging.EventBus()
        strategy = RecordingStrategy(bus)
        recorder = RequestRecorder(bus)

        strategy._current_symbol = "AAPL"
        strategy._current_ts = pd.Timestamp("2026-01-01 10:00:00", tz="UTC")

        order_id = strategy.submit_order(
            order_type=models.OrderType.MARKET,
            side=models.TradeSide.BUY,
            quantity=100.0,
            action=models.ActionType.ENTRY_LONG,
            signal="test_signal",
        )

        bus.wait_until_system_idle()

        assert isinstance(order_id, uuid.UUID)
        assert len(recorder.requests) == 1

        request = recorder.requests[0]
        assert request.symbol == "AAPL"
        assert request.order_type == models.OrderType.MARKET
        assert request.side == models.TradeSide.BUY
        assert request.quantity == 100.0
        assert request.action == models.ActionType.ENTRY_LONG
        assert request.signal == "test_signal"

        strategy.shutdown()
        recorder.shutdown()

    def test_submit_order_action_and_signal_default_to_none(self):
        bus = messaging.EventBus()
        strategy = RecordingStrategy(bus)
        recorder = RequestRecorder(bus)

        strategy._current_symbol = "AAPL"
        strategy._current_ts = pd.Timestamp("2026-01-01 10:00:00", tz="UTC")

        strategy.submit_order(
            order_type=models.OrderType.LIMIT,
            side=models.TradeSide.SELL,
            quantity=50.0,
            limit_price=150.0,
        )

        bus.wait_until_system_idle()

        assert len(recorder.requests) == 1
        request = recorder.requests[0]
        assert request.action is None
        assert request.signal is None

        strategy.shutdown()
        recorder.shutdown()

    def test_submit_order_with_all_optional_fields(self):
        bus = messaging.EventBus()
        strategy = RecordingStrategy(bus)
        recorder = RequestRecorder(bus)

        strategy._current_symbol = "MSFT"
        strategy._current_ts = pd.Timestamp("2026-01-01 10:00:00", tz="UTC")

        strategy.submit_order(
            order_type=models.OrderType.STOP_LIMIT,
            side=models.TradeSide.BUY,
            quantity=25.0,
            limit_price=100.0,
            stop_price=95.0,
            action=models.ActionType.ADD,
            signal="add_to_position",
        )

        bus.wait_until_system_idle()

        request = recorder.requests[0]
        assert request.limit_price == 100.0
        assert request.stop_price == 95.0
        assert request.action == models.ActionType.ADD
        assert request.signal == "add_to_position"

        strategy.shutdown()
        recorder.shutdown()
