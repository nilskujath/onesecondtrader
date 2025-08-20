"""
The Trading Infrastructure Toolkit for Python.

Research, simulate, and deploy algorithmic trading strategies — all in one place.
"""

# Core infrastructure
from .monitoring import logger

# Domain models
from .domain.models import DomainModel, MarketData, PositionManagement, SystemManagement

__all__ = [
    # Core infrastructure
    "logger",
    # Domain models
    "DomainModel",
    "MarketData",
    "PositionManagement",
    "SystemManagement",
]
