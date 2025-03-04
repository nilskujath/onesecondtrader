import collections
import pandas as pd
import dataclasses
from onesecondtrader.ontology.enum_definitions import Rtype
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
