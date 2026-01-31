import uuid

from onesecondtrader.events.orders import OrderExpired


class TestOrderExpired:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderExpired(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            symbol="AAPL",
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert event.broker_order_id is None
        assert event.symbol == "AAPL"
