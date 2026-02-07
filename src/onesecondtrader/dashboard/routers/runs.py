"""
API endpoints for run management.

Provides endpoints for listing, deleting, and querying runs and their round-trips.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..backtest import (
    cancel_backtest,
    running_jobs,
    _orchestrator_refs,
    _jobs_lock,
)
from ..db import get_runs_db_path, get_runs, CHILD_TABLES
from ..roundtrips import get_roundtrips
from ..chart_settings import load_chart_settings, save_chart_settings
from ..charting import (
    generate_chart_image,
    generate_segment_chart_image,
    generate_trade_journey_chart,
    generate_pnl_summary_chart,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs")
async def api_runs() -> dict:
    """Return list of recent runs from the database."""
    runs = get_runs()
    return {"runs": runs}


class DeleteRunsRequest(BaseModel):
    """
    Request model for deleting runs.

    Attributes:
        run_ids:
            List of run IDs to delete.
    """

    run_ids: list[str]


@router.delete("/runs")
async def api_delete_runs(request: DeleteRunsRequest) -> dict:
    """Delete specified runs and their associated data.

    Cancels any running/queued backtests for the requested run IDs first,
    then deletes the data with a generous busy-timeout.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"deleted": 0}
    if not request.run_ids:
        return {"deleted": 0}

    # Cancel running/queued backtests that match the requested run IDs.
    # The job dict is keyed by the UUID run_id, but the DB run_id is on
    # the orchestrator (orch.run_id).  We need to check both.
    # Collect IDs to cancel first, then cancel outside the lock to avoid
    # deadlock (cancel_backtest acquires _jobs_lock internally).
    request_id_set = set(request.run_ids)
    to_cancel: list[str] = []
    with _jobs_lock:
        for job_id, status in list(running_jobs.items()):
            if status not in ("running", "queued"):
                continue
            if job_id in request_id_set:
                to_cancel.append(job_id)
                continue
            orch = _orchestrator_refs.get(job_id)
            if orch is not None and getattr(orch, "run_id", None) in request_id_set:
                to_cancel.append(job_id)

    cancelled = False
    for job_id in to_cancel:
        cancelled = cancel_backtest(job_id) or cancelled

    if cancelled:
        await asyncio.sleep(1)

    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in request.run_ids)
        for table in CHILD_TABLES:
            cursor.execute(
                f"DELETE FROM {table} WHERE run_id IN ({placeholders})",
                request.run_ids,
            )
        cursor.execute(
            f"DELETE FROM runs WHERE run_id IN ({placeholders})",
            request.run_ids,
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return {"deleted": deleted}
    except sqlite3.OperationalError as exc:
        logger.warning("delete runs failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Database is busy, please try again shortly: {exc}",
        )
    except Exception as exc:
        logger.exception("unexpected error deleting runs")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete runs: {exc}",
        )


@router.get("/runs/{run_id}/roundtrips")
async def api_run_roundtrips(run_id: str) -> dict:
    """Return computed round-trip trades for a run."""
    roundtrips = get_roundtrips(run_id)
    return {"roundtrips": roundtrips}


