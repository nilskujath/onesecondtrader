"""
This module provides the Portfolio class.
"""

import threading
from collections.abc import Iterable
from onesecondtrader import messaging
from onesecondtrader.messaging import events
from onesecondtrader.monitoring import console
from onesecondtrader.brokers import base_broker
from onesecondtrader.strategies import base_strategy
from onesecondtrader.core.models import StrategyShutdownMode


class Portfolio:
    """
    The Portfolio class orchestrates the trading infrastructure's components.
    It manages the broker connection, market data reception, and strategy execution.

    Multiple instances of the same Strategy class can be registered concurrently.
    Symbol ownership is exclusive and enforced by the portfolio: each symbol may be
    owned by at most one strategy instance at a time. Use `add_strategy()` with a list
    of symbols or `assign_symbols(...)` with a specific strategy and a list of symbols
    to claim symbols; `owner_of(symbol)` returns the current owner.
    """

    def __init__(
        self,
        event_bus: messaging.EventBus | None = None,
        broker_class: type[base_broker.BaseBroker] | None = None,
    ):
        """
        Initialize the Portfolio class, subscribe to events, and connect to the broker.

        Args:
            event_bus (EventBus | None): Event bus to use; defaults to
                system_event_bus when None.
            broker_class (type[base_broker.BaseBroker] | None): Broker class to
                instantiate and connect. Must be a subclass of BaseBroker.

        Attributes:
            self.event_bus (eventbus.EventBus): Event bus used for communication between
                the trading infrastructure's components.
            self._lock (threading.Lock): Lock for thread-safe operations.
            self._strategies (set[base_strategy.Strategy]): Registered strategy
                instances.
            self._symbol_owner (dict[str, base_strategy.Strategy]): Exclusive symbol
                ownership map; each symbol is owned by at most one strategy instance at
                a time.
            self.strategy_removal_pending (set[base_strategy.Strategy]): Set of
                strategies that are still active but marked for removal once all symbols
                are released.
            self.broker (base_broker.BaseBroker | None): Instantiated broker; may be
                disconnected if connect failed.
        """
        # INITIALIZE EVENT BUS
        # ------------------------------------------------------------------------------
        self.event_bus: messaging.EventBus = (
            event_bus if event_bus else messaging.system_event_bus
        )

        # SUBSCRIBE HANDLER METHODS TO EVENTS VIA event_bus.subscribe
        # ------------------------------------------------------------------------------
        self.event_bus.subscribe(events.Strategy.SymbolRelease, self.on_symbol_release)

        # INITIALIZE LOCK FOR THREAD-SAFE OPERATIONS WITHIN THE PORTFOLIO
        # ------------------------------------------------------------------------------
        self._lock = threading.Lock()

        # KEEP TRACK OF STRATEGIES AND SYMBOL OWNERSHIP
        # ------------------------------------------------------------------------------
        self._strategies: set[base_strategy.Strategy] = set()
        self.strategy_removal_pending: set[base_strategy.Strategy] = set()
        self._symbol_owner: dict[str, base_strategy.Strategy] = {}

        # INITIALIZE BROKER
        # ------------------------------------------------------------------------------
        # TODO Decouple by also doing this via an event
        self.broker: base_broker.BaseBroker | None = None
        if broker_class is None or not issubclass(broker_class, base_broker.BaseBroker):
            broker_name = (
                getattr(broker_class, "__name__", str(broker_class))
                if broker_class
                else None
            )
            console.logger.error(
                "Portfolio requires a valid broker_class (subclass of BaseBroker), "
                f"got {broker_name}"
            )
            return
        try:
            self.broker = broker_class(self.event_bus)
        except Exception as e:
            console.logger.error(
                f"Failed to instantiate broker "
                f"{getattr(broker_class, '__name__', str(broker_class))}: {e}"
            )
            return

        # CONNECT TO BROKER
        # ------------------------------------------------------------------------------
        try:
            connected = self.broker.connect()
            if not connected:
                console.logger.error(
                    f"Failed to connect broker {type(self.broker).__name__}"
                )
        except Exception as e:
            console.logger.error(f"Broker connect failed: {e}")

    def add_strategy(
        self,
        strategy_instance: base_strategy.Strategy,
        symbols: Iterable[str] | None = None,
    ) -> bool:
        """
        Register a Strategy instance and optionally assign a list of symbols to it.

        If symbols are provided, potential conflicts are checked first under a lock.
        If any conflicts exist, no symbols are assigned; a warning is logged listing
        both non_conflicting and conflicting symbols and instructions to use
        assign_symbols(...) are provided.
        If no conflicts exist, all provided symbols are claimed by the strategy.

        Args:
            strategy_instance (base_strategy.Strategy): Strategy instance to register.
            symbols (Iterable[str] | None): Optional list of symbols to assign to the
                strategy.

        Returns:
            bool: True if the strategy was registered, False otherwise.
        """
        # VALIDATE THAT INSTANCE IS A SUBCLASS OF base_strategy.Strategy
        # ------------------------------------------------------------------------------
        if not isinstance(strategy_instance, base_strategy.Strategy):
            console.logger.error("add_strategy: strategy must inherit from Strategy")
            return False

        # ADD STRATEGY INSTANCE TO REGISTRY IF NOT ALREADY REGISTERED
        # ------------------------------------------------------------------------------
        with self._lock:
            if strategy_instance in self._strategies:
                console.logger.warning("add_strategy: strategy already registered")
                return False
            self._strategies.add(strategy_instance)

        # ASSIGN SYMBOLS IF PROVIDED AND NO CONFLICTS EXIST, ELSE LOG WARNING
        # ------------------------------------------------------------------------------
        if symbols is not None:
            # Create an ordered list of unique, non-empty, trimmed symbols
            symbols_list = list(
                dict.fromkeys(s.strip() for s in symbols if s and s.strip())
            )

            # Check for conflicts, claim symbols for strategy if no conflicts arise
            if symbols_list:
                non_conflicting: list[str] = []
                conflicting: list[str] = []
                with self._lock:
                    for sym in symbols_list:
                        owner = self._symbol_owner.get(sym)
                        if owner is None or owner is strategy_instance:
                            non_conflicting.append(sym)
                        else:
                            conflicting.append(sym)
                if conflicting:
                    console.logger.warning(
                        "add_strategy: symbols not assigned due to conflicts; "
                        "use Portfolio.assign_symbols(...) after resolving. "
                        f"non_conflicting={non_conflicting}, conflicts={conflicting}"
                    )
                    return False
                else:
                    for sym in symbols_list:
                        self._symbol_owner[sym] = strategy_instance
                    self.event_bus.publish(
                        events.Strategy.SymbolAssignment(
                            strategy=strategy_instance,
                            symbol_list=symbols_list,
                        )
                    )
                    return True

        return True

    def remove_strategy(
        self,
        strategy_instance: base_strategy.Strategy,
        shutdown_mode: StrategyShutdownMode = StrategyShutdownMode.SOFT,
    ) -> bool:
        """
        Mark a strategy for removal and request it to close its positions in the manner
        dictated via the `shutdown_mode` argument (default to soft shutdown, i.e. wait
        for open positions to close naturally and release symbols once they are flat).

        Args:
            strategy_instance (base_strategy.Strategy): Strategy instance to remove.
            shutdown_mode (StrategyShutdownMode): Shutdown mode to use. Defaults to
                StrategyShutdownMode.SOFT.
        """

        # IF STRATEGY IS REGISTERED, MARK IT FOR REMOVAL AND PUBLISH STOP TRADING EVENT
        # ------------------------------------------------------------------------------
        with self._lock:
            if strategy_instance not in self._strategies:
                console.logger.warning("remove_strategy: strategy not registered")
                return False
            self.strategy_removal_pending.add(strategy_instance)

        # PUBLISH STOP TRADING REQUEST TO EVENT BUS
        # ------------------------------------------------------------------------------
        self.event_bus.publish(
            events.Strategy.StopTrading(
                strategy=strategy_instance,
                shutdown_mode=shutdown_mode,
            )
        )
        return True

    def assign_symbols(
        self, strategy_instance: base_strategy.Strategy, symbols: Iterable[str]
    ):
        """
        Assign a list of symbols to a strategy.

        Args:
            strategy_instance (base_strategy.Strategy): Strategy instance to assign
                symbols to.
            symbols (Iterable[str]): List of symbols to assign.
        """
        # IF STRATEGY IS REGISTERED, MARK IT FOR REMOVAL AND PUBLISH STOP TRADING EVENT
        # ------------------------------------------------------------------------------
        with self._lock:
            if strategy_instance not in self._strategies:
                console.logger.warning("remove_strategy: strategy not registered")
                return False
            self.strategy_removal_pending.add(strategy_instance)

        # ASSIGN SYMBOLS IF PROVIDED AND NO CONFLICTS EXIST, ELSE LOG WARNING
        # ------------------------------------------------------------------------------
        # TODO This is an repetition of the same logic as in add_strategy; refactor

        if symbols is not None:
            # Create an ordered list of unique, non-empty, trimmed symbols
            symbols_list = list(
                dict.fromkeys(s.strip() for s in symbols if s and s.strip())
            )

            # Check for conflicts, claim symbols for strategy if no conflicts arise
            if symbols_list:
                non_conflicting: list[str] = []
                conflicting: list[str] = []
                with self._lock:
                    for sym in symbols_list:
                        owner = self._symbol_owner.get(sym)
                        if owner is None or owner is strategy_instance:
                            non_conflicting.append(sym)
                        else:
                            conflicting.append(sym)
                if conflicting:
                    console.logger.warning(
                        "assign_symbols: symbols not assigned due to conflicts; "
                        "use Portfolio.assign_symbols(...) after resolving. "
                        f"non_conflicting={non_conflicting}, conflicts={conflicting}"
                    )
                    return False
                else:
                    for sym in symbols_list:
                        self._symbol_owner[sym] = strategy_instance
                    self.event_bus.publish(
                        events.Strategy.SymbolAssignment(
                            strategy=strategy_instance,
                            symbol_list=symbols_list,
                        )
                    )
                    return True

    def unassign_symbols(
        self, strategy: base_strategy.Strategy, symbols: Iterable[str]
    ) -> list[str]:
        if not isinstance(strategy, base_strategy.Strategy):
            console.logger.error(
                "unassign_symbols: strategy must inherit from Strategy"
            )
            return []
        symbols_list = list(
            dict.fromkeys(s.strip() for s in symbols if s and s.strip())
        )
        if not symbols_list:
            return []
        removed: list[str] = []
        with self._lock:
            for sym in symbols_list:
                if self._symbol_owner.get(sym) is strategy:
                    del self._symbol_owner[sym]
                    removed.append(sym)
        if removed:
            strategy.remove_symbols(removed)
        return removed

    def owner_of(self, symbol: str) -> base_strategy.Strategy | None:
        """
        Return the owning strategy for a symbol or None if unowned.
        """
        with self._lock:
            return self._symbol_owner.get(symbol)

    def on_symbol_release(self, event: events.Base.Event) -> None:
        """
        Handle symbol release events. Ignores unrelated event types.

        If a symbol is released, it is unassigned from the strategy that owns it
        (inside the symbol_owner registry). If the strategy is marked for removal and
        has no more symbols assigned to it, it is automatically deregistered.
        """

        # IGNORE UNRELATED EVENT TYPES
        # ------------------------------------------------------------------------------
        if not isinstance(event, events.Strategy.SymbolRelease):
            return

        # IF STRATEGY IS REGISTERED, RELEASE SYMBOL FROM STRATEGY
        # ------------------------------------------------------------------------------
        # TODO This needs reworking; this will be the same logic as unassig_symbols
        strategy = event.strategy
        with self._lock:
            if strategy not in self._strategies:
                console.logger.warning("on_symbol_release: strategy not registered")
                return
        removed = self.unassign_symbols(strategy, [event.symbol])
        if not removed:
            console.logger.warning(
                f"on_symbol_release: symbol {event.symbol} not owned by "
                f"{getattr(event.strategy, 'name', type(event.strategy).__name__)}"
            )
            return
        pending = False
        with self._lock:
            pending = strategy in self.strategy_removal_pending
            has_owned_left = any(
                owner is strategy for owner in self._symbol_owner.values()
            )
        if pending and not has_owned_left:
            try:
                if bool(strategy.is_flat()):
                    with self._lock:
                        if strategy in self._strategies:
                            self._strategies.remove(strategy)
                        self.strategy_removal_pending.discard(strategy)
                    console.logger.info(
                        f"Strategy {getattr(strategy, 'name', type(strategy).__name__)} "
                        f"removed: all symbols released and flat"
                    )
            except Exception:
                pass
        console.logger.info(
            f"on_symbol_release: symbol {event.symbol} released from "
            f"{getattr(event.strategy, 'name', type(event.strategy).__name__)}"
        )
