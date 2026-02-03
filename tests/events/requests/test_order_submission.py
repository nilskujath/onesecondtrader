import uuid

from onesecondtrader.events.requests import OrderSubmissionRequest
from onesecondtrader.models import ActionType, OrderType, TradeSide


class TestOrderSubmissionRequest:
    def test_fields(self):
        event = OrderSubmissionRequest(
            ts_event_ns=1000,
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=TradeSide.BUY,
            quantity=100.0,
        )
        assert event.ts_event_ns == 1000
        assert event.symbol == "AAPL"
        assert event.order_type == OrderType.MARKET
        assert event.side == TradeSide.BUY
        assert event.quantity == 100.0
        assert isinstance(event.system_order_id, uuid.UUID)
        assert event.limit_price is None
        assert event.stop_price is None
        assert event.action is None
        assert event.signal is None

    def test_action_and_signal_fields(self):
        event = OrderSubmissionRequest(
            ts_event_ns=2000,
            symbol="MSFT",
            order_type=OrderType.LIMIT,
            side=TradeSide.SELL,
            quantity=50.0,
            limit_price=150.0,
            action=ActionType.EXIT_LONG,
            signal="ma_crossover",
        )
        assert event.action == ActionType.EXIT_LONG
        assert event.signal == "ma_crossover"
