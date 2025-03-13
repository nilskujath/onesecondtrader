import enum


class Rtype(enum.Enum):
    OHLCV_1S = 32
    OHLCV_1M = 33
    OHLCV_1H = 34
    OHLCV_1D = 35


class OrderType(enum.Enum):
    MARKET = enum.auto()
    LIMIT = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()


class TradeDirection(enum.Enum):
    LONG = enum.auto()
    SHORT = enum.auto()
