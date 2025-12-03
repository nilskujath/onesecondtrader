import abc
import uuid

from onesecondtrader.core import BaseConsumer, Events, event_bus


class BaseBroker(BaseConsumer):
    """
    Base class for all brokers.
    """

    def __init__(self) -> None:
        super().__init__()
        event_bus.subscribe(self, Events.SubmitOrder)
        event_bus.subscribe(self, Events.CancelOrder)
        event_bus.subscribe(self, Events.ModifyOrder)

    def on_event(self, event) -> None:
        match event:
            case Events.SubmitOrder():
                self.on_submit_order(event)
            case Events.CancelOrder():
                self.on_cancel_order(event)
            case Events.ModifyOrder():
                self.on_modify_order(event)

    @abc.abstractmethod
    def on_submit_order(self, event: Events.SubmitOrder) -> None:
        pass

    @abc.abstractmethod
    def on_cancel_order(self, event: Events.CancelOrder) -> None:
        pass

    @abc.abstractmethod
    def on_modify_order(self, event: Events.ModifyOrder) -> None:
        pass


class SimulatedBroker(BaseBroker):
    """
    Simulated broker for backtesting.
    """

    def __init__(self) -> None:
        super().__init__()
        event_bus.subscribe(self, Events.IncomingBar)

        self._pending_market_orders: dict[str, dict[uuid.UUID, Events.SubmitOrder]] = {}
        self._pending_limit_orders: dict[str, dict[uuid.UUID, Events.SubmitOrder]] = {}
        self._pending_stop_orders: dict[str, dict[uuid.UUID, Events.SubmitOrder]] = {}
        self._pending_stop_limit_orders: dict[
            str, dict[uuid.UUID, Events.SubmitOrder]
        ] = {}

    def on_event(self, event) -> None:
        match event:
            case Events.SubmitOrder():
                self.on_submit_order(event)
            case Events.CancelOrder():
                self.on_cancel_order(event)
            case Events.ModifyOrder():
                self.on_modify_order(event)
            case Events.IncomingBar():
                self.on_incoming_bar(event)

    def on_submit_order(self, event: Events.SubmitOrder) -> None:
        pass

    def on_cancel_order(self, event: Events.CancelOrder) -> None:
        pass

    def on_modify_order(self, event: Events.ModifyOrder) -> None:
        pass

    def on_incoming_bar(self, event: Events.IncomingBar) -> None:
        self._process_pending_orders(event)

        bar_ready = Events.BarReady(
            ts_event=event.ts_event,
            symbol=event.symbol,
            record_type=event.record_type,
            open=event.open,
            high=event.high,
            low=event.low,
            close=event.close,
            volume=event.volume,
        )
        event_bus.publish(bar_ready)

    def _process_pending_orders(self, event: Events.IncomingBar) -> None:
        pass
