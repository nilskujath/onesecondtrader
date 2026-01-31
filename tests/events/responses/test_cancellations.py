import uuid

from onesecondtrader.events.responses import CancellationAccepted, CancellationRejected
from onesecondtrader.models import CancellationRejectionReason


class TestCancellationAccepted:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = CancellationAccepted(
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
        event = CancellationAccepted(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            broker_order_id="BROKER123",
        )
        assert event.broker_order_id == "BROKER123"


class TestCancellationRejected:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = CancellationRejected(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            rejection_reason=CancellationRejectionReason.UNKNOWN,
            rejection_message="Order already cancelled",
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert event.rejection_reason == CancellationRejectionReason.UNKNOWN
        assert event.rejection_message == "Order already cancelled"