@router.get("/runs/{run_id}/chart.png")
async def api_run_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    direction: str,
    pnl: float,
    chart_type: str = "c_bars",
) -> Response:
    """Return a PNG chart image for a round-trip trade."""
    chart_settings = load_chart_settings(run_id) or None
    image_bytes = generate_chart_image(
        run_id,
        symbol,
        start_ns,
        end_ns,
        direction,
        pnl,
        chart_type,
        chart_settings=chart_settings,
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


TIME_PERIOD_NS = {
    "year": 365 * 24 * 60 * 60 * 1_000_000_000,
    "quarter": 91 * 24 * 60 * 60 * 1_000_000_000,
    "month": 30 * 24 * 60 * 60 * 1_000_000_000,
    "week": 7 * 24 * 60 * 60 * 1_000_000_000,
    "day": 24 * 60 * 60 * 1_000_000_000,
    "4hour": 4 * 60 * 60 * 1_000_000_000,
    "hour": 60 * 60 * 1_000_000_000,
    "15min": 15 * 60 * 1_000_000_000,
    "5min": 5 * 60 * 1_000_000_000,
    "1min": 60 * 1_000_000_000,
}


def _split_by_bars(
    cursor, run_id: str, symbol: str, segment_size: int, overlap: int
) -> list[dict]:
    cursor.execute(
        """
        SELECT ts_event_ns
        FROM bars_processed
        WHERE run_id = ? AND symbol = ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol),
    )
    all_ts = [row[0] for row in cursor.fetchall()]
    if not all_ts:
        return []
    segments = []
    step = max(1, segment_size - overlap)
    segment_num = 1
    start_idx = 0
    while start_idx < len(all_ts):
        end_idx = min(start_idx + segment_size, len(all_ts))
        segments.append(
            {
                "symbol": symbol,
                "segment_num": segment_num,
                "start_ts": str(all_ts[start_idx]),
                "end_ts": str(all_ts[end_idx - 1]),
                "bar_count": end_idx - start_idx,
            }
        )
        segment_num += 1
        start_idx += step
        if end_idx >= len(all_ts):
            break
    return segments


def _get_period_boundary(ts_ns: int, time_period: str) -> int:
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)
    if time_period == "year":
        boundary = datetime(dt.year, 1, 1, tzinfo=timezone.utc)
    elif time_period == "quarter":
        quarter_month = ((dt.month - 1) // 3) * 3 + 1
        boundary = datetime(dt.year, quarter_month, 1, tzinfo=timezone.utc)
    elif time_period == "month":
        boundary = datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)
    elif time_period == "week":
        days_since_monday = dt.weekday()
        boundary = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
        boundary = boundary.replace(hour=0, minute=0, second=0, microsecond=0)
        boundary = datetime.fromtimestamp(
            boundary.timestamp() - days_since_monday * 86400, tz=timezone.utc
        )
    elif time_period == "day":
        boundary = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    elif time_period == "4hour":
        hour_block = (dt.hour // 4) * 4
        boundary = datetime(dt.year, dt.month, dt.day, hour_block, tzinfo=timezone.utc)
    elif time_period == "hour":
        boundary = datetime(dt.year, dt.month, dt.day, dt.hour, tzinfo=timezone.utc)
    elif time_period == "15min":
        min_block = (dt.minute // 15) * 15
        boundary = datetime(
            dt.year, dt.month, dt.day, dt.hour, min_block, tzinfo=timezone.utc
        )
    elif time_period == "5min":
        min_block = (dt.minute // 5) * 5
        boundary = datetime(
            dt.year, dt.month, dt.day, dt.hour, min_block, tzinfo=timezone.utc
        )
    elif time_period == "1min":
        boundary = datetime(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, tzinfo=timezone.utc
        )
    else:
        boundary = datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    return int(boundary.timestamp() * 1_000_000_000)


def _split_by_time(
    cursor, run_id: str, symbol: str, time_period: str, overlap: int
) -> list[dict]:
    period_ns = TIME_PERIOD_NS.get(time_period, TIME_PERIOD_NS["day"])
    cursor.execute(
        """
        SELECT ts_event_ns
        FROM bars_processed
        WHERE run_id = ? AND symbol = ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol),
    )
    all_ts = [row[0] for row in cursor.fetchall()]
    if not all_ts:
        return []
    segments = []
    segment_num = 1
    idx = 0
    while idx < len(all_ts):
        period_start = _get_period_boundary(all_ts[idx], time_period)
        period_end = period_start + period_ns - 1
        start_idx = idx
        end_idx = idx
        while end_idx + 1 < len(all_ts) and all_ts[end_idx + 1] <= period_end:
            end_idx += 1
        actual_start_idx = max(0, start_idx - overlap) if overlap > 0 else start_idx
        segments.append(
            {
                "symbol": symbol,
                "segment_num": segment_num,
                "start_ts": str(all_ts[actual_start_idx]),
                "end_ts": str(all_ts[end_idx]),
                "bar_count": end_idx - actual_start_idx + 1,
                "period_start_ns": str(period_start),
                "period_end_ns": str(period_end + 1),
            }
        )
        segment_num += 1
        idx = end_idx + 1
    return segments


