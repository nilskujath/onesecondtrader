import math
import time

from onesecondtrader import events, models
from onesecondtrader.indicators.wilders.parabolic_sar import ParabolicSAR


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


def test_name() -> None:
    sar = ParabolicSAR()
    assert sar.name == "PSAR_0.02_0.02_0.2"


def test_first_bar_is_nan() -> None:
    sar = ParabolicSAR()
    sar.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    assert is_nan(sar.latest("AAPL"))


def test_second_bar_produces_value() -> None:
    sar = ParabolicSAR()
    sar.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    assert not is_nan(sar.latest("AAPL"))


def test_uptrend_initial_sar_is_prev_low() -> None:
    sar = ParabolicSAR()
    sar.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    # Uptrend detected (high >= prev_high), SAR = prev_low = 48.0
    assert sar.latest("AAPL") == 48.0


def test_downtrend_initial_sar_is_prev_high() -> None:
    sar = ParabolicSAR()
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    sar.update(make_bar("AAPL", high=50.0, low=47.0, close=48.0))
    # Downtrend detected (high < prev_high), SAR = prev_high = 52.0
    assert sar.latest("AAPL") == 52.0


def test_sar_advances_in_uptrend() -> None:
    sar = ParabolicSAR(af_start=0.02, af_step=0.02, af_max=0.20)
    # Bar 0: low=49
    sar.update(make_bar("AAPL", high=50.0, low=49.0, close=49.5))
    # Bar 1: uptrend, SAR=49.0, EP=52.0, AF=0.02
    sar.update(make_bar("AAPL", high=52.0, low=50.0, close=51.0))
    assert sar.latest("AAPL") == 49.0
    # Bar 2: SAR_raw = 49.0 + 0.02 * (52.0 - 49.0) = 49.06
    # Clamp: min(low_buf) = min(49.0, 50.0) = 49.0 -> clamped to 49.0
    # But low=51 > 49.0 -> no reversal; high=54 > EP=52 -> EP=54, AF=0.04
    sar.update(make_bar("AAPL", high=54.0, low=51.0, close=53.0))
    assert sar.latest("AAPL") == 49.0
    # Bar 3: SAR_raw = 49.0 + 0.04 * (54.0 - 49.0) = 49.2
    # Clamp: min(low_buf) = min(50.0, 51.0) = 50.0 -> 49.2 ok (49.2 < 50.0)
    # high=56 > EP=54 -> EP=56, AF=0.06
    sar.update(make_bar("AAPL", high=56.0, low=52.0, close=55.0))
    assert abs(sar.latest("AAPL") - 49.2) < 1e-10


def test_reversal_from_long_to_short() -> None:
    sar = ParabolicSAR(af_start=0.02, af_step=0.02, af_max=0.20)
    # Bar 0
    sar.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    # Bar 1: uptrend, SAR=48.0, EP=52.0
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    # Bar 2: SAR = 48.0 + 0.02*(52-48) = 48.08, low=40 < 48.08 -> reversal
    # SAR becomes EP=52.0 (previous extreme)
    sar.update(make_bar("AAPL", high=49.0, low=40.0, close=41.0))
    assert sar.latest("AAPL") == 52.0


def test_reversal_from_short_to_long() -> None:
    sar = ParabolicSAR(af_start=0.02, af_step=0.02, af_max=0.20)
    # Bar 0
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    # Bar 1: downtrend, SAR=52.0, EP=47.0
    sar.update(make_bar("AAPL", high=50.0, low=47.0, close=48.0))
    assert sar.latest("AAPL") == 52.0
    # Bar 2: SAR = 52.0 + 0.02*(47-52) = 51.9, high=55 > 51.9 -> reversal
    # SAR becomes EP=47.0 (previous extreme)
    sar.update(make_bar("AAPL", high=55.0, low=48.0, close=54.0))
    assert sar.latest("AAPL") == 47.0


def test_af_clamped_at_max() -> None:
    sar = ParabolicSAR(af_start=0.10, af_step=0.10, af_max=0.20)
    # Bar 0
    sar.update(make_bar("AAPL", high=50.0, low=49.0, close=49.5))
    # Bar 1: uptrend, AF=0.10
    sar.update(make_bar("AAPL", high=52.0, low=50.0, close=51.0))
    # Bar 2: new EP -> AF=0.20 (capped at max)
    sar.update(make_bar("AAPL", high=54.0, low=51.0, close=53.0))
    # Bar 3: new EP -> AF should still be 0.20 (can't exceed max)
    sar.update(make_bar("AAPL", high=56.0, low=52.0, close=55.0))
    # Bar 4: new EP -> AF stays 0.20
    sar.update(make_bar("AAPL", high=58.0, low=54.0, close=57.0))
    # Verify SAR is advancing correctly with AF=0.20
    # If AF exceeded 0.20, SAR would advance too fast
    val = sar.latest("AAPL")
    assert not is_nan(val)
    assert val < 54.0  # SAR should still be below recent lows


def test_per_symbol_isolation() -> None:
    sar = ParabolicSAR()
    sar.update(make_bar("AAPL", high=50.0, low=48.0, close=49.0))
    sar.update(make_bar("MSFT", high=200.0, low=195.0, close=198.0))
    sar.update(make_bar("AAPL", high=52.0, low=49.0, close=51.0))
    sar.update(make_bar("MSFT", high=205.0, low=198.0, close=203.0))
    # Both in uptrend
    assert sar.latest("AAPL") == 48.0
    assert sar.latest("MSFT") == 195.0


def test_plot_defaults() -> None:
    sar = ParabolicSAR()
    assert sar.plot_at == 0
    assert sar.plot_as == models.PlotStyle.DOTS
    assert sar.plot_color == models.PlotColor.BLACK
