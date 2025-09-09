from dataclasses import dataclass
import enum


class BrokerType(enum.Enum):
    """
    Enum for broker types.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `LOCAL_SIMULATED` | `enum.auto()` | Locally simulated broker |
    | `IB_SIMULATED` | `enum.auto()` | Interactive Brokers paper trading account |
    | `IB_LIVE` | `enum.auto()` | Interactive Brokers live trading account |
    | `MT5` | `enum.auto()` | MetaTrader 5 |
    """

    LOCAL_SIMULATED = enum.auto()
    IB_SIMULATED = enum.auto()
    IB_LIVE = enum.auto()
    MT5 = enum.auto()


@dataclass(frozen=True, slots=True)
class Bar:
    """
    Class for representing a OHLC(V) bar of market data.

    Attributes:
        open (float): Open price
        high (float): High price
        low (float): Low price
        close (float): Close price
        volume (float): Volume
    """

    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class Side(enum.Enum):
    """
    Enum for order sides.
    """

    BUY = enum.auto()
    SELL = enum.auto()


class TimeInForce(enum.Enum):
    """
    Order time-in-force specifications.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `DAY` | `enum.auto()` | Valid until end of trading day |
    | `FOK` | `enum.auto()` | Fill entire order immediately or cancel (Fill-or-Kill) |
    | `GTC` | `enum.auto()` | Active until explicitly cancelled (Good-Till-Cancelled) |
    | `GTD` | `enum.auto()` | Active until specified date (Good-Till-Date) |
    | `IOC` | `enum.auto()` | Execute available quantity immediately, cancel rest
        (Immediate-or-Cancel) |
    """

    DAY = enum.auto()
    FOK = enum.auto()
    GTC = enum.auto()
    GTD = enum.auto()
    IOC = enum.auto()


class OrderType(enum.Enum):
    """
    Enum for order types.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `MARKET` | `enum.auto()` | Market order |
    | `LIMIT` | `enum.auto()` | Limit order |
    | `STOP` | `enum.auto()` | Stop order |
    | `STOP_LIMIT` | `enum.auto()` | Stop-limit order |
    """

    MARKET = enum.auto()
    LIMIT = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()


class OrderLifecycleState(enum.Enum):
    """
    Enum for order lifecycle states.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `PENDING` | `enum.auto()` | Order has been submitted, but not yet acknowledged by
        the broker |
    | `OPEN` | `enum.auto()` | Order has been acknowledged by the broker, but not yet
        filled or cancelled |
    | `FILLED` | `enum.auto()` | Order has been filled |
    | `CANCELLED` | `enum.auto()` | Order has been cancelled |
    """

    PENDING = enum.auto()
    OPEN = enum.auto()
    PARTIALLY_FILLED = enum.auto()
    FILLED = enum.auto()
    CANCELLED = enum.auto()


class OrderRejectionReason(enum.Enum):
    """
    Enum for order rejection reasons.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `UNKNOWN` | `enum.auto()` | Unknown reason |
    | `NEGATIVE_QUANTITY` | `enum.auto()` | Negative quantity |
    """

    UNKNOWN = enum.auto()
    NEGATIVE_QUANTITY = enum.auto()
