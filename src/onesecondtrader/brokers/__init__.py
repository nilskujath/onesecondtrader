"""
Provides interfaces for order execution via a simulated broker and adapters to real venues.
"""

from onesecondtrader.brokers.base import BrokerBase
from onesecondtrader.brokers.simulated import SimulatedBroker

__all__ = [
    "BrokerBase",
    "SimulatedBroker",
]
