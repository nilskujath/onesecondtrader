"""
Core module containing the backbone of OneSecondTrader's event-driven architecture.
"""

import abc
import dataclasses
import enum
import logging
import pandas as pd
import queue
import threading
import uuid

from collections import defaultdict


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
)
logger = logging.getLogger("onesecondtrader")


class Models:
    """
    Namespace for all models.
    """

    class RecordType(enum.Enum):
        OHLCV_1S = 32
        OHLCV_1M = 33
        OHLCV_1H = 34
        OHLCV_1D = 35

    class OrderSide(enum.Enum):
        BUY = enum.auto()
        SELL = enum.auto()

    class OrderType(enum.Enum):
        MARKET = enum.auto()
        LIMIT = enum.auto()
        STOP = enum.auto()
        STOP_LIMIT = enum.auto()

    class RejectionReason(enum.Enum):
        ORDER_ALREADY_FILLED = enum.auto()
        ORDER_ALREADY_CANCELLED = enum.auto()
        ORDER_PENDING_EXECUTION = enum.auto()
        INSUFFICIENT_FUNDS = enum.auto()
        MARKET_CLOSED = enum.auto()
        UNKNOWN = enum.auto()

    class TimeInForce(enum.Enum):
        GTC = enum.auto()
        DAY = enum.auto()
        IOC = enum.auto()
        FOK = enum.auto()


class Events:
    """
    Namespace for all events.
    """

    # BASE EVENT
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class BaseEvent:
        ts_event: pd.Timestamp = dataclasses.field(
            default_factory=lambda: pd.Timestamp.now(tz="UTC")
        )

    # SYSTEM EVENTS
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class SystemEvent(BaseEvent):
        pass

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class SystemShutdown(SystemEvent):
        pass

    # MARKET EVENTS
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class MarketEvent(BaseEvent):
        pass

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class IncomingBar(MarketEvent):
        ts_event: pd.Timestamp
        symbol: str
        record_type: Models.RecordType
        open: float
        high: float
        low: float
        close: float
        volume: int | None = None

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class BarReady(MarketEvent):
        ts_event: pd.Timestamp
        symbol: str
        record_type: Models.RecordType
        open: float
        high: float
        low: float
        close: float
        volume: int | None = None

    # BROKER REQUESTS EVENTS
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class BrokerRequestEvent(BaseEvent):
        pass

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class SubmitOrder(BrokerRequestEvent):
        order_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
        symbol: str
        order_type: Models.OrderType
        side: Models.OrderSide
        quantity: float
        limit_price: float | None = None
        stop_price: float | None = None
        time_in_force: Models.TimeInForce = Models.TimeInForce.GTC

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class ModifyOrder(BrokerRequestEvent):
        symbol: str
        order_id: uuid.UUID
        quantity: float | None = None
        limit_price: float | None = None
        stop_price: float | None = None

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class CancelOrder(BrokerRequestEvent):
        symbol: str
        order_id: uuid.UUID

    # BROKER RESPONSE EVENTS
    @dataclasses.dataclass(kw_only=True, frozen=True)
    class BrokerResponseEvent(BaseEvent):
        ts_broker: pd.Timestamp

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderSubmitted(BrokerResponseEvent):
        order_id: uuid.UUID
        broker_order_id: str | None = None

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderModified(BrokerResponseEvent):
        order_id: uuid.UUID
        broker_order_id: str | None = None

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class Fill(BrokerResponseEvent):
        fill_id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
        broker_fill_id: str | None = None
        associated_order_id: uuid.UUID
        symbol: str
        side: Models.OrderSide
        quantity_filled: float
        fill_price: float
        commission: float
        exchange: str = "SIMULATED"

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderRejected(BrokerResponseEvent):
        order_id: uuid.UUID
        reason: Models.RejectionReason

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderCancelled(BrokerResponseEvent):
        order_id: uuid.UUID

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class OrderExpired(BrokerResponseEvent):
        order_id: uuid.UUID

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class CancelRejected(BrokerResponseEvent):
        order_id: uuid.UUID
        reason: Models.RejectionReason

    @dataclasses.dataclass(kw_only=True, frozen=True)
    class ModifyRejected(BrokerResponseEvent):
        order_id: uuid.UUID
        reason: Models.RejectionReason


class BaseConsumer(abc.ABC):
    """
    Base class for all consumers.
    """

    def __init__(self) -> None:
        self.queue: queue.Queue[Events.BaseEvent] = queue.Queue()
        self._thread = threading.Thread(
            target=self._consume, name=self.__class__.__name__, daemon=True
        )
        self._thread.start()

    @abc.abstractmethod
    def on_event(self, event: Events.BaseEvent) -> None:
        pass

    def receive(self, event: Events.BaseEvent) -> None:
        self.queue.put(event)

    def _consume(self) -> None:
        while True:
            event = self.queue.get()
            if isinstance(event, Events.SystemShutdown):
                self.queue.task_done()
                break
            self.on_event(event)
            self.queue.task_done()


class EventBus:
    """
    Event bus for publishing events to the consumers subscribed to them.
    """

    def __init__(self) -> None:
        self._subscriptions: defaultdict[type[Events.BaseEvent], list[BaseConsumer]] = (
            defaultdict(list)
        )
        self._consumers: set[BaseConsumer] = set()
        self._lock: threading.Lock = threading.Lock()

    def subscribe(self, subscriber: BaseConsumer, event_type: type[Events.BaseEvent]):
        with self._lock:
            self._consumers.add(subscriber)
            if subscriber not in self._subscriptions[event_type]:
                self._subscriptions[event_type].append(subscriber)

    def unsubscribe(self, subscriber: BaseConsumer):
        with self._lock:
            for consumer_list in self._subscriptions.values():
                if subscriber in consumer_list:
                    consumer_list.remove(subscriber)
            if not any(subscriber in cl for cl in self._subscriptions.values()):
                self._consumers.discard(subscriber)

    def publish(self, event: Events.BaseEvent) -> None:
        with self._lock:
            consumers = list(self._subscriptions[type(event)])
        for consumer in consumers:
            consumer.receive(event)

    # Enable synchronous execution via wait_until_idle()
    def wait_until_idle(self) -> None:
        with self._lock:
            consumers = list(self._consumers)
        for consumer in consumers:
            consumer.queue.join()


event_bus = EventBus()
"""
Global instance of `EventBus`.
"""
