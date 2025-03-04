import abc
import threading
from onesecondtrader.ontology.event_messages import (
    IncomingBarEventMessage,
)


class ABCDatafeed(abc.ABC):

    def __init__(self):
        self._instance_stop_event = threading.Event()

    @abc.abstractmethod
    def _get_next_bar_event_message(self) -> IncomingBarEventMessage:
        pass

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def _enqueue_incoming_bar_event_messages(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass
