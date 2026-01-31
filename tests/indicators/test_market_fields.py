import math
import time

from onesecondtrader import events, models
from onesecondtrader.indicators.market_fields import Open, High, Low, Close, Volume


def make_bar(
    symbol: str,
    open: float = 100.0,
    high: float = 105.0,
    low: float = 95.0,
    close: float = 102.0,
    volume: int | None = 1000,
) -> events.market.BarReceived:
    return events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol=symbol,
        bar_period=models.BarPeriod.MINUTE,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def is_nan(x: float) -> bool:
    return isinstance(x, float) and math.isnan(x)


def test_open_indicator_name() -> None:
    ind = Open()
    assert ind.name == "OPEN"


def test_open_extracts_open_price() -> None:
    ind = Open()
    ind.update(make_bar(symbol="AAPL", open=100.0))
    assert ind.latest("AAPL") == 100.0
    ind.update(make_bar(symbol="AAPL", open=101.5))
    assert ind.latest("AAPL") == 101.5


def test_high_indicator_name() -> None:
    ind = High()
    assert ind.name == "HIGH"


def test_high_extracts_high_price() -> None:
    ind = High()
    ind.update(make_bar(symbol="AAPL", high=105.0))
    assert ind.latest("AAPL") == 105.0
    ind.update(make_bar(symbol="AAPL", high=106.5))
    assert ind.latest("AAPL") == 106.5


def test_low_indicator_name() -> None:
    ind = Low()
    assert ind.name == "LOW"


def test_low_extracts_low_price() -> None:
    ind = Low()
    ind.update(make_bar(symbol="AAPL", low=95.0))
    assert ind.latest("AAPL") == 95.0
    ind.update(make_bar(symbol="AAPL", low=94.5))
    assert ind.latest("AAPL") == 94.5


def test_close_indicator_name() -> None:
    ind = Close()
    assert ind.name == "CLOSE"


def test_close_extracts_close_price() -> None:
    ind = Close()
    ind.update(make_bar(symbol="AAPL", close=102.0))
    assert ind.latest("AAPL") == 102.0
    ind.update(make_bar(symbol="AAPL", close=103.5))
    assert ind.latest("AAPL") == 103.5


def test_volume_indicator_name() -> None:
    ind = Volume()
    assert ind.name == "VOLUME"


def test_volume_extracts_volume() -> None:
    ind = Volume()
    ind.update(make_bar(symbol="AAPL", volume=1000))
    assert ind.latest("AAPL") == 1000.0
    ind.update(make_bar(symbol="AAPL", volume=2500))
    assert ind.latest("AAPL") == 2500.0


def test_volume_returns_nan_when_none() -> None:
    ind = Volume()
    ind.update(make_bar(symbol="AAPL", volume=None))
    assert is_nan(ind.latest("AAPL"))


def test_per_symbol_isolation() -> None:
    open_ind = Open()
    high_ind = High()
    low_ind = Low()
    close_ind = Close()
    volume_ind = Volume()

    open_ind.update(make_bar(symbol="AAPL", open=100.0))
    open_ind.update(make_bar(symbol="MSFT", open=200.0))
    high_ind.update(make_bar(symbol="AAPL", high=105.0))
    high_ind.update(make_bar(symbol="MSFT", high=205.0))
    low_ind.update(make_bar(symbol="AAPL", low=95.0))
    low_ind.update(make_bar(symbol="MSFT", low=195.0))
    close_ind.update(make_bar(symbol="AAPL", close=102.0))
    close_ind.update(make_bar(symbol="MSFT", close=202.0))
    volume_ind.update(make_bar(symbol="AAPL", volume=1000))
    volume_ind.update(make_bar(symbol="MSFT", volume=2000))

    assert open_ind.latest("AAPL") == 100.0
    assert open_ind.latest("MSFT") == 200.0
    assert high_ind.latest("AAPL") == 105.0
    assert high_ind.latest("MSFT") == 205.0
    assert low_ind.latest("AAPL") == 95.0
    assert low_ind.latest("MSFT") == 195.0
    assert close_ind.latest("AAPL") == 102.0
    assert close_ind.latest("MSFT") == 202.0
    assert volume_ind.latest("AAPL") == 1000.0
    assert volume_ind.latest("MSFT") == 2000.0


def test_history_access() -> None:
    ind = Close()
    ind.update(make_bar(symbol="AAPL", close=100.0))
    ind.update(make_bar(symbol="AAPL", close=101.0))
    ind.update(make_bar(symbol="AAPL", close=102.0))

    assert ind["AAPL", 0] == 100.0
    assert ind["AAPL", 1] == 101.0
    assert ind["AAPL", 2] == 102.0
    assert ind["AAPL", -1] == 102.0
    assert ind["AAPL", -2] == 101.0
    assert ind["AAPL", -3] == 100.0
