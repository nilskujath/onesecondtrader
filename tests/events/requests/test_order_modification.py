import uuid

from onesecondtrader.events.requests import OrderModificationRequest


class TestOrderModificationRequest:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderModificationRequest(
            ts_event_ns=1000,
            system_order_id=order_id,
            symbol="AAPL",
        )
        assert event.ts_event_ns == 1000
        assert event.system_order_id == order_id
        assert event.symbol == "AAPL"
        assert event.quantity is None
        assert event.limit_price is None
        assert event.stop_price is None
