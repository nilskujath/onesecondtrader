import queue
import sys
import threading
import enum
import dataclasses
import pandas as pd
import collections
import logging
import typing
import abc


########################################################################################
#   GLOBAL STOP EVENT                                                                  #
########################################################################################


GLOBAL_STOP_EVENT = threading.Event()


########################################################################################
#   Logging Setup                                                                      #
########################################################################################


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
)
logger = logging.getLogger(__name__)


########################################################################################
#   Event Messages                                                                     #
########################################################################################


class Rtype(enum.Enum):
    # Designed for compatibility with DataBento record type (rtype) discriminant
    # See https://databento.com/docs/standards-and-conventions/common-fields-enums-types
    OHLCV_1S = 32
    OHLCV_1M = 33
    OHLCV_1H = 34
    OHLCV_1D = 35


class OrderType(enum.Enum):
    MARKET = enum.auto()
    LIMIT = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()
    BRACKET = enum.auto()


class TradeDirection(enum.Enum):
    LONG = enum.auto()
    SHORT = enum.auto()


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


########################################################################################
#   Event Queues                                                                       #
########################################################################################


incoming_bar_event_message_queue = queue.Queue()
processed_bar_event_message_queue = queue.Queue()


########################################################################################
#   Strategy Registry                                                                  #
########################################################################################

# OneSecondTrader does not support trading the same instrument with two different
# strategies which is why a max.-one-strategy-per-symbol-mapping needs to be enforced
# via a Strategy Registry system.


strategy_registry: dict[int, list[str]] = {}


class StrategyRegistry:

    @staticmethod
    def register_strategy(strategy_id: int) -> None:
        if strategy_id in strategy_registry:
            logger.error(f"Strategy {strategy_id} is already registered")
            sys.exit(1)
        strategy_registry[strategy_id] = []
        logger.info(f"Registered strategy {strategy_id} to Strategy Registry")

    @staticmethod
    def register_symbols_to_strategy(
        strategy_id: int, symbols_to_register: list[str]
    ) -> None:
        if strategy_id not in strategy_registry:
            logger.error(f"Strategy with ID {strategy_id} is not registered")
            sys.exit(1)
        for (
            existing_strategy,
            registered_symbols,
        ) in strategy_registry.items():
            for symbol in symbols_to_register:
                if symbol in registered_symbols:
                    logger.error(
                        f"Symbol {symbol} is already registered to strategy "
                        f"with ID {strategy_id}"
                    )
                    sys.exit(1)

        strategy_registry[strategy_id].extend(symbols_to_register)
        logger.info(f"Registered symbol {symbols_to_register} to Strategy Registry")


########################################################################################
#   Market Data Connection
########################################################################################


class MarketDataConnector(abc.ABC):

    def __init__(self):
        self._instance_stop_event = threading.Event()

    @abc.abstractmethod
    def _get_next_bar_event_message(self) -> IncomingBarEventMessage:
        pass

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass
