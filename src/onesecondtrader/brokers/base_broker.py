import abc
from onesecondtrader import messaging
from onesecondtrader.messaging import events


class BaseBroker(abc.ABC):
    def __init__(self, event_bus: messaging.EventBus | None = None):
        self.event_bus: messaging.EventBus = (
            event_bus if event_bus else messaging.system_event_bus
        )
        self._is_connected: bool = False

    def connect(self) -> bool:
        if self._is_connected:
            return True
        self._subscribe_to_events()
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        if not self._is_connected:
            return
        try:
            self.event_bus.unsubscribe(events.System.Shutdown, self.on_system_shutdown)
        finally:
            self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def _subscribe_to_events(self) -> None:
        """
        Subscribe to relevant events from the event bus.
        """
        self.event_bus.subscribe(events.System.Shutdown, self.on_system_shutdown)
        self.event_bus.subscribe(events.Strategy.SymbolRelease, self.on_symbol_release)

    def on_system_shutdown(self, event: events.Base.Event) -> None:
        """
        Handle system shutdown events (ignore unrelated events).
        """
        if not isinstance(event, events.System.Shutdown):
            return
        # Default no-op
        return

    def on_symbol_release(self, event: events.Base.Event) -> None:
        """
        Handle portfolio symbol release events (ignore unrelated events).
        Intended for brokers to perform any symbol-specific cleanup if necessary.
        Default implementation is a no-op.
        """
        if not isinstance(event, events.Strategy.SymbolRelease):
            return
        # Default no-op
        return

    def on_request_market_order(self, event: events.Request.MarketOrder) -> None:
        """
        Handle market order requests.
        """
        pass

    def on_request_limit_order(self, event: events.Request.LimitOrder) -> None:
        """
        Handle limit order requests.
        """
        pass

    def on_request_stop_order(self, event: events.Request.StopOrder) -> None:
        """
        Handle stop order requests.
        """
        pass

    def on_request_stop_limit_order(self, event: events.Request.StopLimitOrder) -> None:
        """
        Handle stop limit order requests.
        """
        pass

    def on_request_cancel_order(self, event: events.Request.CancelOrder) -> None:
        """
        Handle cancel order requests.
        """
        pass

    def on_request_flush_symbol(self, event: events.Request.FlushSymbol) -> None:
        """
        Handle flush symbol requests.
        """
        pass

    def on_request_flush_all(self, event: events.Request.FlushAll) -> None:
        """
        Handle flush all requests.
        """
        pass
