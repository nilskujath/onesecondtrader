import abc

from onesecondtrader.core import events, messaging, models


class Datafeed(abc.ABC):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self._event_bus = event_bus

    def _publish(self, event: events.EventBase) -> None:
        self._event_bus.publish(event)

    @abc.abstractmethod
    def stream(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        pass

    @abc.abstractmethod
    def shutdown(self) -> None:
        pass
