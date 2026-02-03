import sqlite3

from onesecondtrader import events, models
from onesecondtrader.brokers.base import BrokerBase
from onesecondtrader.datafeeds.base import DatafeedBase
from onesecondtrader.orchestrator import Orchestrator
from onesecondtrader.strategies.base import ParamSpec, StrategyBase


class MockBroker(BrokerBase):
    def connect(self) -> None:
        pass

    def _on_submit_order(self, event: events.requests.OrderSubmissionRequest) -> None:
        pass

    def _on_cancel_order(self, event: events.requests.OrderCancellationRequest) -> None:
        pass

    def _on_modify_order(self, event: events.requests.OrderModificationRequest) -> None:
        pass


class MockDatafeed(DatafeedBase):
    bars_to_publish: list[events.market.BarReceived] = []

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def subscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        pass

    def unsubscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        pass

    def wait_until_complete(self) -> None:
        for bar in self.bars_to_publish:
            self._publish(bar)
        self._event_bus.wait_until_system_idle()


class MockStrategy(StrategyBase):
    name = "Test Strategy"
    symbols = ["AAPL"]
    parameters = {"bar_period": ParamSpec(default=models.BarPeriod.MINUTE)}

    def setup(self) -> None:
        pass

    def on_bar(self, event: events.market.BarReceived) -> None:
        pass


def test_orchestrator_creates_runs_database(tmp_path):
    test_db_path = tmp_path / "runs.db"

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=MockDatafeed,
    )
    orchestrator.run()

    assert test_db_path.exists()


def test_orchestrator_registers_run_with_completed_status(tmp_path):
    test_db_path = tmp_path / "runs.db"

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=MockDatafeed,
    )
    orchestrator.run()

    conn = sqlite3.connect(str(test_db_path))
    row = conn.execute("SELECT status FROM runs").fetchone()
    conn.close()

    assert row[0] == "completed"


def test_orchestrator_records_bars_from_datafeed(tmp_path):
    import time

    test_db_path = tmp_path / "runs.db"

    class ConfiguredDatafeed(MockDatafeed):
        bars_to_publish = [
            events.market.BarReceived(
                ts_event_ns=time.time_ns(),
                symbol="AAPL",
                bar_period=models.BarPeriod.MINUTE,
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1000,
            ),
        ]

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=ConfiguredDatafeed,
    )
    orchestrator.run()

    conn = sqlite3.connect(str(test_db_path))
    row = conn.execute("SELECT symbol, open, close FROM bars").fetchone()
    conn.close()

    assert row[0] == "AAPL"
    assert row[1] == 100.0
    assert row[2] == 103.0


def test_orchestrator_generates_run_id_with_strategy_names(tmp_path):
    test_db_path = tmp_path / "runs.db"

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=MockDatafeed,
    )
    orchestrator.run()

    conn = sqlite3.connect(str(test_db_path))
    row = conn.execute("SELECT run_id FROM runs").fetchone()
    conn.close()

    assert "Test Strategy" in row[0]


def test_orchestrator_collects_symbols_from_strategies(tmp_path):
    test_db_path = tmp_path / "runs.db"

    class Strategy1(StrategyBase):
        name = "Strategy1"
        symbols = ["AAPL", "MSFT"]
        parameters = {"bar_period": ParamSpec(default=models.BarPeriod.MINUTE)}

        def setup(self) -> None:
            pass

        def on_bar(self, event: events.market.BarReceived) -> None:
            pass

    class Strategy2(StrategyBase):
        name = "Strategy2"
        symbols = ["GOOG"]
        parameters = {"bar_period": ParamSpec(default=models.BarPeriod.MINUTE)}

        def setup(self) -> None:
            pass

        def on_bar(self, event: events.market.BarReceived) -> None:
            pass

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[Strategy1, Strategy2],
        broker=MockBroker,
        datafeed=MockDatafeed,
    )

    symbols = orchestrator._collect_symbols()

    assert set(symbols) == {"AAPL", "MSFT", "GOOG"}


def test_orchestrator_stores_config_in_run(tmp_path):
    import json

    test_db_path = tmp_path / "runs.db"

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)
        mode = "backtest"

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=MockDatafeed,
    )
    orchestrator.run()

    conn = sqlite3.connect(str(test_db_path))
    row = conn.execute("SELECT config FROM runs").fetchone()
    conn.close()

    config = json.loads(row[0])
    assert config["mode"] == "backtest"
    assert "AAPL" in config["symbols"]
    assert "Test Strategy" in config["strategies"]


def test_orchestrator_marks_run_failed_on_exception(tmp_path):
    test_db_path = tmp_path / "runs.db"

    class FailingDatafeed(MockDatafeed):
        def wait_until_complete(self) -> None:
            raise RuntimeError("Datafeed error")

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[MockStrategy],
        broker=MockBroker,
        datafeed=FailingDatafeed,
    )

    try:
        orchestrator.run()
    except RuntimeError:
        pass

    conn = sqlite3.connect(str(test_db_path))
    row = conn.execute("SELECT status FROM runs").fetchone()
    conn.close()

    assert row[0] == "failed"


def test_orchestrator_shuts_down_all_components(tmp_path):
    test_db_path = tmp_path / "runs.db"
    shutdown_order = []

    class TrackingDatafeed(MockDatafeed):
        def disconnect(self) -> None:
            shutdown_order.append("datafeed")

    class TrackingBroker(MockBroker):
        def disconnect(self) -> None:
            shutdown_order.append("broker")
            super().disconnect()

    class TrackingStrategy(MockStrategy):
        def shutdown(self) -> None:
            shutdown_order.append("strategy")
            super().shutdown()

    class ConfiguredOrchestrator(Orchestrator):
        db_path = str(test_db_path)

    orchestrator = ConfiguredOrchestrator(
        strategies=[TrackingStrategy],
        broker=TrackingBroker,
        datafeed=TrackingDatafeed,
    )
    orchestrator.run()

    assert "datafeed" in shutdown_order
    assert "broker" in shutdown_order
    assert "strategy" in shutdown_order
