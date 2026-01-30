import uuid

from onesecondtrader.events.requests import OrderSubmissionRequest
from onesecondtrader.models import OrderType, TradeSide


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
