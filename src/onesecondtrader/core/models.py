from dataclasses import dataclass
import enum


@dataclass(frozen=True, slots=True)
class Bar:
    """
    Class for representing a OHLC(V) bar of market data.

    Attributes:
        open (float): Open price
        high (float): High price
        low (float): Low price
        close (float): Close price
        volume (int | None): Volume
    """

    open: float
    high: float
    low: float
    close: float
    volume: int | None = None


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
    | `IOC` | `enum.auto()` | Execute available quantity immediately, cancel rest (Immediate-or-Cancel) |
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
    | `PENDING` | `enum.auto()` | Order has been submitted, but not yet acknowledged by the brokers |
    | `OPEN` | `enum.auto()` | Order has been acknowledged by the brokers, but not yet filled or cancelled |
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


class RecordType(enum.Enum):
    """
    Enum for Databento record types.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `OHLCV_1S` | `32` | 1-second bars |
    | `OHLCV_1M` | `33` | 1-minute bars |
    | `OHLCV_1H` | `34` | 1-hour bars |
    | `OHLCV_1D` | `35` | 1-day bars |
    """

    OHLCV_1S = 32
    OHLCV_1M = 33
    OHLCV_1H = 34
    OHLCV_1D = 35

    @classmethod
    def to_string(cls, rtype: int) -> str:
        match rtype:
            case cls.OHLCV_1S.value:
                return "1-second bars"
            case cls.OHLCV_1M.value:
                return "1-minute bars"
            case cls.OHLCV_1H.value:
                return "1-hour bars"
            case cls.OHLCV_1D.value:
                return "daily bars"
            case _:
                return f"unknown ({rtype})"


class XMAMode(enum.Enum):
    """
    Enum for moving average modes.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `OPEN` | `enum.auto()` | Open price |
    | `HIGH` | `enum.auto()` | High price |
    | `LOW` | `enum.auto()` | Low price |
    | `CLOSE` | `enum.auto()` | Close price |
    | `TYPICAL_PRICE` | `enum.auto()` | Typical price ((H+ L + C) / 3) |
    | `WEIGHTED_CLOSE` | `enum.auto()` | Weighted close price ((H + L + 2*C) / 4) |
    """

    OPEN = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()
    CLOSE = enum.auto()
    TYPICAL_PRICE = enum.auto()
    WEIGHTED_CLOSE = enum.auto()


class Position:
    pass


class StrategyShutdownMode(enum.Enum):
    """
    Enum for strategy shutdown modes.

    **Attributes:**

    | Enum | Value | Description |
    |------|-------|-------------|
    | `SOFT` | `enum.auto()` | Do not open new positions; wait until current positions close naturally |
    | `HARD` | `enum.auto()` | Close all positions immediately with market orders |
    """

    SOFT = enum.auto()
    HARD = enum.auto()
