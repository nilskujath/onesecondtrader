import sqlite3

from onesecondtrader import events, messaging, models
from onesecondtrader.datafeeds.simulated import SimulatedDatafeed
from onesecondtrader.secmaster.utils import create_secmaster_db


def _make_db(tmp_path):
    db_path = tmp_path / "secmaster.db"
    create_secmaster_db(db_path)
    return db_path


def _make_publisher(con, name="databento", dataset="X.TEST"):
    cur = con.cursor()
    cur.execute(
        "INSERT INTO publishers (name, dataset, venue) VALUES (?, ?, ?)",
        (name, dataset, "X"),
    )
    return int(cur.lastrowid)


def _make_instrument(con, publisher_id, source_id):
    con.execute(
        "INSERT INTO instruments (publisher_ref, source_instrument_id) VALUES (?, ?)",
        (publisher_id, source_id),
    )
    return con.execute("SELECT last_insert_rowid()").fetchone()[0]


def _make_symbology(con, publisher_id, symbol, source_id, start, end):
    con.execute(
        "INSERT INTO symbology "
        "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (publisher_id, symbol, "raw_symbol", source_id, start, end),
    )


def _make_ohlcv(con, instrument_id, rtype, ts_event, o, h, lo, c, v):
    con.execute(
        "INSERT INTO ohlcv "
        "(instrument_id, rtype, ts_event, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (instrument_id, rtype, ts_event, o, h, lo, c, v),
    )


def test_simulated_datafeed_requires_publisher_name():
    event_bus = messaging.EventBus()

    class BadFeed(SimulatedDatafeed):
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    try:
        BadFeed(event_bus)
    except ValueError as e:
        assert "publisher_name" in str(e)
    else:
        raise AssertionError("Expected ValueError")


def test_simulated_datafeed_requires_dataset():
    event_bus = messaging.EventBus()

    class BadFeed(SimulatedDatafeed):
        publisher_name: str = "databento"
        symbol_type: str = "raw_symbol"

    try:
        BadFeed(event_bus)
    except ValueError as e:
        assert "dataset" in str(e)
    else:
        raise AssertionError("Expected ValueError")


def test_simulated_datafeed_requires_symbol_type():
    event_bus = messaging.EventBus()

    class BadFeed(SimulatedDatafeed):
        publisher_name: str = "databento"
        dataset: str = "X.TEST"

    try:
        BadFeed(event_bus)
    except ValueError as e:
        assert "symbol_type" in str(e)
    else:
        raise AssertionError("Expected ValueError")


