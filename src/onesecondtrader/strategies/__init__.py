"""
Provides a base class for creating custom trading strategies and provides example strategies.
"""

from .base import StrategyBase
from .examples import SMACrossover

__all__ = [
    "StrategyBase",
    "SMACrossover",
]
