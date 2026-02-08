"""
API endpoints for chart settings management.

Provides endpoints for loading and saving per-strategy chart settings.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import get_strategy_key
from ..chart_settings import load_chart_settings, save_chart_settings

router = APIRouter(prefix="/api", tags=["chart-settings"])


@router.get("/runs/{run_id}/chart-settings")
async def api_get_chart_settings(run_id: str) -> dict:
    """Return saved chart settings for a run (keyed by strategy class)."""
    strategy_key = get_strategy_key(run_id)
    return load_chart_settings(strategy_key)


class ChartSettingsRequest(BaseModel):
    """Request model for saving chart settings."""

    indicators: dict | None = None
    fill_between: list | None = None
    chart_type: str | None = None
    overlap: int | None = None


@router.put("/runs/{run_id}/chart-settings")
async def api_put_chart_settings(run_id: str, request: ChartSettingsRequest) -> dict:
    """Save chart settings for a run (keyed by strategy class)."""
    strategy_key = get_strategy_key(run_id)
    settings: dict = {}
    if request.indicators is not None:
        settings["indicators"] = request.indicators
    if request.fill_between is not None:
        settings["fill_between"] = request.fill_between
    if request.chart_type is not None:
        settings["chart_type"] = request.chart_type
    if request.overlap is not None:
        settings["overlap"] = request.overlap
    save_chart_settings(strategy_key, settings)
    return {"status": "ok"}
