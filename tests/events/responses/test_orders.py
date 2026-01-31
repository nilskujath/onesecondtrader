import uuid

from onesecondtrader.events.responses import OrderAccepted, OrderRejected
from onesecondtrader.models import OrderRejectionReason


class TestOrderAccepted:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderAccepted(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert event.broker_order_id is None

    def test_fields_with_broker_order_id(self):
        order_id = uuid.uuid4()
        event = OrderAccepted(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            broker_order_id="BROKER123",
        )
        assert event.broker_order_id == "BROKER123"


class TestOrderRejected:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = OrderRejected(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            rejection_reason=OrderRejectionReason.UNKNOWN,
            rejection_message="Insufficient funds",
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert event.rejection_reason == OrderRejectionReason.UNKNOWN
        assert event.rejection_message == "Insufficient funds"
