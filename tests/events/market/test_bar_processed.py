from onesecondtrader.events.market import BarProcessed
from onesecondtrader.models import BarPeriod


class TestBarProcessed:
    def test_fields(self):
        event = BarProcessed(
            ts_event_ns=1000,
            symbol="AAPL",
            bar_period=BarPeriod.SECOND,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
        )
        assert event.ts_event_ns == 1000
        assert event.symbol == "AAPL"
        assert event.bar_period == BarPeriod.SECOND
        assert event.open == 100.0
        assert event.high == 101.0
        assert event.low == 99.0
        assert event.close == 100.5
        assert event.volume is None
        assert event.indicators == {}

    def test_fields_with_indicators(self):
        event = BarProcessed(
            ts_event_ns=1000,
            symbol="AAPL",
            bar_period=BarPeriod.SECOND,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            indicators={"sma_20": 99.5, "ema_10": 100.2},
        )
        assert event.indicators == {"sma_20": 99.5, "ema_10": 100.2}
