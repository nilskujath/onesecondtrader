import json
import sqlite3
import time

from onesecondtrader import events, messaging, models
from onesecondtrader.orchestrator import RunRecorder


def test_run_recorder_creates_database(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    assert db_path.exists()
    recorder.shutdown()


def test_run_recorder_registers_run_on_init(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
        config={"mode": "backtest"},
        metadata={"version": "1.0"},
    )
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT * FROM runs WHERE run_id = ?", ("test-run-1",)
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[1] == "Test Run"
    assert row[4] == "running"
    assert json.loads(row[5]) == {"mode": "backtest"}
    assert json.loads(row[6]) == {"version": "1.0"}


def test_run_recorder_update_run_status(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    ts_end = time.time_ns()
    recorder.update_run_status("completed", ts_end)
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT status, ts_end FROM runs WHERE run_id = ?", ("test-run-1",)
    ).fetchone()
    conn.close()

    assert row[0] == "completed"
    assert row[1] == ts_end


def test_run_recorder_records_bar_received(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    bar = events.market.BarReceived(
        ts_event_ns=time.time_ns(),
        symbol="AAPL",
        bar_period=models.BarPeriod.MINUTE,
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1000,
    )
    bus.publish(bar)
    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT symbol, open, high, low, close, volume FROM bars WHERE run_id = ?",
        ("test-run-1",),
    ).fetchone()
    conn.close()

    assert row[0] == "AAPL"
    assert row[1] == 100.0
    assert row[2] == 105.0
    assert row[3] == 99.0
    assert row[4] == 103.0
    assert row[5] == 1000


def test_run_recorder_records_order_submission(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    order = events.requests.OrderSubmissionRequest(
        ts_event_ns=time.time_ns(),
        symbol="AAPL",
        order_type=models.OrderType.MARKET,
        side=models.TradeSide.BUY,
        quantity=100.0,
    )
    bus.publish(order)
    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT symbol, order_type, side, quantity FROM order_submissions WHERE run_id = ?",
        ("test-run-1",),
    ).fetchone()
    conn.close()

    assert row[0] == "AAPL"
    assert row[1] == "MARKET"
    assert row[2] == "BUY"
    assert row[3] == 100.0


def test_run_recorder_records_fill_event(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    fill = events.orders.FillEvent(
        ts_event_ns=time.time_ns(),
        ts_broker_ns=time.time_ns(),
        associated_order_id="order-123",
        symbol="AAPL",
        side=models.TradeSide.BUY,
        quantity_filled=50.0,
        fill_price=101.5,
        commission=1.0,
        exchange="NASDAQ",
    )
    bus.publish(fill)
    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT symbol, side, quantity_filled, fill_price, commission, exchange FROM fills WHERE run_id = ?",
        ("test-run-1",),
    ).fetchone()
    conn.close()

    assert row[0] == "AAPL"
    assert row[1] == "BUY"
    assert row[2] == 50.0
    assert row[3] == 101.5
    assert row[4] == 1.0
    assert row[5] == "NASDAQ"


def test_run_recorder_batches_inserts(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    for i in range(50):
        bar = events.market.BarReceived(
            ts_event_ns=time.time_ns(),
            symbol=f"SYM{i}",
            bar_period=models.BarPeriod.MINUTE,
            open=100.0 + i,
            high=105.0 + i,
            low=99.0 + i,
            close=103.0 + i,
            volume=1000 + i,
        )
        bus.publish(bar)

    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    count = conn.execute(
        "SELECT COUNT(*) FROM bars WHERE run_id = ?", ("test-run-1",)
    ).fetchone()[0]
    conn.close()

    assert count == 50


def test_run_recorder_records_order_accepted(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    accepted = events.responses.OrderAccepted(
        ts_event_ns=time.time_ns(),
        ts_broker_ns=time.time_ns(),
        associated_order_id="order-123",
        broker_order_id="broker-456",
    )
    bus.publish(accepted)
    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT associated_order_id, broker_order_id FROM orders_accepted WHERE run_id = ?",
        ("test-run-1",),
    ).fetchone()
    conn.close()

    assert row[0] == "order-123"
    assert row[1] == "broker-456"


def test_run_recorder_records_order_rejected(tmp_path):
    db_path = tmp_path / "runs.db"
    bus = messaging.EventBus()

    recorder = RunRecorder(
        event_bus=bus,
        db_path=db_path,
        run_id="test-run-1",
        name="Test Run",
    )

    rejected = events.responses.OrderRejected(
        ts_event_ns=time.time_ns(),
        ts_broker_ns=time.time_ns(),
        associated_order_id="order-123",
        rejection_reason=models.OrderRejectionReason.UNKNOWN,
        rejection_message="Not enough funds",
    )
    bus.publish(rejected)
    bus.wait_until_system_idle()
    recorder.shutdown()

    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT associated_order_id, rejection_reason, rejection_message FROM orders_rejected WHERE run_id = ?",
        ("test-run-1",),
    ).fetchone()
    conn.close()

    assert row[0] == "order-123"
    assert row[1] == "UNKNOWN"
    assert row[2] == "Not enough funds"
