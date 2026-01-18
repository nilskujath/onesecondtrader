from onesecondtrader import events, indicators, models
from .base import StrategyBase


class SMACrossover(StrategyBase):
    fast_period: int = 20
    slow_period: int = 100
    quantity: float = 1.0

    def setup(self) -> None:
        self.fast_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.fast_period)
        )
        self.slow_sma = self.add_indicator(
            indicators.SimpleMovingAverage(period=self.slow_period)
        )

    def on_bar(self, event: events.BarReceived) -> None:
        if (
            self.fast_sma[-2] <= self.slow_sma[-2]
            and self.fast_sma.latest > self.slow_sma.latest
            and self.position <= 0
        ):
            self.submit_order(
                models.OrderType.MARKET, models.OrderSide.BUY, self.quantity
            )

        if (
            self.fast_sma[-2] >= self.slow_sma[-2]
            and self.fast_sma.latest < self.slow_sma.latest
            and self.position >= 0
        ):
            self.submit_order(
                models.OrderType.MARKET, models.OrderSide.SELL, self.quantity
            )
