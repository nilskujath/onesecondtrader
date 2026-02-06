import math
import time

from onesecondtrader import events, models
from onesecondtrader.indicators.wilders.atr import ATR


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


def test_name() -> None:
    atr = ATR(period=14)
    assert atr.name == "ATR_14"
    atr5 = ATR(period=5)
    assert atr5.name == "ATR_5"


def test_period_clamped() -> None:
    atr = ATR(period=0)
    assert atr.period == 1


def test_returns_nan_during_warmup() -> None:
    atr = ATR(period=3)
    # Bar 0: first bar, no prev_close -> nan
    atr.update(make_bar("AAPL", close=10.0, high=11.0, low=9.0))
    assert is_nan(atr.latest("AAPL"))
    # Bar 1: count=1, period=3, still warming up
    atr.update(make_bar("AAPL", close=12.0, high=13.0, low=11.0))
    assert is_nan(atr.latest("AAPL"))
    # Bar 2: count=2, period=3, still warming up
    atr.update(make_bar("AAPL", close=11.0, high=12.0, low=10.0))
    assert is_nan(atr.latest("AAPL"))
    # Bar 3: count=3, period=3, first ATR computed
    atr.update(make_bar("AAPL", close=13.0, high=14.0, low=12.0))
    assert not is_nan(atr.latest("AAPL"))


def test_first_atr_is_simple_average_of_trs() -> None:
    atr = ATR(period=3)
    # Bar 0: initialize prev_close=10
    atr.update(make_bar("AAPL", close=10.0, high=10.0, low=10.0))
    # Bar 1: TR = max(12-8, |12-10|, |8-10|) = max(4, 2, 2) = 4
    atr.update(make_bar("AAPL", close=11.0, high=12.0, low=8.0))
    # Bar 2: TR = max(13-9, |13-11|, |9-11|) = max(4, 2, 2) = 4
    atr.update(make_bar("AAPL", close=12.0, high=13.0, low=9.0))
    # Bar 3: TR = max(14-10, |14-12|, |10-12|) = max(4, 2, 2) = 4
    atr.update(make_bar("AAPL", close=13.0, high=14.0, low=10.0))
    # First ATR = (4 + 4 + 4) / 3 = 4.0
    assert atr.latest("AAPL") == 4.0


def test_wilder_smoothing_after_initial() -> None:
    atr = ATR(period=2)
    # Bar 0: init prev_close=10
    atr.update(make_bar("AAPL", close=10.0, high=10.0, low=10.0))
    # Bar 1: TR = max(12-8, |12-10|, |8-10|) = 4
    atr.update(make_bar("AAPL", close=11.0, high=12.0, low=8.0))
    # Bar 2: TR = max(14-10, |14-11|, |10-11|) = 4
    atr.update(make_bar("AAPL", close=13.0, high=14.0, low=10.0))
    # First ATR = (4 + 4) / 2 = 4.0
    assert atr.latest("AAPL") == 4.0
    # Bar 3: TR = max(15-12, |15-13|, |12-13|) = 3
    atr.update(make_bar("AAPL", close=14.0, high=15.0, low=12.0))
    # ATR = (4.0 * 1 + 3) / 2 = 3.5
    assert atr.latest("AAPL") == 3.5


def test_per_symbol_isolation() -> None:
    atr = ATR(period=2)
    atr.update(make_bar("AAPL", close=10.0, high=10.0, low=10.0))
    atr.update(make_bar("MSFT", close=100.0, high=100.0, low=100.0))
    atr.update(make_bar("AAPL", close=12.0, high=14.0, low=8.0))
    atr.update(make_bar("MSFT", close=110.0, high=120.0, low=90.0))
    # AAPL count=1 -> nan, MSFT count=1 -> nan
    assert is_nan(atr.latest("AAPL"))
    assert is_nan(atr.latest("MSFT"))
    atr.update(make_bar("AAPL", close=11.0, high=13.0, low=9.0))
    atr.update(make_bar("MSFT", close=105.0, high=115.0, low=95.0))
    # AAPL first ATR computed, MSFT first ATR computed
    assert not is_nan(atr.latest("AAPL"))
    assert not is_nan(atr.latest("MSFT"))


def test_true_range_uses_prev_close() -> None:
    """TR should use |high - prev_close| when gap up."""
    atr = ATR(period=1)
    # Bar 0: init prev_close=10
    atr.update(make_bar("AAPL", close=10.0, high=10.0, low=10.0))
    # Bar 1: gap up, H=25, L=20, C=22, prev_close=10
    # TR = max(25-20, |25-10|, |20-10|) = max(5, 15, 10) = 15
    atr.update(make_bar("AAPL", close=22.0, high=25.0, low=20.0))
    assert atr.latest("AAPL") == 15.0


def test_history_access() -> None:
    atr = ATR(period=2, max_history=10)
    atr.update(make_bar("AAPL", close=10.0, high=10.0, low=10.0))
    atr.update(make_bar("AAPL", close=12.0, high=14.0, low=8.0))
    atr.update(make_bar("AAPL", close=11.0, high=13.0, low=9.0))
    # Index 0: nan (init bar), Index 1: nan (warmup), Index 2: first ATR
    assert is_nan(atr["AAPL", 0])
    assert is_nan(atr["AAPL", 1])
    assert not is_nan(atr["AAPL", 2])
    assert atr["AAPL", -1] == atr.latest("AAPL")


def test_missing_symbol_returns_nan() -> None:
    atr = ATR()
    assert is_nan(atr.latest("UNKNOWN"))


def test_plot_defaults() -> None:
    atr = ATR()
    assert atr.plot_at == 1
    assert atr.plot_as == models.PlotStyle.LINE
    assert atr.plot_color == models.PlotColor.BLACK
