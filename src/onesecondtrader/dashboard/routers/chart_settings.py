"""
API endpoints for chart settings management.

Provides endpoints for loading and saving per-strategy chart settings.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import get_strategy_key
from ..chart_settings import (
    load_chart_settings,
    save_chart_settings,
    load_indicator_defaults,
    save_indicator_default,
    save_global_defaults,
)

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


# ── Per-indicator global defaults ──


@router.get("/indicator-defaults")
async def api_get_indicator_defaults() -> dict:
    """Return all saved indicator visual defaults."""
    return load_indicator_defaults()


class IndicatorDefaultRequest(BaseModel):
    """Request model for saving a single indicator's visual defaults."""

    panel: int | None = None
    below_price: bool | None = None
    style: str | None = None
    color: str | None = None
    width: str | None = None
    visible: bool | None = None


@router.put("/indicator-defaults/{name}")
async def api_put_indicator_default(
    name: str, request: IndicatorDefaultRequest
) -> dict:
    """Save visual defaults for a single indicator by name."""
    settings = {k: v for k, v in request.model_dump().items() if v is not None}
    save_indicator_default(name, settings)
    return {"status": "ok"}


class GlobalDefaultsRequest(BaseModel):
    """Request model for saving global chart defaults."""

    chart_type: str | None = None
    overlap: int | None = None


@router.put("/indicator-defaults")
async def api_put_global_defaults(request: GlobalDefaultsRequest) -> dict:
    """Save global chart defaults (chart_type, overlap)."""
    save_global_defaults(chart_type=request.chart_type, overlap=request.overlap)
    return {"status": "ok"}
