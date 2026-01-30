from onesecondtrader.events import EventBase


class TestEventBase:
    def test_fields(self):
        event = EventBase(ts_event_ns=1000)
        assert event.ts_event_ns == 1000
        assert isinstance(event.ts_created_ns, int)
