"""
The Trading Infrastructure Toolkit for Python.

Research, simulate, and deploy algorithmic trading strategies — all in one place.
"""

# Core infrastructure
from .log_config import logger

# Domain models
from .domain_models import MarketData, PositionManagement

__all__ = [
    # Core infrastructure
    "logger",
    # Domain models
    "MarketData",
    "PositionManagement",
]
