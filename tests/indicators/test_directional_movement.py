import math
import time

from onesecondtrader import events, models
from onesecondtrader.indicators.wilders.plus_di import PlusDI
from onesecondtrader.indicators.wilders.minus_di import MinusDI
from onesecondtrader.indicators.wilders.adx import ADX
from onesecondtrader.indicators.wilders.adx import (
    _directional_movement,
    _true_range,
)


def make_bar(
    symbol: str,
    high: float,
    low: float,
    close: float,
    open: float | None = None,
    volume: int | None = 1000,
) -> events.market.BarReceived:
    return events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        bar_period=models.BarPeriod.MINUTE,
        open=open if open is not None else close,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def is_nan(x: float) -> bool:
    return isinstance(x, float) and math.isnan(x)


# --- Helper tests ---


def test_true_range_basic() -> None:
    assert _true_range(12.0, 8.0, 10.0) == 4.0


def test_true_range_gap_up() -> None:
    # |H - prev_close| = |25 - 10| = 15 > H-L = 5
    assert _true_range(25.0, 20.0, 10.0) == 15.0


def test_true_range_gap_down() -> None:
    # |L - prev_close| = |5 - 20| = 15 > H-L = 5
    assert _true_range(10.0, 5.0, 20.0) == 15.0


def test_directional_movement_up() -> None:
    # up_move = 52-50 = 2, down_move = 48-49 = -1
    plus_dm, minus_dm = _directional_movement(52.0, 49.0, 50.0, 48.0)
    assert plus_dm == 2.0
    assert minus_dm == 0.0


def test_directional_movement_down() -> None:
    # up_move = 50-52 = -2, down_move = 49-47 = 2
    plus_dm, minus_dm = _directional_movement(50.0, 47.0, 52.0, 49.0)
    assert plus_dm == 0.0
    assert minus_dm == 2.0


def test_directional_movement_inside_bar() -> None:
    # up_move = 51-52 = -1, down_move = 49-48 = 1; both conditions fail
    plus_dm, minus_dm = _directional_movement(51.0, 49.0, 52.0, 48.0)
    assert plus_dm == 0.0
    assert minus_dm == 0.0


def test_directional_movement_equal_moves() -> None:
    # up_move = 2, down_move = 2; neither > other
    plus_dm, minus_dm = _directional_movement(52.0, 46.0, 50.0, 48.0)
    assert plus_dm == 0.0
    assert minus_dm == 0.0


# --- PlusDI tests ---


def test_plus_di_name() -> None:
    di = PlusDI(period=14)
    assert di.name == "PLUS_DI_14"


def test_plus_di_warmup() -> None:
    di = PlusDI(period=3)
    # Bar 0: init
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    assert is_nan(di.latest("AAPL"))
    # Bars 1-2: accumulating
    di.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    assert is_nan(di.latest("AAPL"))
    di.update(make_bar("AAPL", high=54.0, low=50.0, close=53.0))
    assert is_nan(di.latest("AAPL"))
    # Bar 3: count == period, first value
    di.update(make_bar("AAPL", high=56.0, low=52.0, close=55.0))
    assert not is_nan(di.latest("AAPL"))


def test_plus_di_value_range() -> None:
    di = PlusDI(period=2)
    bars = [
        (50.0, 48.0, 49.0),
        (52.0, 49.0, 51.0),
        (54.0, 50.0, 53.0),
        (56.0, 51.0, 54.0),
        (53.0, 50.0, 51.0),
    ]
    for h, lo, c in bars:
        di.update(make_bar("AAPL", high=h, low=lo, close=c))
    val = di.latest("AAPL")
    if not is_nan(val):
        assert 0.0 <= val <= 100.0


def test_plus_di_period_clamped() -> None:
    di = PlusDI(period=0)
    assert di.period == 1


def test_plus_di_positive_in_uptrend() -> None:
    """+DI should be positive in a sustained uptrend."""
    di = PlusDI(period=2)
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    di.update(make_bar("AAPL", high=53.0, low=50.0, close=52.0))
    di.update(make_bar("AAPL", high=56.0, low=52.0, close=55.0))
    val = di.latest("AAPL")
    assert not is_nan(val)
    assert val > 0.0


def test_plus_di_per_symbol_isolation() -> None:
    di = PlusDI(period=2)
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    di.update(make_bar("MSFT", high=200.0, low=195.0, close=198.0))
    di.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    di.update(make_bar("MSFT", high=205.0, low=197.0, close=202.0))
    # Both still warming up at count=1
    assert is_nan(di.latest("AAPL"))
    assert is_nan(di.latest("MSFT"))
    di.update(make_bar("AAPL", high=54.0, low=50.0, close=53.0))
    di.update(make_bar("MSFT", high=210.0, low=200.0, close=207.0))
    assert not is_nan(di.latest("AAPL"))
    assert not is_nan(di.latest("MSFT"))


# --- MinusDI tests ---


def test_minus_di_name() -> None:
    di = MinusDI(period=14)
    assert di.name == "MINUS_DI_14"


def test_minus_di_warmup() -> None:
    di = MinusDI(period=3)
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    assert is_nan(di.latest("AAPL"))
    di.update(make_bar("AAPL", high=49.0, low=46.0, close=47.0))
    assert is_nan(di.latest("AAPL"))
    di.update(make_bar("AAPL", high=48.0, low=44.0, close=45.0))
    assert is_nan(di.latest("AAPL"))
    di.update(make_bar("AAPL", high=46.0, low=42.0, close=43.0))
    assert not is_nan(di.latest("AAPL"))


