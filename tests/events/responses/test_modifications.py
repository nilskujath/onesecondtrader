import uuid

from onesecondtrader.events.responses import ModificationAccepted, ModificationRejected
from onesecondtrader.models import ModificationRejectionReason


class TestModificationAccepted:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = ModificationAccepted(
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
        event = ModificationAccepted(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            broker_order_id="BROKER123",
        )
        assert event.broker_order_id == "BROKER123"


class TestModificationRejected:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = ModificationRejected(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            rejection_reason=ModificationRejectionReason.UNKNOWN,
            rejection_message="Order already filled",
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert event.rejection_reason == ModificationRejectionReason.UNKNOWN
        assert event.rejection_message == "Order already filled"
