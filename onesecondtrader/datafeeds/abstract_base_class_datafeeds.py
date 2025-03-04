import abc
import threading
from onesecondtrader.ontology.event_messages import (
    IncomingBarEventMessage,
)
import queue
from onesecondtrader.ontology.global_queues import incoming_bar_event_message_queue


class ABCDatafeed(abc.ABC):

    def __init__(self, producer_target_queue: queue.Queue | None = None):
        self._instance_stop_event = threading.Event()
        self.producer_target_queue = (
            producer_target_queue or incoming_bar_event_message_queue
        )

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
