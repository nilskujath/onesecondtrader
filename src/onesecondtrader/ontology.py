"""
Domain-specific data models that are used system-wide.
"""

import dataclasses


@dataclasses.dataclass(slots=True)
class Bar:
    """
    Data model for OHLCV bar data.
    """

    open: float
    high: float
    low: float
    close: float
    volume: int
