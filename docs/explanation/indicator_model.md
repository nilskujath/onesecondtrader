# Indicator Model

This page explains the design decisions behind OneSecondTrader's indicator system: why each indicator produces a single scalar, how per-symbol state is isolated, how indicators register themselves automatically, and how plotting metadata is encoded for the charting backend.

## One Indicator, One Scalar

Every indicator in OneSecondTrader produces exactly **one `float` value per bar**. An SMA produces a single moving average value. An RSI produces a single oscillator value. The base class enforces this contract:

```python
@abc.abstractmethod
def _compute_indicator(self, incoming_bar: BarReceived) -> float: ...
```

!!! info "Design Decision: Single-Scalar Output"

    Many indicator libraries return multiple values from a single call --- for example, Bollinger Bands might return `(upper, middle, lower)` as a tuple. OneSecondTrader deliberately avoids this.

    With single-scalar output:

    - Every indicator has exactly one name, one history buffer, and one plot line. The charting backend, the `BarProcessed` event dictionary, and strategy code all use the same uniform interface.
    - Indicators are composable. You can combine any set of indicators without worrying about tuple unpacking, mixed return types, or indexing conventions.
    - The history buffer (a bounded `deque[float]`) is simple and fast. There is no need for structured arrays or named columns.

!!! example "Bollinger Bands: Decomposition in Practice"

    Bollinger Bands have three outputs: upper band, middle band (SMA), and lower band. In OneSecondTrader, these are three separate indicator classes:

    - `BollingerUpper` --- computes SMA + *k* &times; &sigma;
    - `BollingerLower` --- computes SMA - *k* &times; &sigma;
    - `SimpleMovingAverage` --- the middle band is just an SMA

    Each class independently maintains its own rolling window, computes one scalar, and has its own name (e.g., `BB_UPPER_20_2.0_CLOSE`). From the strategy's perspective, these are three ordinary indicators added via `add_indicator()`.

    The trade-off is redundancy: both Bollinger classes internally recompute the SMA and standard deviation. This is a deliberate choice --- the simplicity of a uniform single-scalar interface outweighs the cost of redundant arithmetic for typical indicator window sizes.

## Per-Symbol State Isolation

A strategy can trade multiple symbols simultaneously. Indicator state must be kept separate for each symbol --- the 20-period SMA of AAPL has nothing to do with the 20-period SMA of MSFT.

The base class achieves this with a dictionary of bounded FIFO buffers:

```python
self._history_data: dict[str, collections.deque[float]] = {}
```

When `update()` is called with a `BarReceived` event, the indicator computes the new value and appends it to the deque for that event's `symbol`. If no deque exists yet, one is created with `maxlen=max_history`:

```python
def update(self, incoming_bar: BarReceived) -> None:
    symbol = incoming_bar.symbol
    value = self._compute_indicator(incoming_bar)  # (1)!

    with self._lock:
        if symbol not in self._history_data:
            self._history_data[symbol] = collections.deque(maxlen=self._max_history)
        self._history_data[symbol].append(value)  # (2)!
```

1. Computation runs **outside** the lock. This means the lock is held only briefly during the append.
2. The `deque` with `maxlen` automatically evicts the oldest value when full, acting as a fixed-size sliding window.

Indicators like SMA and RSI that need rolling computation state (running sums, previous prices) maintain their own per-symbol dictionaries:

```python
# SMA maintains a per-symbol rolling window:
self._window: dict[str, collections.deque[float]] = {}

# RSI maintains per-symbol running averages:
self._prev_price: dict[str, float] = {}
self._avg_gain: dict[str, float] = {}
self._avg_loss: dict[str, float] = {}
```

This pattern ensures that calling `sma.update(bar_for_aapl)` followed by `sma.update(bar_for_msft)` never mixes state between the two symbols.

## Thread Safety

The indicator base class protects `_history_data` with a lock. Both writes (in `update()`) and reads (in `__getitem__()` and `latest()`) acquire the lock before accessing the dictionary:

