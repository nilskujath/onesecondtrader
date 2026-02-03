from onesecondtrader import events, indicators, models
from .base import StrategyBase, ParamSpec


class SMACrossover(StrategyBase):
    name = "SMA Crossover"
    parameters = {
        "bar_period": ParamSpec(default=models.BarPeriod.SECOND),
        "fast_period": ParamSpec(default=20, min=5, max=100, step=1),
        "slow_period": ParamSpec(default=100, min=10, max=500, step=1),
        "quantity": ParamSpec(default=1.0, min=0.1, max=100.0, step=0.1),
    }

    def setup(self) -> None:
        self.fast_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.fast_period)  # type: ignore[attr-defined]
        )
        self.slow_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.slow_period)  # type: ignore[attr-defined]
        )

    def on_bar(self, event: events.market.BarReceived) -> None:
        sym = event.symbol
        if (
            self.fast_sma[sym, -2] <= self.slow_sma[sym, -2]
            and self.fast_sma.latest(sym) > self.slow_sma.latest(sym)
            and self.position <= 0
        ):
            self.submit_order(
                models.OrderType.MARKET,
                models.TradeSide.BUY,
                self.quantity,  # type: ignore[attr-defined]
                action=models.ActionType.ENTRY,
                signal="sma_crossover_up",
            )

        if (
            self.fast_sma[sym, -2] >= self.slow_sma[sym, -2]
            and self.fast_sma.latest(sym) < self.slow_sma.latest(sym)
            and self.position >= 0
        ):
            self.submit_order(
                models.OrderType.MARKET,
                models.TradeSide.SELL,
                self.quantity,  # type: ignore[attr-defined]
                action=models.ActionType.EXIT,
                signal="sma_crossover_down",
            )
