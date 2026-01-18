---
hide:
  - navigation
  - toc
---
<h1 style="text-align: center; margin-bottom: 10px; font-weight: normal; color: var(--md-default-fg-color);">
  The Trading Infrastructure Toolkit for Python
</h1>

<p style="text-align: center; font-size: 1.5em; color: var(--md-default-fg-color); margin-top: 0; margin-bottom: 60px;">
  Research, simulate, and deploy algorithmic strategies — all in one place.
</p>

!!! warning "Under Construction"

    This package is under construction! OneSecondTrader is still a work in progress, but don’t worry – a pre-release version is just around the corner. Grab a coffee and hang tight!

<div class="image-grid-light" style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 20px; margin: 20px 0;">
  <img src="images/placeholder-light.png" alt="Chart 1" style="width: 100%; height: auto;">
  <img src="images/placeholder-light.png" alt="Chart 2" style="width: 100%; height: auto;">
  <img src="images/placeholder-light.png" alt="Chart 3" style="width: 100%; height: auto;">
  <img src="images/placeholder-light.png" alt="Chart 4" style="width: 100%; height: auto;">
</div>

<div class="image-grid-dark" style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 20px; margin: 20px 0;">
  <img src="images/placeholder-dark.png" alt="Chart 1" style="width: 100%; height: auto;">
  <img src="images/placeholder-dark.png" alt="Chart 2" style="width: 100%; height: auto;">
  <img src="images/placeholder-dark.png" alt="Chart 3" style="width: 100%; height: auto;">
  <img src="images/placeholder-dark.png" alt="Chart 4" style="width: 100%; height: auto;">
</div>


## :material-airplane-takeoff: Quick**start**

Step 1: Install package

=== "pip"

    ```bash
    pip install onesecondtrader 
    ```

=== "poetry"

    ```python
    poetry add onesecondtrader
    ```
---

Step 2: Define strategy

```python
from onesecondtrader.strategies import StrategyBase
from onesecondtrader.indicators import SimpleMovingAverage
from onesecondtrader.models import OrderType, OrderSide
from onesecondtrader.events import BarReceived


class MySMACrossover(StrategyBase):
    def setup(self) -> None:
        self.fast_sma = self.add_indicator(SimpleMovingAverage(period=20))
        self.slow_sma = self.add_indicator(SimpleMovingAverage(period=100))

    def on_bar(self, event: BarReceived) -> None:
        if (
            self.fast_sma[-2] <= self.slow_sma[-2]
            and self.fast_sma.latest > self.slow_sma.latest
            and self.position <= 0
        ):
            self.submit_order(OrderType.MARKET, OrderSide.BUY, 1.0)

        if (
            self.fast_sma[-2] >= self.slow_sma[-2]
            and self.fast_sma.latest < self.slow_sma.latest
            and self.position >= 0
        ):
            self.submit_order(OrderType.MARKET, OrderSide.SELL, 1.0)
```