```python
def __getitem__(self, key: tuple[str, int]) -> float:
    symbol, index = key
    with self._lock:
        history = self._history_data.get(symbol)
        if history is None:
            return np.nan
        try:
            return history[index]
        except IndexError:
            return np.nan
```

!!! warning "Thread Safety for Subclasses"

    The base class lock protects the history buffer, but **not** any state that subclasses maintain for their own computations. `_compute_indicator()` runs outside the lock.

    For indicators like SMA, this is fine in practice: the strategy's worker thread calls `update()` sequentially for each indicator, and no other thread accesses the SMA's rolling window.

    However, indicators that maintain mutable state (like RSI's `_prev_price`, `_avg_gain`, `_avg_loss` dictionaries) are technically unprotected from concurrent access by different threads. In the current design, this is safe because a single strategy instance processes bars sequentially in its own worker thread. But if you were to share an indicator instance across multiple strategies running in separate threads, the rolling state could be corrupted.

    The base class documents this explicitly: *"Subclasses that maintain internal state are responsible for ensuring its thread safety."*

## Auto-Registration via `__init_subclass__`

When you create a new indicator class by subclassing `IndicatorBase`, it is automatically registered in a global registry:

```python
_indicator_registry: dict[str, type[IndicatorBase]] = {}

class IndicatorBase(abc.ABC):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.__name__.startswith("_"):  # (1)!
            _indicator_registry[cls.__name__] = cls
```

1. Classes whose names start with an underscore (e.g., `_BaseOscillator`) are excluded. This convention is used for internal helper base classes that are not meant to be instantiated as standalone indicators.

This means creating a new indicator is a zero-configuration operation: define the class, and it becomes discoverable by the dashboard and any code that calls `get_registered_indicators()`.

The `discover_indicators()` function complements this by dynamically importing `.py` files from a directory. When the dashboard starts, it scans the indicator directories, imports the files, and the `__init_subclass__` hook triggers registration as a side effect of the import.

!!! info "Design Decision: Why Auto-Registration?"

    The alternative would be an explicit registration step --- a central file listing all indicators, or a decorator that must be applied to each class. Auto-registration eliminates this boilerplate: drop a new `.py` file into the indicators directory, and it appears in the dashboard immediately.

    The leading-underscore exclusion convention provides an escape hatch for helper classes that should not appear in the registry (e.g., abstract intermediate classes that provide shared functionality to a family of indicators).

## The `name` Property

Every indicator has a `name` property that returns a **canonical string identifier** encoding the indicator type and its configuration:

```python
# SimpleMovingAverage:
@property
def name(self) -> str:
    return f"SMA_{self.period}_{self.bar_field.name}"
# → "SMA_20_CLOSE"

# RSI:
@property
def name(self) -> str:
    return f"RSI_{self.period}_{self.bar_field.name}"
# → "RSI_14_CLOSE"

# BollingerUpper:
@property
def name(self) -> str:
    return f"BB_UPPER_{self.period}_{self.num_std}_{self.bar_field.name}"
# → "BB_UPPER_20_2.0_CLOSE"
```

This name serves as the **universal key** for an indicator's values throughout the system:

- In `BarProcessed.indicators`, the name is the dictionary key mapping to the computed value.
- In the charting backend, the name identifies which series to plot.
- In strategy code, the name is what you see when debugging or logging indicator values.

!!! info "Design Decision: Config-Encoded Names"

    By encoding parameters into the name, two instances of the same indicator type with different configurations (e.g., `SMA_20_CLOSE` vs `SMA_50_CLOSE`) are automatically distinguishable. There is no risk of name collisions, and no need for a separate naming or aliasing mechanism.

## Plotting Metadata

Each indicator carries three plotting attributes set at construction time:

| Attribute | Type | Purpose |
|---|---|---|
| `plot_at` | `int` | Identifies which chart panel the indicator appears on. `0` = the main price panel, other values create separate sub-panels. |
| `plot_as` | `PlotStyle` | Visual rendering style: `LINE`, `HISTOGRAM`, `DOTS`, `DASH1`/`2`/`3`, `BACKGROUND1`/`2`. |
| `plot_color` | `PlotColor` | Rendering color: `BLACK`, `RED`, `BLUE`, `GREEN`, `ORANGE`, `PURPLE`, `CYAN`, `MAGENTA`, `YELLOW`, `WHITE`, `TEAL`. |

!!! info "Design Decision: Metadata on the Indicator"

    Plotting configuration lives on the indicator itself rather than in a separate charting configuration file. The rationale is that the indicator's author knows best how it should be displayed: an RSI belongs in a separate panel (not overlaid on prices), and Bollinger Bands belong on the price panel.

    This also means that when an indicator is added to a strategy, its visual representation is fully determined without any additional configuration step.

### The Encoding Scheme

When the strategy emits a `BarProcessed` event, it encodes each indicator's plotting metadata into the dictionary key:

```
{plot_at:02d}{style_code}{color_code}_{name}
```

For example, an SMA with `plot_at=0`, `plot_as=LINE`, `plot_color=BLUE` and name `SMA_20_CLOSE` becomes:

```
00LB_SMA_20_CLOSE
```

The charting backend parses this prefix to determine where and how to draw the indicator without needing access to the indicator object itself. The encoding uses single-character codes:

??? note "Style and Color Code Tables"

    **Style Codes:**

    | PlotStyle | Code |
    |---|---|
    | `LINE` | `L` |
    | `HISTOGRAM` | `H` |
    | `DOTS` | `D` |
    | `DASH1` | `1` |
    | `DASH2` | `2` |
    | `DASH3` | `3` |
    | `BACKGROUND1` | `A` |
    | `BACKGROUND2` | `E` |

    **Color Codes:**

    | PlotColor | Code |
    |---|---|
    | `BLACK` | `K` |
    | `RED` | `R` |
    | `BLUE` | `B` |
    | `GREEN` | `G` |
    | `ORANGE` | `O` |
    | `PURPLE` | `P` |
    | `CYAN` | `C` |
    | `MAGENTA` | `M` |
    | `YELLOW` | `Y` |
    | `WHITE` | `W` |
    | `TEAL` | `T` |

OHLCV indicators (`OPEN`, `HIGH`, `LOW`, `CLOSE`, `VOLUME`) are excluded from the `BarProcessed` indicator dictionary by default (they are already represented in the bar's own fields), unless their `plot_at` is changed from the default value of `99`.

```mermaid
classDiagram
    class IndicatorBase {
        <<abstract>>
        -_history_data: dict~str, deque~float~~
        -_lock: Lock
        -_plot_at: int
        -_plot_as: PlotStyle
        -_plot_color: PlotColor
        +name* str
        +update(bar: BarReceived) void
        +latest(symbol: str) float
        #_compute_indicator(bar: BarReceived)* float
    }

    class SimpleMovingAverage {
        -_window: dict~str, deque~float~~
        +period: int
        +bar_field: BarField
        +name: "SMA_{period}_{field}"
    }

    class RSI {
        -_prev_price: dict~str, float~
        -_avg_gain: dict~str, float~
        -_avg_loss: dict~str, float~
        +period: int
        +bar_field: BarField
        +name: "RSI_{period}_{field}"
    }

    class BollingerUpper {
        -_window: dict~str, deque~float~~
        +period: int
        +num_std: float
        +bar_field: BarField
        +name: "BB_UPPER_{period}_{std}_{field}"
    }

    IndicatorBase <|-- SimpleMovingAverage
    IndicatorBase <|-- RSI
    IndicatorBase <|-- BollingerUpper
```

[:material-link-variant: View IndicatorBase API Reference](../reference/indicators/base.md)
