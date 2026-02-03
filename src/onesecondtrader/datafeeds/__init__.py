"""
Provides data feed components for ingesting market data into the system.
"""

from .base import DatafeedBase
from .simulated import SimulatedDatafeed

__all__ = [
    "DatafeedBase",
    "SimulatedDatafeed",
]
