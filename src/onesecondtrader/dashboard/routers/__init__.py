"""
FastAPI routers for the dashboard API.

Exports all API routers for inclusion in the main FastAPI application.
"""

from .runs import router as runs_router
from .strategies import router as strategies_router
from .secmaster import router as secmaster_router
from .presets import router as presets_router
from .backtest import router as backtest_router

__all__ = [
    "runs_router",
    "strategies_router",
    "secmaster_router",
    "presets_router",
    "backtest_router",
]
