"""
API endpoints for chart image generation.

Provides endpoints for generating PNG chart images for round-trip trades,
trade journeys, PnL summaries, and bar segments.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ..db import get_strategy_key
from ..chart_settings import load_chart_settings
from ..charting import (
    generate_chart_image,
    generate_segment_chart_image,
    generate_trade_journey_chart,
    generate_pnl_summary_chart,
)
from ..explorer import get_session_run_ids
from ..roundtrips import get_roundtrips

router = APIRouter(prefix="/api", tags=["charts"])


@router.get("/runs/{run_id}/chart.png")
async def api_run_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    direction: str,
    pnl: float,
    chart_type: str = "c_bars",
    context: int = 100,
) -> Response:
    """Return a PNG chart image for a round-trip trade."""
    strategy_key = get_strategy_key(run_id)
    chart_settings = load_chart_settings(strategy_key) or None
    image_bytes = generate_chart_image(
        run_id,
        symbol,
        start_ns,
        end_ns,
        direction,
        pnl,
        chart_type,
        chart_settings=chart_settings,
        context=context,
    )
    return Response(content=image_bytes, media_type="image/png")


@router.get("/runs/{run_id}/trade-journey.png")
async def api_trade_journey_chart(run_id: str, symbol: str | None = None) -> Response:
    """Return a Trade Journey chart image for round-trip trades in a run, optionally filtered by symbol."""
    roundtrips = get_roundtrips(run_id)
    if symbol:
        roundtrips = [rt for rt in roundtrips if rt["symbol"] == symbol]
    image_bytes = generate_trade_journey_chart(run_id, roundtrips)
    return Response(content=image_bytes, media_type="image/png")


@router.get("/runs/{run_id}/pnl-summary.png")
async def api_pnl_summary_chart(run_id: str, symbol: str | None = None) -> Response:
    """Return a PnL Summary chart image for round-trip trades in a run, optionally filtered by symbol."""
    roundtrips = get_roundtrips(run_id)
    if symbol:
        roundtrips = [rt for rt in roundtrips if rt["symbol"] == symbol]
    image_bytes = generate_pnl_summary_chart(roundtrips)
    return Response(content=image_bytes, media_type="image/png")


@router.get("/runs/{run_id}/segment-chart.png")
def api_segment_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    period_start_ns: int | None = None,
    period_end_ns: int | None = None,
    chart_type: str = "c_bars",
    highlight_start_ns: int | None = None,
    highlight_end_ns: int | None = None,
) -> Response:
    """Return a PNG chart image for a bar segment."""
    strategy_key = get_strategy_key(run_id)
    chart_settings = load_chart_settings(strategy_key) or None
    image_bytes = generate_segment_chart_image(
        run_id,
        symbol,
        start_ns,
        end_ns,
        period_start_ns,
        period_end_ns,
        chart_type,
        chart_settings=chart_settings,
        highlight_start_ns=highlight_start_ns,
        highlight_end_ns=highlight_end_ns,
    )
    return Response(content=image_bytes, media_type="image/png")


@router.get("/sessions/{session_id}/segment-chart.png")
def api_session_segment_chart_image(
    session_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    period_start_ns: int | None = None,
    period_end_ns: int | None = None,
    chart_type: str = "c_bars",
    highlight_start_ns: int | None = None,
    highlight_end_ns: int | None = None,
    run_ids: str | None = None,
) -> Response:
    """Return a PNG segment chart merging indicators from all session runs."""
    if run_ids is not None:
        run_id_list = [r for r in run_ids.split(",") if r]
    else:
        run_id_list = []
    if not run_id_list:
        run_id_list = get_session_run_ids(session_id)
    if not run_id_list:
        return Response(content=b"", media_type="image/png")
    primary_run_id = run_id_list[0]
    extra_run_ids = run_id_list[1:] if len(run_id_list) > 1 else None
    strategy_key = f"session:{session_id}"
    chart_settings = load_chart_settings(strategy_key) or None
    image_bytes = generate_segment_chart_image(
        primary_run_id,
        symbol,
        start_ns,
        end_ns,
        period_start_ns,
        period_end_ns,
        chart_type,
        chart_settings=chart_settings,
        highlight_start_ns=highlight_start_ns,
        highlight_end_ns=highlight_end_ns,
        extra_run_ids=extra_run_ids,
    )
    return Response(content=image_bytes, media_type="image/png")
