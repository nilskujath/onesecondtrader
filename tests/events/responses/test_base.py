import uuid

from onesecondtrader.events.responses import ResponseBase


class TestResponseBase:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = ResponseBase(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
