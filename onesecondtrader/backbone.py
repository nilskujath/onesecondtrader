import sys
import threading
import logging


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


########################################################################################
#   Event Queues                                                                       #
########################################################################################


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
