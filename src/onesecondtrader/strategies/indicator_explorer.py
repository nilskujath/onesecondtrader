"""No-op strategy for indicator exploration.

IndicatorExplorer exists solely to register indicators dynamically and let
the Orchestrator / RunRecorder pipeline process bars identically to a real
backtest.  It performs no trading logic.
"""

from onesecondtrader import events, models
from .base import ParamSpec, StrategyBase


class IndicatorExplorer(StrategyBase):
    name = "Indicator Explorer"
    parameters = {
        "bar_period": ParamSpec(default=models.BarPeriod.SECOND),
    }

    def setup(self) -> None:
        pass  # Indicators are registered dynamically via configured subclass

    def on_bar(self, event: events.market.BarReceived) -> None:
        pass  # No trading logic -- pure indicator computation