def test_simulated_datafeed_connect_resolves_publisher(tmp_path):
    db_path = _make_db(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    _make_publisher(con)
    con.commit()
    con.close()

    class Feed(SimulatedDatafeed):
        publisher_name: str = "databento"
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    Feed.db_path = str(db_path)

    event_bus = messaging.EventBus()
    feed = Feed(event_bus)
    feed.connect()

    assert feed._publisher_id is not None
    feed.disconnect()


def test_simulated_datafeed_connect_raises_for_missing_publisher(tmp_path):
    db_path = _make_db(tmp_path)

    class Feed(SimulatedDatafeed):
        publisher_name: str = "nonexistent"
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    Feed.db_path = str(db_path)

    event_bus = messaging.EventBus()
    feed = Feed(event_bus)

    try:
        feed.connect()
    except ValueError as e:
        assert "not found" in str(e)
    else:
        raise AssertionError("Expected ValueError")


def test_simulated_datafeed_streams_bars(tmp_path):
    db_path = _make_db(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)
    instrument_id = _make_instrument(con, publisher_id, 100)
    _make_symbology(con, publisher_id, "AAPL", 100, "2020-01-01", "2020-12-31")

    ts1 = 1577836800_000_000_000
    ts2 = 1577836860_000_000_000
    _make_ohlcv(
        con,
        instrument_id,
        33,
        ts1,
        100_000_000_000,
        101_000_000_000,
        99_000_000_000,
        100_500_000_000,
        1000,
    )
    _make_ohlcv(
        con,
        instrument_id,
        33,
        ts2,
        100_500_000_000,
        102_000_000_000,
        100_000_000_000,
        101_000_000_000,
        2000,
    )
    con.commit()
    con.close()

    class Feed(SimulatedDatafeed):
        publisher_name: str = "databento"
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    Feed.db_path = str(db_path)

    received_bars: list[events.market.BarReceived] = []
    event_bus = messaging.EventBus()

    class Collector(messaging.Subscriber):
        def _on_event(self, event: events.EventBase) -> None:
            if isinstance(event, events.market.BarReceived):
                received_bars.append(event)

    collector = Collector(event_bus)
    event_bus.subscribe(collector, events.market.BarReceived)

    feed = Feed(event_bus)
    feed.connect()
    feed.subscribe(["AAPL"], models.BarPeriod.MINUTE)
    feed.wait_until_complete()
    feed.disconnect()
    collector.wait_until_idle()
    collector.shutdown()

    assert len(received_bars) == 2
    assert received_bars[0].symbol == "AAPL"
    assert received_bars[0].ts_event_ns == ts1
    assert received_bars[1].ts_event_ns == ts2


def test_simulated_datafeed_filters_by_subscription(tmp_path):
    db_path = _make_db(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)

    inst_aapl = _make_instrument(con, publisher_id, 100)
    inst_msft = _make_instrument(con, publisher_id, 101)
    _make_symbology(con, publisher_id, "AAPL", 100, "2020-01-01", "2020-12-31")
    _make_symbology(con, publisher_id, "MSFT", 101, "2020-01-01", "2020-12-31")

    ts1 = 1577836800_000_000_000
    _make_ohlcv(
        con,
        inst_aapl,
        33,
        ts1,
        100_000_000_000,
        101_000_000_000,
        99_000_000_000,
        100_500_000_000,
        1000,
    )
    _make_ohlcv(
        con,
        inst_msft,
        33,
        ts1,
        200_000_000_000,
        201_000_000_000,
        199_000_000_000,
        200_500_000_000,
        2000,
    )
    con.commit()
    con.close()

    class Feed(SimulatedDatafeed):
        publisher_name: str = "databento"
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    Feed.db_path = str(db_path)

    received_bars: list[events.market.BarReceived] = []
    event_bus = messaging.EventBus()

    class Collector(messaging.Subscriber):
        def _on_event(self, event: events.EventBase) -> None:
            if isinstance(event, events.market.BarReceived):
                received_bars.append(event)

    collector = Collector(event_bus)
    event_bus.subscribe(collector, events.market.BarReceived)

    feed = Feed(event_bus)
    feed.connect()
    feed.subscribe(["AAPL"], models.BarPeriod.MINUTE)
    feed.wait_until_complete()
    feed.disconnect()
    collector.wait_until_idle()
    collector.shutdown()

    assert len(received_bars) == 1
    assert received_bars[0].symbol == "AAPL"


def test_simulated_datafeed_respects_time_range(tmp_path):
    db_path = _make_db(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = ON;")
    publisher_id = _make_publisher(con)
    instrument_id = _make_instrument(con, publisher_id, 100)
    _make_symbology(con, publisher_id, "AAPL", 100, "2020-01-01", "2020-12-31")

    ts1 = 1577836800_000_000_000
    ts2 = 1577836860_000_000_000
    ts3 = 1577836920_000_000_000
    _make_ohlcv(
        con,
        instrument_id,
        33,
        ts1,
        100_000_000_000,
        101_000_000_000,
        99_000_000_000,
        100_500_000_000,
        1000,
    )
    _make_ohlcv(
        con,
        instrument_id,
        33,
        ts2,
        100_500_000_000,
        102_000_000_000,
        100_000_000_000,
        101_000_000_000,
        2000,
    )
    _make_ohlcv(
        con,
        instrument_id,
        33,
        ts3,
        101_000_000_000,
        103_000_000_000,
        100_500_000_000,
        102_000_000_000,
        3000,
    )
    con.commit()
    con.close()

    class Feed(SimulatedDatafeed):
        publisher_name: str = "databento"
        dataset: str = "X.TEST"
        symbol_type: str = "raw_symbol"

    Feed.db_path = str(db_path)
    Feed.start_ts = ts2
    Feed.end_ts = ts2

    received_bars: list[events.market.BarReceived] = []
    event_bus = messaging.EventBus()

    class Collector(messaging.Subscriber):
        def _on_event(self, event: events.EventBase) -> None:
            if isinstance(event, events.market.BarReceived):
                received_bars.append(event)

    collector = Collector(event_bus)
    event_bus.subscribe(collector, events.market.BarReceived)

    feed = Feed(event_bus)
    feed.connect()
    feed.subscribe(["AAPL"], models.BarPeriod.MINUTE)
    feed.wait_until_complete()
    feed.disconnect()
    collector.wait_until_idle()
    collector.shutdown()

    assert len(received_bars) == 1
    assert received_bars[0].ts_event_ns == ts2
