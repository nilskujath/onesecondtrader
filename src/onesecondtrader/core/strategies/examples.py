from onesecondtrader.core import events, indicators, models
from .base import StrategyBase


class SMACrossover(StrategyBase):
    name = "SMA Crossover"
    parameters = {
        "bar_period": models.ParamSpec(default=models.BarPeriod.SECOND),
        "fast_period": models.ParamSpec(default=20, min=5, max=100, step=1),
        "slow_period": models.ParamSpec(default=100, min=10, max=500, step=1),
        "quantity": models.ParamSpec(default=1.0, min=0.1, max=100.0, step=0.1),
    }

    def setup(self) -> None:
        self.fast_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.fast_period)  # type: ignore[attr-defined]
        )
        self.slow_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.slow_period)  # type: ignore[attr-defined]
        )

    def on_bar(self, event: events.BarReceived) -> None:
        if (
            self.fast_sma[-2] <= self.slow_sma[-2]
            and self.fast_sma.latest > self.slow_sma.latest
            and self.position <= 0
        ):
            self.submit_order(
                models.OrderType.MARKET,
                models.OrderSide.BUY,
                self.quantity,  # type: ignore[attr-defined]
                action=models.ActionType.ENTRY,
                signal="sma_crossover_up",
            )

        if (
            self.fast_sma[-2] >= self.slow_sma[-2]
            and self.fast_sma.latest < self.slow_sma.latest
            and self.position >= 0
        ):
            self.submit_order(
                models.OrderType.MARKET,
                models.OrderSide.SELL,
                self.quantity,  # type: ignore[attr-defined]
                action=models.ActionType.EXIT,
                signal="sma_crossover_down",
            )