def test_minus_di_period_clamped() -> None:
    di = MinusDI(period=0)
    assert di.period == 1


def test_minus_di_value_range() -> None:
    di = MinusDI(period=2)
    bars = [
        (50.0, 48.0, 49.0),
        (49.0, 46.0, 47.0),
        (48.0, 44.0, 45.0),
        (46.0, 42.0, 43.0),
        (48.0, 43.0, 47.0),
    ]
    for h, lo, c in bars:
        di.update(make_bar("AAPL", high=h, low=lo, close=c))
    val = di.latest("AAPL")
    if not is_nan(val):
        assert 0.0 <= val <= 100.0


def test_minus_di_per_symbol_isolation() -> None:
    di = MinusDI(period=2)
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    di.update(make_bar("MSFT", high=200.0, low=195.0, close=198.0))
    di.update(make_bar("AAPL", high=49.0, low=46.0, close=47.0))
    di.update(make_bar("MSFT", high=198.0, low=192.0, close=194.0))
    assert is_nan(di.latest("AAPL"))
    assert is_nan(di.latest("MSFT"))
    di.update(make_bar("AAPL", high=47.0, low=44.0, close=45.0))
    di.update(make_bar("MSFT", high=195.0, low=189.0, close=191.0))
    assert not is_nan(di.latest("AAPL"))
    assert not is_nan(di.latest("MSFT"))


def test_minus_di_positive_in_downtrend() -> None:
    """In a sustained downtrend, -DI should be positive."""
    di = MinusDI(period=2)
    di.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    di.update(make_bar("AAPL", high=49.0, low=46.0, close=47.0))
    di.update(make_bar("AAPL", high=47.0, low=44.0, close=45.0))
    val = di.latest("AAPL")
    assert not is_nan(val)
    assert val > 0.0


# --- ADX tests ---


def test_adx_name() -> None:
    adx = ADX(period=14)
    assert adx.name == "ADX_14"


def test_adx_period_clamped() -> None:
    adx = ADX(period=0)
    assert adx.period == 1


def test_adx_warmup_2x_period() -> None:
    period = 3
    adx = ADX(period=period)
    # Warmup: bar 0 = init (nan), bars 1..(period-1) accumulate DI (nan),
    # bar period = first DI/DX (dx_count=1), ... bar (2*period-1) = first ADX.
    # So 2*period bars total, first value at 0-based index 2*period - 1.
    warmup_bars = 2 * period
    bars_data = [
        (50.0, 48.0, 49.0),
        (52.0, 49.0, 51.0),
        (54.0, 50.0, 53.0),
        (56.0, 52.0, 55.0),
        (55.0, 51.0, 53.0),
        (57.0, 53.0, 56.0),
        (59.0, 55.0, 58.0),
    ]
    for i, (h, lo, c) in enumerate(bars_data):
        adx.update(make_bar("AAPL", high=h, low=lo, close=c))
        val = adx.latest("AAPL")
        if i < warmup_bars - 1:
            assert is_nan(val), f"Expected nan at bar {i}, got {val}"
        else:
            assert not is_nan(val), f"Expected value at bar {i}, got nan"


def test_adx_value_range() -> None:
    adx = ADX(period=2)
    bars = [
        (50.0, 48.0, 49.0),
        (52.0, 49.0, 51.0),
        (54.0, 50.0, 53.0),
        (56.0, 51.0, 54.0),
        (53.0, 50.0, 51.0),
        (55.0, 49.0, 53.0),
        (52.0, 48.0, 50.0),
    ]
    for h, lo, c in bars:
        adx.update(make_bar("AAPL", high=h, low=lo, close=c))
    val = adx.latest("AAPL")
    if not is_nan(val):
        assert 0.0 <= val <= 100.0


def test_adx_strong_trend() -> None:
    """ADX should be high in a strongly trending market."""
    adx = ADX(period=3)
    # Strong uptrend
    bars = [
        (50.0, 48.0, 49.0),
        (53.0, 50.0, 52.0),
        (56.0, 52.0, 55.0),
        (59.0, 55.0, 58.0),
        (62.0, 58.0, 61.0),
        (65.0, 61.0, 64.0),
        (68.0, 64.0, 67.0),
        (71.0, 67.0, 70.0),
    ]
    for h, lo, c in bars:
        adx.update(make_bar("AAPL", high=h, low=lo, close=c))
    val = adx.latest("AAPL")
    assert not is_nan(val)
    assert val > 25.0  # ADX > 25 indicates strong trend


def test_adx_per_symbol_isolation() -> None:
    adx = ADX(period=2)
    bars = [
        (50.0, 48.0, 49.0),
        (52.0, 49.0, 51.0),
        (54.0, 50.0, 53.0),
        (56.0, 51.0, 54.0),
        (53.0, 50.0, 51.0),
    ]
    for h, lo, c in bars:
        adx.update(make_bar("AAPL", high=h, low=lo, close=c))
        adx.update(make_bar("MSFT", high=h * 2, low=lo * 2, close=c * 2))
    # Both should have values by now
    assert not is_nan(adx.latest("AAPL"))
    assert not is_nan(adx.latest("MSFT"))
