"""
Provides the infrastructure for event-based communication between system components.
"""

from .eventbus import EventBus
from .subscriber import Subscriber

__all__ = [
    "EventBus",
    "Subscriber",
]
