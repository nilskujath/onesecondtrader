"""
FastAPI routers for the dashboard API.

Exports all API routers for inclusion in the main FastAPI application.
"""

from .runs import router as runs_router
from .strategies import router as strategies_router
from .secmaster import router as secmaster_router
from .presets import router as presets_router
from .backtest import router as backtest_router
from .indicators import router as indicators_router
from .explore import router as explore_router
from .explore import explore_presets_router, condition_presets_router
from .explorer import router as explorer_router
from .charts import router as charts_router
from .segments import router as segments_router
from .bars import router as bars_router
from .chart_settings import router as chart_settings_router
from .splits import router as splits_router

__all__ = [
    "runs_router",
    "strategies_router",
    "secmaster_router",
    "presets_router",
    "backtest_router",
    "indicators_router",
    "explore_router",
    "explore_presets_router",
    "condition_presets_router",
    "explorer_router",
    "charts_router",
    "segments_router",
    "bars_router",
    "chart_settings_router",
    "splits_router",
]
