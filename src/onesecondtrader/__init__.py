"""
The Trading Infrastructure Toolkit for Python.

Research, simulate, and deploy algorithmic trading strategies — all in one place.
"""

# Core infrastructure
from .monitoring import logger

# Domain models
from .domain import MarketData, PositionManagement, SystemManagement

__all__ = [
    # Core infrastructure
    "logger",
    # Domain models
    "MarketData",
    "PositionManagement",
    "SystemManagement",
]
