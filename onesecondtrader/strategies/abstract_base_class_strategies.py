import abc
import threading
import queue
from onesecondtrader.ontology.global_queues import (
    global_incoming_bar_event_message_queue,
    global_processed_bar_event_message_queue,
)


class ABCStrategy(abc.ABC):

    def __init__(
        self,
        symbols: list | None = None,
        incoming_data_queue: queue.Queue | None = None,
        processed_data_queue: queue.Queue | None = None,
    ):
        self._instance_stop_event = threading.Event()
        self._symbols = symbols
        self._incoming_data_queue = (
            incoming_data_queue or global_incoming_bar_event_message_queue
        )
        self._processed_data_queue = (
            processed_data_queue or global_processed_bar_event_message_queue
        )
        self._no_filter_mode = self._symbols is None
