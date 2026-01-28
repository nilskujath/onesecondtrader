from __future__ import annotations

import abc

from onesecondtrader.core import events, messaging, models


class DatafeedBase(abc.ABC):
    def __init__(self, event_bus: messaging.EventBus) -> None:
        self._event_bus = event_bus

    def _publish(self, event: events.EventBase) -> None:
        self._event_bus.publish(event)

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        pass

    @abc.abstractmethod
    def subscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        pass

    @abc.abstractmethod
    def unsubscribe(self, symbol: str, bar_period: models.BarPeriod) -> None:
        pass

    def wait_until_complete(self) -> None:
        pass
