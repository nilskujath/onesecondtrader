"""
Provides a library of common technical indicators and a base class for creating custom ones.
"""

from .base import IndicatorBase, discover_indicators, get_registered_indicators
from .moving_averages import SimpleMovingAverage
from .market_fields import Open, High, Low, Close, Volume
from .bollinger import BollingerLower, BollingerUpper, BollingerBandwidth

__all__ = [
    "IndicatorBase",
    "discover_indicators",
    "get_registered_indicators",
    "SimpleMovingAverage",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "BollingerLower",
    "BollingerUpper",
    "BollingerBandwidth",
]
