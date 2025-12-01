"""
Core module containing the backbone of OneSecondTrader's event-driven architecture.
"""

import abc
import dataclasses
import enum
import pandas as pd
import queue
import threading

from collections import defaultdict


class Models:
    """
    Namespace for all models.
    """

    class RecordType(enum.Enum):
        OHLCV_1S = 32
        OHLCV_1M = 33
        OHLCV_1H = 34
        OHLCV_1D = 35


class Events:
    """
    Namespace for all events.
    """

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class BaseEvent:
        ts_event: pd.Timestamp = dataclasses.field(
            default_factory=lambda: pd.Timestamp.now(tz="UTC")
        )

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class SystemShutdown(BaseEvent):
        pass

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class IncomingBar(BaseEvent):
        ts_event: pd.Timestamp
        symbol: str
        record_type: Models.RecordType
        open: float
        high: float
        low: float
        close: float
        volume: int | None = None


class BaseConsumer(abc.ABC):
    """
    Base class for all consumers.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[Events.BaseEvent] = queue.Queue()
        self._thread = threading.Thread(target=self._consume, daemon=True)
        self._thread.start()

    @abc.abstractmethod
    def on_event(self, event: Events.BaseEvent) -> None:
        pass

    def receive(self, event: Events.BaseEvent) -> None:
        self._queue.put(event)

    def _consume(self) -> None:
        while True:
            event = self._queue.get()
            if isinstance(event, Events.SystemShutdown):
                break
            self.on_event(event)


class EventBus:
    """
    Event bus for publishing events to the consumers subscribed to them.
    """

    def __init__(self) -> None:
        self._subscriptions: defaultdict[type[Events.BaseEvent], list[BaseConsumer]] = (
            defaultdict(list)
        )
        self._lock: threading.Lock = threading.Lock()

    def subscribe(self, subscriber: BaseConsumer, event_type: type[Events.BaseEvent]):
        with self._lock:
            if subscriber not in self._subscriptions[event_type]:
                self._subscriptions[event_type].append(subscriber)

    def unsubscribe(self, subscriber: BaseConsumer):
        with self._lock:
            for consumer_list in self._subscriptions.values():
                if subscriber in consumer_list:
                    consumer_list.remove(subscriber)

    def publish(self, event: Events.BaseEvent) -> None:
        with self._lock:
            consumers = list(self._subscriptions[type(event)])
        for consumer in consumers:
            consumer.receive(event)
