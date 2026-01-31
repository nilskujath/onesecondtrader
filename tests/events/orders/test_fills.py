import uuid

from onesecondtrader.events.orders import FillEvent
from onesecondtrader.models import TradeSide


class TestFillEvent:
    def test_fields(self):
        order_id = uuid.uuid4()
        event = FillEvent(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            symbol="AAPL",
            side=TradeSide.BUY,
            quantity_filled=100.0,
            fill_price=150.25,
            commission=1.0,
        )
        assert event.ts_event_ns == 1000
        assert event.ts_broker_ns == 900
        assert event.associated_order_id == order_id
        assert isinstance(event.fill_id, uuid.UUID)
        assert event.broker_order_id is None
        assert event.broker_fill_id is None
        assert event.symbol == "AAPL"
        assert event.side == TradeSide.BUY
        assert event.quantity_filled == 100.0
        assert event.fill_price == 150.25
        assert event.commission == 1.0
        assert event.exchange == "SIMULATED"

    def test_fields_with_broker_ids(self):
        order_id = uuid.uuid4()
        fill_id = uuid.uuid4()
        event = FillEvent(
            ts_event_ns=1000,
            ts_broker_ns=900,
            associated_order_id=order_id,
            fill_id=fill_id,
            broker_order_id="BROKER123",
            broker_fill_id="FILL456",
            symbol="AAPL",
            side=TradeSide.SELL,
            quantity_filled=50.0,
            fill_price=151.00,
            commission=0.5,
            exchange="NYSE",
        )
        assert event.fill_id == fill_id
        assert event.broker_order_id == "BROKER123"
        assert event.broker_fill_id == "FILL456"
        assert event.exchange == "NYSE"
