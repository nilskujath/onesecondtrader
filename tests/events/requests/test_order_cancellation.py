import uuid

from onesecondtrader.events.requests import OrderCancellationRequest


class TestOrderCancellationRequest:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderCancellationRequest(
            ts_event_ns=1000,
            system_order_id=order_id,
            symbol="AAPL",
        )
        assert event.ts_event_ns == 1000
        assert event.system_order_id == order_id
        assert event.symbol == "AAPL"
