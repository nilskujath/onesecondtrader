import collections
import pandas as pd
import dataclasses
from onesecondtrader.ontology.enum_definitions import Rtype, OrderType, TradeDirection
import threading


GLOBAL_STOP_EVENT = threading.Event()


OHLCV = collections.namedtuple("OHLCV", ["open", "high", "low", "close", "volume"])


@dataclasses.dataclass
class IncomingBarEventMessage:
    ts_event: pd.Timestamp
    bar_rtype: Rtype
    symbol: str
    ohlcv: OHLCV


@dataclasses.dataclass
class ProcessedBarEventMessage:
    strategy_id: int
    ts_event: pd.Timestamp
    bar_rtype: Rtype
    symbol: str
    ohlcv: OHLCV
    indicator_values: dict


@dataclasses.dataclass
class StrategyOrderEventMessage:
    strategy_id: int
    ts_event: pd.Timestamp
    order_type: OrderType
    quantity: int
    trade_direction: TradeDirection


@dataclasses.dataclass
class StrategyMarketOrderEventMessage(StrategyOrderEventMessage):
    order_type: OrderType.MARKET


@dataclasses.dataclass
class StrategyLimitOrderEventMessage(StrategyOrderEventMessage):
    order_type: OrderType.LIMIT
    limit_price: float


@dataclasses.dataclass
class StrategyStopOrderEventMessage(StrategyOrderEventMessage):
    order_type: OrderType.STOP
    stop_price: float


@dataclasses.dataclass
class StrategyStopLimitOrderEventMessage(StrategyOrderEventMessage):
    order_type: OrderType.STOP_LIMIT
    stop_price: float
    limit_price: float
