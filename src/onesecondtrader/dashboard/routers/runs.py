"""
API endpoints for run management.

Provides endpoints for listing, deleting, and querying runs and their round-trips.
"""

from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from ..db import get_runs_db_path, get_runs, CHILD_TABLES
from ..roundtrips import get_roundtrips
from ..charting import (
    generate_chart_image,
    generate_segment_chart_image,
    generate_trade_journey_chart,
    generate_pnl_summary_chart,
)

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
    """Delete specified runs and their associated data."""
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return {"deleted": 0}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    deleted = 0
    for run_id in request.run_ids:
        for table in CHILD_TABLES:
            cursor.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        deleted += cursor.rowcount
    conn.commit()
    conn.close()
    return {"deleted": deleted}


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
) -> Response:
    """Return a PNG chart image for a round-trip trade."""
    image_bytes = generate_chart_image(run_id, symbol, start_ns, end_ns, direction, pnl)
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
) -> Response:
    """Return a PNG chart image for a bar segment."""
    image_bytes = generate_segment_chart_image(
        run_id, symbol, start_ns, end_ns, period_start_ns, period_end_ns
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
    bars = []
    indicator_series: dict[str, list[dict]] = {}
    indicator_meta: dict[str, dict] = {}
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
                tag = int(name[:2]) if len(name) >= 2 and name[:2].isdigit() else 99
                style = name[2] if len(name) > 2 and name[2] in "LHD" else "L"
                display_name = (
                    name[4:]
                    if len(name) > 4 and name[2] == "_"
                    else (name[3:] if len(name) > 3 else name)
                )
                indicator_meta[name] = {
                    "tag": tag,
                    "style": style,
                    "display_name": display_name,
                }
            if value is not None and value == value:
                indicator_series[name].append({"time": ts_seconds, "value": value})
    indicators_out = {
        name: {"data": data, "meta": indicator_meta[name]}
        for name, data in indicator_series.items()
        if indicator_meta[name]["tag"] != 99
    }
    return {"bars": bars, "indicators": indicators_out}
