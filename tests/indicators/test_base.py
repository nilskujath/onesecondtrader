import math
import threading
import time

import numpy as np

from onesecondtrader.events.market import BarReceived
from onesecondtrader.indicators.base import IndicatorBase
from onesecondtrader.models import BarPeriod, PlotColor


class CloseIndicator(IndicatorBase):
    @property
    def name(self) -> str:
        return "close"

    def _compute_indicator(self, incoming_bar: BarReceived) -> float:
        return float(incoming_bar.close)


def make_bar(symbol: str, close: float) -> BarReceived:
    return BarReceived(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        bar_period=BarPeriod.MINUTE,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


def is_nan(x: float) -> bool:
    return isinstance(x, float) and math.isnan(x)


def test_name_is_stable_string() -> None:
    ind = CloseIndicator()
    assert isinstance(ind.name, str)
    assert ind.name == "close"


def test_plot_at_is_exposed() -> None:
    ind = CloseIndicator(plot_at=123)
    assert ind.plot_at == 123


def test_plot_color_defaults_to_black() -> None:
    ind = CloseIndicator()
    assert ind.plot_color == PlotColor.BLACK


def test_plot_color_exposes_user_supplied_value() -> None:
    ind = CloseIndicator(plot_color=PlotColor.RED)
    assert ind.plot_color == PlotColor.RED


def test_missing_symbol_returns_nan() -> None:
    ind = CloseIndicator()
    assert is_nan(ind.latest("AAPL"))
    assert is_nan(ind["AAPL", -1])
    assert is_nan(ind["AAPL", 0])


def test_out_of_bounds_returns_nan() -> None:
    ind = CloseIndicator()
    ind.update(make_bar(symbol="AAPL", close=100.0))
    assert is_nan(ind["AAPL", 1])
    assert is_nan(ind["AAPL", -2])


def test_latest_matches_getitem_negative_one() -> None:
    ind = CloseIndicator()
    ind.update(make_bar(symbol="AAPL", close=100.0))
    ind.update(make_bar(symbol="AAPL", close=101.5))
    assert ind.latest("AAPL") == ind["AAPL", -1]
    assert ind["AAPL", -1] == 101.5


def test_per_symbol_isolation() -> None:
    ind = CloseIndicator()
    ind.update(make_bar(symbol="AAPL", close=100.0))
    ind.update(make_bar(symbol="MSFT", close=200.0))
    ind.update(make_bar(symbol="AAPL", close=101.0))
    assert ind["AAPL", -1] == 101.0
    assert ind["MSFT", -1] == 200.0


def test_max_history_bounds_buffer() -> None:
    ind = CloseIndicator(max_history=3)
    ind.update(make_bar(symbol="AAPL", close=1.0))
    ind.update(make_bar(symbol="AAPL", close=2.0))
    ind.update(make_bar(symbol="AAPL", close=3.0))
    ind.update(make_bar(symbol="AAPL", close=4.0))
    assert ind["AAPL", 0] == 2.0
    assert ind["AAPL", 1] == 3.0
    assert ind["AAPL", 2] == 4.0
    assert is_nan(ind["AAPL", 3])


def test_max_history_is_clamped_to_at_least_one() -> None:
    ind = CloseIndicator(max_history=0)
    ind.update(make_bar(symbol="AAPL", close=1.0))
    ind.update(make_bar(symbol="AAPL", close=2.0))
    assert ind["AAPL", -1] == 2.0
    assert ind["AAPL", 0] == 2.0
    assert is_nan(ind["AAPL", -2])


def test_thread_safety_under_concurrent_updates() -> None:
    ind = CloseIndicator(max_history=50)

    def worker(symbol: str, start: float) -> None:
        for i in range(500):
            ind.update(make_bar(symbol=symbol, close=start + i))

    t1 = threading.Thread(target=worker, args=("AAPL", 0.0))
    t2 = threading.Thread(target=worker, args=("MSFT", 10_000.0))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    aapl_latest = ind.latest("AAPL")
    msft_latest = ind.latest("MSFT")

    assert not np.isnan(aapl_latest)
    assert not np.isnan(msft_latest)

    assert ind["AAPL", -50] <= aapl_latest
    assert ind["MSFT", -50] <= msft_latest

    assert is_nan(ind["AAPL", -51])
    assert is_nan(ind["MSFT", -51])
