from __future__ import annotations

import pathlib

import dotenv
import pandas as pd

from onesecondtrader import messaging, models
from onesecondtrader.brokers.base import BrokerBase
from onesecondtrader.datafeeds.base import DatafeedBase
from onesecondtrader.strategies.base import StrategyBase
from .run_recorder import RunRecorder


class Orchestrator:
    """
    Orchestrates the execution of a trading run.

    The orchestrator instantiates strategies, broker, datafeed, and recorder components,
    connects them via an event bus, and coordinates the run lifecycle from start to shutdown.
    """

    db_path: str = "runs.db"
    mode: str = "backtest"
    start_date: str | None = None
    end_date: str | None = None

    def __init__(
        self,
        strategies: list[type[StrategyBase]],
        broker: type[BrokerBase],
        datafeed: type[DatafeedBase],
    ) -> None:
        """
        Initialize the orchestrator with component classes.

        Parameters:
            strategies:
                List of strategy classes to instantiate for the run.
            broker:
                Broker class to instantiate for order execution.
            datafeed:
                Datafeed class to instantiate for market data delivery.
        """
        dotenv.load_dotenv()
        self._strategy_classes = strategies
        self._broker_class = broker
        self._datafeed_class = datafeed
        self._event_bus: messaging.EventBus | None = None
        self._strategies: list[StrategyBase] = []
        self._broker: BrokerBase | None = None
        self._datafeed: DatafeedBase | None = None
        self._recorder: RunRecorder | None = None

    @property
    def progress(self) -> float:
        datafeed = self._datafeed
        if datafeed is None:
            return 0.0
        return datafeed.progress

    def run(self) -> None:
        """
        Execute the trading run.

        Creates all components, connects them, subscribes to symbols, waits for
        the datafeed to complete, and then shuts down all components.
        """
        self.run_id = self._generate_run_id()

        self._event_bus = messaging.EventBus()

        self._recorder = self._create_recorder(self.run_id)
        self._broker = self._broker_class(self._event_bus)
        self._strategies = [s(self._event_bus) for s in self._strategy_classes]
        self._datafeed = self._datafeed_class(self._event_bus)

        try:
            self._broker.connect()
            self._datafeed.connect()
            self._subscribe_symbols()
            self._datafeed.wait_until_complete()
            self._event_bus.wait_until_system_idle()
            self._recorder.update_run_status(
                "completed", pd.Timestamp.now(tz="UTC").value
            )
        except Exception:
            if self._recorder:
                self._recorder.update_run_status(
                    "failed", pd.Timestamp.now(tz="UTC").value
                )
            raise
        finally:
            self._shutdown()

    def _generate_run_id(self) -> str:
        """
        Generate a unique run identifier.

        Returns:
            A string combining the current UTC timestamp and strategy names.
        """
        timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d_%H-%M-%S")
        strategy_names = "_".join(s.name for s in self._strategy_classes)
        return f"{timestamp}_{strategy_names}"

    def _collect_symbols(self) -> list[str]:
        """
        Collect all unique symbols from the strategy classes.

        Returns:
            A deduplicated list of symbols from all strategies.
        """
        symbols = []
        for strategy_class in self._strategy_classes:
            symbols.extend(strategy_class.symbols)
        return list(set(symbols))

    def _create_recorder(self, run_id: str) -> RunRecorder:
        """
        Create and return a RunRecorder instance for this run.

        Parameters:
            run_id:
                Unique identifier for this run.

        Returns:
            A configured RunRecorder instance.
        """
        assert self._event_bus is not None
        config = {
            "mode": self.mode,
            "symbols": self._collect_symbols(),
            "strategies": [s.name for s in self._strategy_classes],
            "start_date": self.start_date,
            "end_date": self.end_date,
        }
        return RunRecorder(
            event_bus=self._event_bus,
            db_path=pathlib.Path(self.db_path),
            run_id=run_id,
            name="_".join(s.name for s in self._strategy_classes),
            config=config,
        )

    def _subscribe_symbols(self) -> None:
        """
        Subscribe the datafeed to symbols for each strategy's bar period.
        """
        assert self._datafeed is not None
        subscriptions: dict[models.BarPeriod, list[str]] = {}
        for strategy_class in self._strategy_classes:
            bar_period_value = strategy_class.parameters["bar_period"].default
            assert isinstance(bar_period_value, models.BarPeriod)
            if bar_period_value not in subscriptions:
                subscriptions[bar_period_value] = []
            subscriptions[bar_period_value].extend(strategy_class.symbols)
        for bar_period, symbols in subscriptions.items():
            self._datafeed.subscribe(list(set(symbols)), bar_period)

    def _shutdown(self) -> None:
        """
        Shut down all components in the correct order.
        """
        if self._datafeed:
            self._datafeed.disconnect()
        if self._broker:
            self._broker.disconnect()
        for strategy in self._strategies:
            strategy.shutdown()
        if self._recorder:
            self._recorder.shutdown()