@router.get("/runs/{run_id}/chart-segments")
async def api_chart_segments(
    run_id: str,
    mode: str = "bars",
    bars_per_chart: int = 500,
    overlap: int = 100,
    time_period: str = "day",
) -> dict:
    """Return chart segment metadata for a run."""
    from ..db import get_runs_db_path

    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"segments": [], "bar_period": None}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT bar_period FROM bars_processed WHERE run_id = ? LIMIT 1
        """,
        (run_id,),
    )
    bar_period_row = cursor.fetchone()
    bar_period = bar_period_row[0] if bar_period_row else None
    cursor.execute(
        """
        SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol
        """,
        (run_id,),
    )
    symbols = [row[0] for row in cursor.fetchall()]
    segments = []
    for symbol in symbols:
        if mode == "time":
            segments.extend(
                _split_by_time(cursor, run_id, symbol, time_period, overlap)
            )
        else:
            segments.extend(
                _split_by_bars(cursor, run_id, symbol, bars_per_chart, overlap)
            )
    conn.close()
    return {"segments": segments, "bar_period": bar_period}


@router.get("/runs/{run_id}/segment-chart.png")
async def api_segment_chart_image(
    run_id: str,
    symbol: str,
    start_ns: int,
    end_ns: int,
    period_start_ns: int | None = None,
    period_end_ns: int | None = None,
    chart_type: str = "c_bars",
) -> Response:
    """Return a PNG chart image for a bar segment."""
    chart_settings = load_chart_settings(run_id) or None
    image_bytes = generate_segment_chart_image(
        run_id,
        symbol,
        start_ns,
        end_ns,
        period_start_ns,
        period_end_ns,
        chart_type,
        chart_settings=chart_settings,
    )
    return Response(content=image_bytes, media_type="image/png")


@router.get("/runs/{run_id}/symbols")
async def api_run_symbols(run_id: str) -> dict:
    """Return list of symbols available in a run."""
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"symbols": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol
        """,
        (run_id,),
    )
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"symbols": symbols}


@router.get("/runs/{run_id}/indicators")
async def api_run_indicators(run_id: str) -> dict:
    """Return list of indicator names present in a run."""
    import json as json_module

    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"indicators": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT indicators FROM bars_processed
        WHERE run_id = ?
        LIMIT 10
        """,
        (run_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    names: set[str] = set()
    for (indicators_json,) in rows:
        if indicators_json:
            indicators = json_module.loads(indicators_json)
            names.update(indicators.keys())
    return {"indicators": sorted(names)}


@router.get("/runs/{run_id}/chart-settings")
async def api_get_chart_settings(run_id: str) -> dict:
    """Return saved chart settings for a run."""
    return load_chart_settings(run_id)


class ChartSettingsRequest(BaseModel):
    """Request model for saving chart settings."""

    indicators: dict | None = None
    fill_between: list | None = None


@router.put("/runs/{run_id}/chart-settings")
async def api_put_chart_settings(run_id: str, request: ChartSettingsRequest) -> dict:
    """Save chart settings for a run."""
    settings: dict = {}
    if request.indicators is not None:
        settings["indicators"] = request.indicators
    if request.fill_between is not None:
        settings["fill_between"] = request.fill_between
    save_chart_settings(run_id, settings)
    return {"status": "ok"}


@router.get("/runs/{run_id}/bar-timestamps")
async def api_run_bar_timestamps(run_id: str, symbol: str) -> dict:
    """Return list of bar timestamps for a run and symbol."""
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"timestamps": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ts_event_ns FROM bars_processed
        WHERE run_id = ? AND symbol = ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol),
    )
    timestamps = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"timestamps": timestamps}


@router.get("/runs/{run_id}/bars")
async def api_run_bars(run_id: str, symbol: str) -> dict:
    """Return bar data for a run and symbol in lightweight-charts format with indicators."""
    import json as json_module

    from ..chart_settings import load_chart_settings
    from ..charting import _get_indicator_setting

    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"bars": [], "indicators": {}}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ts_event_ns, open, high, low, close, volume, indicators
        FROM bars_processed
        WHERE run_id = ? AND symbol = ?
        ORDER BY ts_event_ns
        """,
        (run_id, symbol),
    )
    rows = cursor.fetchall()
    conn.close()

    chart_settings = load_chart_settings(run_id) or None

    bars = []
    indicator_series: dict[str, list[dict]] = {}
    indicator_meta: dict[str, dict] = {}
    _color_idx = 0
    for row in rows:
        ts_seconds = row[0] // 1_000_000_000
        bars.append(
            {
                "time": ts_seconds,
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
        )
        indicators = json_module.loads(row[6]) if row[6] else {}
        for name, value in indicators.items():
            if name not in indicator_series:
                indicator_series[name] = []
                cfg = _get_indicator_setting(chart_settings, name, _color_idx)
                _color_idx += 1
                indicator_meta[name] = {
                    "panel": cfg.get("panel", 0),
                    "style": cfg.get("style", "line"),
                    "color": cfg.get("color", "black"),
                    "display_name": name,
                    "visible": cfg.get("visible", True),
                }
            if value is not None and value == value:
                indicator_series[name].append({"time": ts_seconds, "value": value})
    indicators_out = {
        name: {"data": data, "meta": indicator_meta[name]}
        for name, data in indicator_series.items()
        if indicator_meta[name].get("visible", True)
    }
    return {"bars": bars, "indicators": indicators_out}
