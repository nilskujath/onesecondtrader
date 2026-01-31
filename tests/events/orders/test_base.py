import uuid

from onesecondtrader.events.orders import OrderBase


class TestOrderBase:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderBase(
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

    def test_fields_with_broker_order_id(self):
        order_id = uuid.uuid4()
        event = OrderBase(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            broker_order_id="BROKER123",
            symbol="AAPL",
        )
        assert event.broker_order_id == "BROKER123"
