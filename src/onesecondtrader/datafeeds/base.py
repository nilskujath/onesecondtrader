from __future__ import annotations

import abc

from onesecondtrader import events, messaging, models


class DatafeedBase(abc.ABC):
    """
    Abstract base class for market data feed implementations.

    A data feed is responsible for connecting to an external data source, managing symbol and bar-period subscriptions, and publishing market data events onto the system event bus.

    Concrete subclasses implement the mechanics of connectivity, subscription handling, and lifecycle management for a specific data source.
    """

    def __init__(self, event_bus: messaging.EventBus) -> None:
        """
        Initialize the data feed with an event bus.

        parameters:
            event_bus:
                Event bus used to publish market data events produced by this data feed.
        """
        self._event_bus = event_bus

    def _publish(self, event: events.EventBase) -> None:
        """
        Publish a market data event to the event bus.

        This method is intended for use by subclasses to forward incoming data from the external source into the internal event-driven system.

        parameters:
            event:
                Event instance to be published.
        """
        self._event_bus.publish(event)

    @abc.abstractmethod
    def connect(self) -> None:
        """
        Establish a connection to the underlying data source.

        Implementations should perform any required setup, authentication, or resource allocation needed before subscriptions can be registered.
        """
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """
        Terminate the connection to the underlying data source.

        Implementations should release resources and ensure that no further events are published after disconnection.
        """
        pass

    @abc.abstractmethod
    def subscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        """
        Subscribe to market data for one or more symbols at a given bar period.

        parameters:
            symbols:
                Instrument symbols to subscribe to, interpreted according to the conventions of the underlying data source.
            bar_period:
                Bar aggregation period specifying the granularity of market data.
        """
        pass

    @abc.abstractmethod
    def unsubscribe(self, symbols: list[str], bar_period: models.BarPeriod) -> None:
        """
        Cancel existing subscriptions for one or more symbols at a given bar period.

        parameters:
            symbols:
                Instrument symbols for which subscriptions should be removed.
            bar_period:
                Bar aggregation period associated with the subscriptions.
        """
        pass

    def wait_until_complete(self) -> None:
        """
        Block until the data feed has completed all pending work.

        This method may be overridden by subclasses that perform asynchronous ingestion or background processing.
        The default implementation does nothing.
        """
        pass
