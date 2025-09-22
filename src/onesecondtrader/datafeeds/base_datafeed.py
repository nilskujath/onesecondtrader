"""
This module provides the base class for all datafeeds.
"""

import abc
from onesecondtrader import messaging
from onesecondtrader.core import models


class BaseDatafeed(abc.ABC):
    """
    Base class for all datafeeds.
    """

    def __init__(self, event_bus: messaging.EventBus | None = None):
        self.event_bus: messaging.EventBus = (
            event_bus if event_bus else messaging.system_event_bus
        )

    @abc.abstractmethod
    def connect(self):
        """
        Connect to the datafeed.
        """
        pass

    @abc.abstractmethod
    def watch(self, symbols: list[tuple[str, models.RecordType]]):
        """
        Start watching symbols.

        Args:
            symbols (list[tuple[str, models.TimeFrame]]): List of symbols to watch with
                their respective timeframes.
        """
        pass

    @abc.abstractmethod
    def unwatch(self, symbols: list[tuple[str, models.RecordType]]):
        """
        Stop watching symbols.

        Args:
            symbols (list[tuple[str, models.TimeFrame]]): List of symbols to stop
                watching with their respective timeframes.
        """
        pass

    @abc.abstractmethod
    def disconnect(self):
        """
        Disconnect from the datafeed.
        """
        pass
