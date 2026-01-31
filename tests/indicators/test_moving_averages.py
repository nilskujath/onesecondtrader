import math
import time


from onesecondtrader import events, models
from onesecondtrader.indicators.moving_averages import SimpleMovingAverage


def make_bar(
    symbol: str,
    close: float,
    open: float | None = None,
    high: float | None = None,
    low: float | None = None,
    volume: int | None = 1000,
) -> events.market.BarReceived:
    return events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        bar_period=models.BarPeriod.MINUTE,
        open=open if open is not None else close,
        high=high if high is not None else close,
        low=low if low is not None else close,
        close=close,
        volume=volume,
    )


def is_nan(x: float) -> bool:
    return isinstance(x, float) and math.isnan(x)


def test_name_includes_period_and_field() -> None:
    sma = SimpleMovingAverage(period=20, bar_field=models.BarField.CLOSE)
    assert sma.name == "SMA_20_CLOSE"
    sma_high = SimpleMovingAverage(period=50, bar_field=models.BarField.HIGH)
    assert sma_high.name == "SMA_50_HIGH"


def test_returns_nan_until_window_is_full() -> None:
    sma = SimpleMovingAverage(period=3)
    sma.update(make_bar(symbol="AAPL", close=1.0))
    assert is_nan(sma.latest("AAPL"))
    sma.update(make_bar(symbol="AAPL", close=2.0))
    assert is_nan(sma.latest("AAPL"))
    sma.update(make_bar(symbol="AAPL", close=3.0))
    assert not is_nan(sma.latest("AAPL"))


def test_computes_correct_average() -> None:
    sma = SimpleMovingAverage(period=3)
    sma.update(make_bar(symbol="AAPL", close=1.0))
    sma.update(make_bar(symbol="AAPL", close=2.0))
    sma.update(make_bar(symbol="AAPL", close=3.0))
    assert sma.latest("AAPL") == 2.0
    sma.update(make_bar(symbol="AAPL", close=4.0))
    assert sma.latest("AAPL") == 3.0
    sma.update(make_bar(symbol="AAPL", close=5.0))
    assert sma.latest("AAPL") == 4.0


def test_rolling_window_maintains_period() -> None:
    sma = SimpleMovingAverage(period=2)
    sma.update(make_bar(symbol="AAPL", close=10.0))
    sma.update(make_bar(symbol="AAPL", close=20.0))
    assert sma.latest("AAPL") == 15.0
    sma.update(make_bar(symbol="AAPL", close=30.0))
    assert sma.latest("AAPL") == 25.0
    sma.update(make_bar(symbol="AAPL", close=40.0))
    assert sma.latest("AAPL") == 35.0


def test_per_symbol_isolation() -> None:
    sma = SimpleMovingAverage(period=2)
    sma.update(make_bar(symbol="AAPL", close=10.0))
    sma.update(make_bar(symbol="AAPL", close=20.0))
    sma.update(make_bar(symbol="MSFT", close=100.0))
    sma.update(make_bar(symbol="MSFT", close=200.0))
    assert sma.latest("AAPL") == 15.0
    assert sma.latest("MSFT") == 150.0


def test_bar_field_open() -> None:
    sma = SimpleMovingAverage(period=2, bar_field=models.BarField.OPEN)
    sma.update(make_bar(symbol="AAPL", open=10.0, close=15.0))
    sma.update(make_bar(symbol="AAPL", open=20.0, close=25.0))
    assert sma.latest("AAPL") == 15.0


def test_bar_field_high() -> None:
    sma = SimpleMovingAverage(period=2, bar_field=models.BarField.HIGH)
    sma.update(make_bar(symbol="AAPL", high=12.0, close=10.0))
    sma.update(make_bar(symbol="AAPL", high=22.0, close=20.0))
    assert sma.latest("AAPL") == 17.0


def test_bar_field_low() -> None:
    sma = SimpleMovingAverage(period=2, bar_field=models.BarField.LOW)
    sma.update(make_bar(symbol="AAPL", low=8.0, close=10.0))
    sma.update(make_bar(symbol="AAPL", low=18.0, close=20.0))
    assert sma.latest("AAPL") == 13.0


def test_bar_field_volume() -> None:
    sma = SimpleMovingAverage(period=2, bar_field=models.BarField.VOLUME)
    sma.update(make_bar(symbol="AAPL", close=10.0, volume=1000))
    sma.update(make_bar(symbol="AAPL", close=20.0, volume=2000))
    assert sma.latest("AAPL") == 1500.0


def test_bar_field_volume_with_none() -> None:
    sma = SimpleMovingAverage(period=2, bar_field=models.BarField.VOLUME)
    sma.update(make_bar(symbol="AAPL", close=10.0, volume=None))
    sma.update(make_bar(symbol="AAPL", close=20.0, volume=1000))
    assert is_nan(sma.latest("AAPL"))


def test_period_clamped_to_at_least_one() -> None:
    sma = SimpleMovingAverage(period=0)
    assert sma.period == 1
    sma.update(make_bar(symbol="AAPL", close=10.0))
    assert sma.latest("AAPL") == 10.0


def test_history_access() -> None:
    sma = SimpleMovingAverage(period=2, max_history=10)
    sma.update(make_bar(symbol="AAPL", close=10.0))
    sma.update(make_bar(symbol="AAPL", close=20.0))
    sma.update(make_bar(symbol="AAPL", close=30.0))
    assert is_nan(sma["AAPL", 0])
    assert sma["AAPL", 1] == 15.0
    assert sma["AAPL", 2] == 25.0
    assert sma["AAPL", -1] == 25.0
    assert sma["AAPL", -2] == 15.0
