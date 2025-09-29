import threading

from onesecondtrader import messaging
from onesecondtrader.messaging import events
from onesecondtrader.strategies import base_strategy
from onesecondtrader.monitoring import console
from onesecondtrader.core import models


class Portfolio:
    def __init__(self, event_bus: messaging.EventBus | None = None):
        """
        Initialize the Portfolio class and subscribe to events.
        Most importantly, the `symbol_to_strategy` registry is initialized,
         which keeps track of which symbols are currently assigned to which strategy
         in order to enforce exclusive symbol ownership.

        Args:
            event_bus (messaging.EventBus | None): Event bus to use; defaults to
                 messaging.system_event_bus when None.

        Attributes:
            self._lock (threading.Lock): Lock for thread-safe operations.
            self.event_bus (messaging.EventBus): Event bus used for communication
                 between the trading infrastructure's components.
            self.symbols_to_strategy (dict[str, base_strategy.Strategy]): Registry of
                 symbols to strategies.
        """
        # ------------------------------------------------------------------------------
        # INITIALIZE LOCK FOR THREAD-SAFE OPERATIONS
        self._lock: threading.Lock = threading.Lock()

        # ------------------------------------------------------------------------------
        # INITIALIZE EVENT BUS AND SUBSCRIBE TO EVENTS
        self.event_bus: messaging.EventBus = (
            event_bus if event_bus else messaging.system_event_bus
        )
        self.event_bus.subscribe(events.Strategy.SymbolRelease, self.on_symbol_release)

        # ------------------------------------------------------------------------------
        # INITIALIZE SYMBOLS TO STRATEGY REGISTRY
        self.symbols_to_strategy: dict[str, base_strategy.Strategy] = {}

    def on_symbol_release(self, event: messaging.events.Base.Event) -> None:
        """
        Event handler for symbol release events (`events.Strategy.SymbolRelease`).
        The symbol is removed from the `symbols_to_strategy` registry.

        Args:
            event (messaging.events.Base.Event): Symbol release event.
        """
        # ------------------------------------------------------------------------------
        # IGNORE UNRELATED EVENT TYPES
        if not isinstance(event, events.Strategy.SymbolRelease):
            return

        # ------------------------------------------------------------------------------
        # RELEASE SYMBOL FROM STRATEGY
        symbol = event.symbol
        with self._lock:
            if symbol in self.symbols_to_strategy:
                del self.symbols_to_strategy[symbol]
                console.logger.info(
                    f"on_symbol_release: symbol {symbol} released from "
                    f"{getattr(event.strategy, 'name', type(event.strategy).__name__)}"
                )
            else:
                console.logger.warning(
                    f"on_symbol_release: symbol {symbol} not owned by "
                    f"{getattr(event.strategy, 'name', type(event.strategy).__name__)}"
                )

    def assign_symbols(
        self, strategy_instance: base_strategy.Strategy, symbols: list[str]
    ) -> bool:
        """
        Assign a list of symbols to a strategy if no conflicts exist and notify the
         strategy of the assignment.

        Args:
            strategy_instance (base_strategy.Strategy): Strategy instance to assign
                symbols to.
            symbols (list[str]): List of symbols to assign.
        """
        # ------------------------------------------------------------------------------
        # VALIDATE THAT INSTANCE IS A SUBCLASS OF base_strategy.Strategy
        if not isinstance(strategy_instance, base_strategy.Strategy):
            console.logger.error("assign_symbols: strategy must inherit from Strategy")
            return False

        # ------------------------------------------------------------------------------
        # CHECK FOR CONFLICTS
        non_conflicting: list[str] = []
        conflicting: list[str] = []
        with self._lock:
            for symbol in symbols:
                owner = self.symbols_to_strategy.get(symbol)
                if owner is None:
                    non_conflicting.append(symbol)
                else:
                    conflicting.append(symbol)
        if conflicting:
            console.logger.warning(
                "assign_symbols: symbols not assigned due to conflicts; "
                "use Portfolio.assign_symbols(...) after resolving. "
                f"non_conflicting={non_conflicting}, conflicts={conflicting}"
            )
            return False
        else:
            # --------------------------------------------------------------------------
            # ASSIGN SYMBOLS TO REGISTRY
            for symbol in symbols:
                self.symbols_to_strategy[symbol] = strategy_instance

            # --------------------------------------------------------------------------
            # PUBLISH SYMBOL ASSIGNMENT EVENT
            # noinspection PyArgumentList
            self.event_bus.publish(
                events.Strategy.SymbolAssignment(
                    strategy=strategy_instance,
                    symbol_list=symbols,
                )
            )
            return True

    def unassign_symbols(
        self,
        symbols: list[str],
        shutdown_mode: models.SymbolShutdownMode = models.SymbolShutdownMode.SOFT,
    ) -> bool:
        """
        Unassign a list of symbols from their owning strategy if all of them have
         previously been assigned to a strategy.
        Calling this methods will request the owning strategy to stop trading the symbol
         in the manner dictated via the `shutdown_mode` argument (default to soft
         shutdown, i.e. wait for open positions to close naturally and release symbols
         once they are flat).
        After the owning strategy has released the symbol, the symbol is unassigned from
         the portfolio via the `on_symbol_release` event handler.

        Args:
            symbols (list[str]): List of symbols to unassign.
            shutdown_mode (models.SymbolShutdownMode): Shutdown mode to use. Defaults
                to `models.SymbolShutdownMode.SOFT`.
        """
        # ------------------------------------------------------------------------------
        # CHECK THAT SYMBOLS ARE REGISTERED
        conflicting: list[str] = []
        with self._lock:
            for symbol in symbols:
                if symbol not in self.symbols_to_strategy:
                    conflicting.append(symbol)
            if conflicting:
                console.logger.warning(
                    "unassign_symbols: symbols not unassigned due to conflicts; "
                    f"conflicts={conflicting}. "
                    f"Use Portfolio.unassign_symbols(...) after resolving."
                )
                return False
            else:
                # ----------------------------------------------------------------------
                # PUBLISH STOP TRADING SYMBOL EVENT FOR EACH SYMBOL
                for symbol in symbols:
                    # noinspection PyArgumentList
                    self.event_bus.publish(
                        events.Strategy.StopTradingSymbol(
                            strategy=self.symbols_to_strategy[symbol],
                            symbol=symbol,
                            shutdown_mode=shutdown_mode,
                        )
                    )
                    console.logger.info(
                        f"unassign_symbols: trading stop for {symbol} trading strategy "
                        f"{self.symbols_to_strategy[symbol]} requested with shutdown"
                        f"mode {shutdown_mode.name}"
                    )
                return True
