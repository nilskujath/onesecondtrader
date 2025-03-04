import abc
from onesecondtrader.ontology.event_messages import IncomingBarEventMessage


class Indicator(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def update(self, bar: IncomingBarEventMessage):
        pass

    @abc.abstractmethod
    def value(self):
        pass
