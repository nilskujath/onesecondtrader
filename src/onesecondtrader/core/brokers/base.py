import abc

from onesecondtrader.core import events, messaging


class BrokerBase(messaging.Subscriber):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        super().__init__(event_bus)
        self._subscribe(
            events.requests.OrderSubmission,
            events.requests.OrderCancellation,
            events.requests.OrderModification,
        )

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        self.shutdown()

    def _on_event(self, event: events.bases.EventBase) -> None:
        match event:
            case events.requests.OrderSubmission() as submit_order:
                self._on_submit_order(submit_order)
            case events.requests.OrderCancellation() as cancel_order:
                self._on_cancel_order(cancel_order)
            case events.requests.OrderModification() as modify_order:
                self._on_modify_order(modify_order)
            case _:
                return

    @abc.abstractmethod
    def _on_submit_order(self, event: events.requests.OrderSubmission) -> None:
        pass

    @abc.abstractmethod
    def _on_cancel_order(self, event: events.requests.OrderCancellation) -> None:
        pass

    @abc.abstractmethod
    def _on_modify_order(self, event: events.requests.OrderModification) -> None:
        pass

    def _respond(self, response_event: events.bases.BrokerResponseEvent) -> None:
        self._publish(response_event)
