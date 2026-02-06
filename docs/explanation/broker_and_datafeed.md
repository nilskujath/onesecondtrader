# Broker and Datafeed

This page explains how the broker and datafeed abstractions make strategy code portable between backtest and live environments, how the simulated broker models order fills, and how the simulated datafeed replays historical data.

## The Abstraction Goal

A strategy publishes `OrderSubmissionRequest` events and receives `OrderAccepted`, `FillEvent`, and other response events. It never knows --- or needs to know --- what is on the other side of those events. This is the central abstraction:

```mermaid
flowchart LR
    ST["Strategy"]
    EB["EventBus"]
    SB["SimulatedBroker<br/>(backtest)"]
    LB["Live Broker Adapter<br/>(live trading)"]

    ST -- "OrderSubmissionRequest" --> EB
    EB -- "OrderSubmissionRequest" --> SB
    EB -- "OrderSubmissionRequest" -.-> LB
    SB -- "OrderAccepted / FillEvent" --> EB
    LB -- "OrderAccepted / FillEvent" -.-> EB
    EB -- "OrderAccepted / FillEvent" --> ST
```

The same strategy class, with identical `on_bar()` logic, runs in both environments. The Orchestrator simply wires a different broker implementation to the EventBus.

The datafeed follows the same pattern. `DatafeedBase` defines the interface: `connect()`, `disconnect()`, `subscribe()`, `unsubscribe()`, and `wait_until_complete()`. In backtesting, `SimulatedDatafeed` replays bars from a SQLite database. In live trading, a different implementation would stream bars from a market data provider.

!!! info "Design Decision: DatafeedBase Is Not a Subscriber"

    Unlike the broker and strategy, `DatafeedBase` does **not** extend `Subscriber`. It has no worker thread and no event queue. It only *publishes* events --- it never receives them.

    This makes sense because a datafeed is a *source*, not a *reactor*. It drives the system by injecting `BarReceived` events into the EventBus, but it has no reason to subscribe to any events itself.

[:material-link-variant: View BrokerBase API Reference](../reference/brokers/base.md) · [:material-link-variant: View DatafeedBase API Reference](../reference/datafeeds/base.md)

## SimulatedBroker Fill Models

The `SimulatedBroker` accepts orders, stores them as pending state, and evaluates them against each incoming `BarReceived` event. Different order types use different fill price models:

| Order Type | Trigger Condition | Fill Price | Rationale |
|---|---|---|---|
| **Market** | Next bar for the matching symbol | Bar open price | The order is "in the market" --- it fills at whatever price is available when the next bar opens. |
| **Limit** | Bar low &le; limit (buy) or bar high &ge; limit (sell) | Better of limit price and bar open | Limit orders guarantee a price *or better*. If the open is already favorable, you get the open. |
| **Stop** | Bar high &ge; stop (buy) or bar low &le; stop (sell) | Worse of stop price and bar open | Stop orders trigger at the stop level but may slip if the bar gaps through. The "worse of" models this slippage. |
| **Stop-Limit** | Bar high &ge; stop (buy) or bar low &le; stop (sell) | Converts to limit order | When the stop triggers, the order becomes a limit order and is evaluated by the limit fill model. |

!!! info "Design Decision: Fixed Processing Order"

    The broker processes pending orders in a fixed sequence on each bar:

    1. Market orders
    2. Stop orders
    3. Stop-limit orders
    4. Limit orders

    This ordering is deliberate. Stop-limit orders that trigger on a bar are converted into limit orders, and those limit orders are then evaluated *on the same bar* because limit processing happens after stop-limit processing. Without this fixed sequence, a stop-limit order could trigger but its resulting limit order would not be evaluated until the next bar.

=== "Backtest"

    - Orders are accepted or rejected **immediately** (no latency simulation).
    - Fill prices are deterministic, computed from OHLC values of the triggering bar.
    - One fill per order (no partial fills).
    - Commission is calculated as `max(quantity * commission_per_unit, minimum_commission_per_order)`.

=== "Live Trading"

    - Orders are sent to the exchange and acknowledged asynchronously.
    - Fill prices depend on real market conditions.
    - Partial fills are common.
    - Commission depends on the venue's fee structure.

!!! warning "Simulation Limitations"

    The simulated broker uses bar OHLC data, which means it cannot model intra-bar dynamics. Specifically:

    - **No intra-bar price path.** The broker does not know the order in which high and low were reached within the bar. It only knows that both were reached at some point.
    - **No partial fills.** Every triggered order fills completely in one event.
    - **No market impact.** Large orders fill at the same price as small orders.
    - **No latency.** Order acceptance is instantaneous. In live trading, there is always a round-trip delay.

    These simplifications make backtest results optimistic compared to live execution. They are appropriate for strategy development and research, but live trading requires careful consideration of these effects.

[:material-link-variant: View SimulatedBroker API Reference](../reference/brokers/simulated.md)

## DatafeedBase and Replay

The `SimulatedDatafeed` replays historical bars from a secmaster SQLite database. The replay model has three important properties:

### Timestamp-Ordered Delivery

Bars are queried from the database ordered by `ts_event` (then by symbol within the same timestamp). This ensures that the system processes all bars from timestamp *T* before any bar from timestamp *T+1*, regardless of how many symbols are subscribed.

### Grouped-by-Timestamp Publishing

Within a single timestamp, all bars are published before the datafeed calls `wait_until_system_idle()`. This means that if you have three symbols and all three have bars at the same timestamp, all three `BarReceived` events are published to the EventBus, and *then* the system waits for all subscribers to process them before moving on.

```python
for _, group in itertools.groupby(rows, key=lambda r: r[2]):  # (1)!
    if self._stop_event.is_set():
        return
    for bar in filter(None, map(to_bar, group)):
        self._publish(bar)
    self._event_bus.wait_until_system_idle()  # (2)!
```

1. Rows are grouped by the timestamp column (index 2). Each group contains all bars for one timestamp.
2. After publishing all bars for one timestamp, the datafeed blocks until every subscriber has processed its queue. This is the idle-wait protocol described in [Event-Driven Architecture](event_driven_architecture.md#the-idle-wait-protocol).

### Price Scaling

Prices in the secmaster database are stored as integers (multiplied by a `price_scale` factor, default 10^9^) for precision. The datafeed divides by `price_scale` when constructing `BarReceived` events to convert back to floating-point prices.

### Symbology Resolution

The datafeed joins against a `symbology` table to resolve ticker symbols, using time-bounded mappings (`start_date` to `end_date`). This supports instruments that change tickers over time --- the same underlying instrument can have different symbols in different date ranges.

[:material-link-variant: View SimulatedDatafeed API Reference](../reference/datafeeds/simulated.md)

## Implications for Live Trading

When moving from backtest to live trading, the **event contract stays the same**. A live broker adapter publishes the same event types (`OrderAccepted`, `FillEvent`, etc.) and a live datafeed publishes the same `BarReceived` events. Strategy code does not change.

What *does* change:

| Aspect | Backtest | Live |
|---|---|---|
| **Event timing** | Deterministic (idle-wait protocol) | Real-time, asynchronous |
| **Fill prices** | Computed from OHLC | Determined by the exchange |
| **Partial fills** | Not modeled | Expected |
| **Latency** | Zero (immediate accept/reject) | Network round-trip delay |
| **Order rejection** | Only for invalid parameters | Also for insufficient margin, halted symbols, etc. |
| **Data gaps** | None (database is complete) | Possible (network issues, exchange outages) |

The key architectural insight is that because strategies interact only with events and never call broker or datafeed methods directly, adding live trading support is purely an infrastructure concern. The strategy layer is unchanged.
