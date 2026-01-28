import dotenv
import pandas as pd

from onesecondtrader.core.brokers import BrokerBase
from onesecondtrader.core.datafeeds import DatafeedBase
from onesecondtrader.core.messaging import EventBus
from onesecondtrader.core.strategies import StrategyBase
from .recorder import RunRecorder


class Orchestrator:
    db_path: str = "runs.db"
    mode: str = "backtest"

    def __init__(
        self,
        strategies: list[type[StrategyBase]],
        broker: type[BrokerBase],
        datafeed: type[DatafeedBase],
    ) -> None:
        dotenv.load_dotenv()
        self._strategy_classes = strategies
        self._broker_class = broker
        self._datafeed_class = datafeed
        self._event_bus: EventBus | None = None
        self._strategies: list[StrategyBase] = []
        self._broker: BrokerBase | None = None
        self._datafeed: DatafeedBase | None = None
        self._recorder: RunRecorder | None = None

    def run(self) -> None:
        run_id = self._generate_run_id()
        symbols = self._collect_symbols()
        bar_period = self._get_bar_period()

        self._event_bus = EventBus()

        self._recorder = self._create_recorder(run_id, symbols, bar_period)
        self._broker = self._broker_class(self._event_bus)
        self._strategies = [s(self._event_bus) for s in self._strategy_classes]
        self._datafeed = self._datafeed_class(self._event_bus)

        try:
            self._broker.connect()
            self._datafeed.connect()
            self._subscribe_symbols()
            self._datafeed.wait_until_complete()
            self._event_bus.wait_until_system_idle()
        finally:
            self._shutdown()

    def _generate_run_id(self) -> str:
        timestamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d_%H-%M-%S")
        strategy_names = "_".join(s.__name__ for s in self._strategy_classes)
        return f"{timestamp}_{strategy_names}"

    def _collect_symbols(self) -> list[str]:
        symbols = []
        for strategy_class in self._strategy_classes:
            symbols.extend(strategy_class.symbols)
        return list(set(symbols))

    def _get_bar_period(self) -> str | None:
        if not self._strategy_classes:
            return None
        params = self._strategy_classes[0].parameters
        if "bar_period" not in params:
            return None
        default = params["bar_period"].default
        if hasattr(default, "name"):
            return default.name  # type: ignore[no-any-return]
        return None

    def _create_recorder(
        self, run_id: str, symbols: list[str], bar_period: str | None
    ) -> RunRecorder:
        class ConfiguredRecorder(RunRecorder):
            db_path = self.db_path

        assert self._event_bus is not None
        return ConfiguredRecorder(
            event_bus=self._event_bus,
            run_id=run_id,
            strategy="_".join(s.name for s in self._strategy_classes),
            mode=self.mode,
            symbols=symbols,
            bar_period=bar_period,
        )

    def _subscribe_symbols(self) -> None:
        assert self._datafeed is not None
        for strategy_class in self._strategy_classes:
            bar_period = strategy_class.parameters["bar_period"].default
            for symbol in strategy_class.symbols:
                self._datafeed.subscribe(symbol, bar_period)  # type: ignore[arg-type]

    def _shutdown(self) -> None:
        if self._datafeed:
            self._datafeed.disconnect()
        if self._broker:
            self._broker.disconnect()
        for strategy in self._strategies:
            strategy.shutdown()
        if self._recorder:
            self._recorder.shutdown()
