"""
API endpoints for chart segmentation.

Provides endpoints for splitting run data into chart segments by bar count,
time period, or conditional indicator logic.
"""

from __future__ import annotations

import json as json_module
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import connect_runs
from ..explorer import get_session_run_ids as _get_session_run_ids

router = APIRouter(prefix="/api", tags=["segments"])

# GIL yield: release every N bars so the event-loop thread can run
_YIELD_BATCH = 2000

# Bounded executor for background filter jobs (matches explorer.py pattern)
_filter_executor = ThreadPoolExecutor(max_workers=1)

# Background filter job tracking
_filter_jobs: dict = {}  # filter_id → {status, progress, segments, cancel_event, error}
_filter_lock = threading.Lock()

TIME_PERIOD_NS = {
    "year": 365 * 24 * 60 * 60 * 1_000_000_000,
    "quarter": 91 * 24 * 60 * 60 * 1_000_000_000,
    "month": 30 * 24 * 60 * 60 * 1_000_000_000,
    "week": 7 * 24 * 60 * 60 * 1_000_000_000,
    "day": 24 * 60 * 60 * 1_000_000_000,
    "4hour": 4 * 60 * 60 * 1_000_000_000,
    "hour": 60 * 60 * 1_000_000_000,
    "20min": 20 * 60 * 1_000_000_000,
    "15min": 15 * 60 * 1_000_000_000,
    "10min": 10 * 60 * 1_000_000_000,
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
    elif time_period == "20min":
        min_block = (dt.minute // 20) * 20
        boundary = datetime(
            dt.year, dt.month, dt.day, dt.hour, min_block, tzinfo=timezone.utc
        )
    elif time_period == "15min":
        min_block = (dt.minute // 15) * 15
        boundary = datetime(
            dt.year, dt.month, dt.day, dt.hour, min_block, tzinfo=timezone.utc
        )
    elif time_period == "10min":
        min_block = (dt.minute // 10) * 10
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


def _get_next_period_boundary(ts_ns: int, time_period: str) -> int:
    """Return the start of the NEXT period after the one containing ts_ns."""
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)
    if time_period == "year":
        boundary = datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
    elif time_period == "quarter":
        quarter_month = ((dt.month - 1) // 3) * 3 + 1
        if quarter_month + 3 > 12:
            boundary = datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            boundary = datetime(dt.year, quarter_month + 3, 1, tzinfo=timezone.utc)
    elif time_period == "month":
        if dt.month == 12:
            boundary = datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            boundary = datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)
    elif time_period == "week":
        period_start = _get_period_boundary(ts_ns, "week")
        boundary = datetime.fromtimestamp(
            period_start / 1_000_000_000 + 7 * 86400, tz=timezone.utc
        )
    elif time_period in (
        "day",
        "4hour",
        "hour",
        "20min",
        "15min",
        "10min",
        "5min",
        "1min",
    ):
        period_start = _get_period_boundary(ts_ns, time_period)
        period_ns = TIME_PERIOD_NS[time_period]
        boundary = datetime.fromtimestamp(
            (period_start + period_ns) / 1_000_000_000, tz=timezone.utc
        )
    else:
        period_start = _get_period_boundary(ts_ns, time_period)
        period_ns = TIME_PERIOD_NS.get(time_period, TIME_PERIOD_NS["day"])
        boundary = datetime.fromtimestamp(
            (period_start + period_ns) / 1_000_000_000, tz=timezone.utc
        )
    return int(boundary.timestamp() * 1_000_000_000)


def _split_by_time(cursor, run_id: str, symbol: str, time_period: str) -> list[dict]:
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
        period_end_ns = _get_next_period_boundary(all_ts[idx], time_period) - 1
        period_end = period_end_ns
        start_idx = idx
        end_idx = idx
        while end_idx + 1 < len(all_ts) and all_ts[end_idx + 1] <= period_end:
            end_idx += 1
        segments.append(
            {
                "symbol": symbol,
                "segment_num": segment_num,
                "start_ts": str(period_start),
                "end_ts": str(period_end + 1),
                "bar_count": end_idx - start_idx + 1,
                "period_start_ns": str(period_start),
                "period_end_ns": str(period_end + 1),
            }
        )
        segment_num += 1
        idx = end_idx + 1
    return segments


class ConditionSpec(BaseModel):
    left_field: str
    operator: str
    right_field: str | None = None
    right_value: float | None = None


class ConditionalSegmentsRequest(BaseModel):
    conditions: list[ConditionSpec]
    context_bars: int = 50
    gap_tolerance: int = 0
    run_ids: list[str] | None = None


BAR_FIELDS = {"open", "high", "low", "close", "volume"}


def _get_bar_field_value(bar_dict: dict, field_name: str) -> float | None:
    """Return a value from OHLCV columns or the indicator JSON."""
    lower = field_name.lower()
    if lower in BAR_FIELDS:
        return bar_dict.get(lower)
    indicators = bar_dict.get("indicators", {})
    return indicators.get(field_name)


def _evaluate_condition(left: float | None, op: str, right: float | None) -> bool:
    """Evaluate left {op} right, returning False if either is NaN/None."""
    if left is None or right is None:
        return False
    import math as _math

    if _math.isnan(left) or _math.isnan(right):
        return False
    if op == "<=":
        return left <= right
    elif op == ">=":
        return left >= right
    elif op == "<":
        return left < right
    elif op == ">":
        return left > right
    elif op == "==":
        return left == right
    elif op == "!=":
        return left != right
    return False


def _build_segments_from_flags(
    bars: list[dict],
    condition_flags: list[bool],
    context_bars: int,
    gap_tolerance: int,
    symbol: str,
) -> list[dict]:
    """Group True flags into merged regions with context padding."""
    # Group consecutive True bars into raw regions
    raw_regions = []
    i = 0
    n = len(condition_flags)
    while i < n:
        if condition_flags[i]:
            start = i
            while i < n and condition_flags[i]:
                i += 1
            raw_regions.append((start, i - 1))
        else:
            i += 1

    if not raw_regions:
        return []

    # Merge regions separated by <= gap_tolerance False bars
    merged = [raw_regions[0]]
    for region in raw_regions[1:]:
        prev_end = merged[-1][1]
        gap = region[0] - prev_end - 1
        if gap <= gap_tolerance:
            merged[-1] = (merged[-1][0], region[1])
        else:
            merged.append(region)

    # Build segments with context
    segments = []
    total_bars = len(bars)
    for seg_num, (cond_start, cond_end) in enumerate(merged, 1):
        ctx_start = max(0, cond_start - context_bars)
        ctx_end = min(total_bars - 1, cond_end + context_bars)
        segments.append(
            {
                "symbol": symbol,
                "segment_num": seg_num,
                "start_ts": str(bars[ctx_start]["ts"]),
                "end_ts": str(bars[ctx_end]["ts"]),
                "condition_start_ts": str(bars[cond_start]["ts"]),
                "condition_end_ts": str(bars[cond_end]["ts"]),
                "bar_count": ctx_end - ctx_start + 1,
                "condition_bar_count": cond_end - cond_start + 1,
            }
        )

    return segments


def _load_bars(cursor, run_id: str, symbol: str, cancel_event=None) -> list[dict]:
    """Load bars from bars_processed for a given run and symbol."""
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
    bars = []
    for i, row in enumerate(rows):
        indicators = json_module.loads(row[6]) if row[6] else {}
        bars.append(
            {
                "ts": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "indicators": indicators,
            }
        )
        if (i + 1) % _YIELD_BATCH == 0:
            time.sleep(0)
            if cancel_event is not None and cancel_event.is_set():
                return bars
    return bars


def _load_bars_merged(
    cursor, run_ids: list[str], symbol: str, cancel_event=None
) -> list[dict]:
    """Load bars from the first run_id, then merge indicators from additional runs."""
    if not run_ids:
        return []
    bars = _load_bars(cursor, run_ids[0], symbol, cancel_event=cancel_event)
    if not bars or len(run_ids) <= 1:
        return bars
    # Build ts -> bar index lookup
    ts_to_idx = {bar["ts"]: i for i, bar in enumerate(bars)}
    for extra_run_id in run_ids[1:]:
        if cancel_event is not None and cancel_event.is_set():
            return bars
        cursor.execute(
            """
            SELECT ts_event_ns, indicators
            FROM bars_processed
            WHERE run_id = ? AND symbol = ?
            ORDER BY ts_event_ns
            """,
            (extra_run_id, symbol),
        )
        for i, row in enumerate(cursor.fetchall()):
            idx = ts_to_idx.get(row[0])
            if idx is not None:
                extra_indicators = json_module.loads(row[1]) if row[1] else {}
                bars[idx]["indicators"].update(extra_indicators)
            if (i + 1) % _YIELD_BATCH == 0:
                time.sleep(0)
                if cancel_event is not None and cancel_event.is_set():
                    return bars
    return bars


def _find_multi_conditional_segments(
    cursor,
    run_id: str,
    symbol: str,
    conditions: list[ConditionSpec],
    context_bars: int,
    gap_tolerance: int,
) -> list[dict]:
    """Evaluate multiple conditions with AND logic per bar."""
    bars = _load_bars(cursor, run_id, symbol)
    if not bars:
        return []

    condition_flags = []
    for j, bar in enumerate(bars):
        all_true = True
        for cond in conditions:
            left_val = _get_bar_field_value(bar, cond.left_field)
            if cond.right_field:
                right_val = _get_bar_field_value(bar, cond.right_field)
            else:
                right_val = cond.right_value
            if not _evaluate_condition(left_val, cond.operator, right_val):
                all_true = False
                break
        condition_flags.append(all_true)
        if (j + 1) % _YIELD_BATCH == 0:
            time.sleep(0)

    return _build_segments_from_flags(
        bars, condition_flags, context_bars, gap_tolerance, symbol
    )


def _find_conditional_segments(
    cursor,
    run_id: str,
    symbol: str,
    left_field: str,
    operator: str,
    right_field: str | None,
    right_value: float | None,
    context_bars: int,
    gap_tolerance: int,
) -> list[dict]:
    bars = _load_bars(cursor, run_id, symbol)
    if not bars:
        return []

    # Evaluate condition per bar
    condition_flags = []
    for j, bar in enumerate(bars):
        left_val = _get_bar_field_value(bar, left_field)
        if right_field:
            right_val = _get_bar_field_value(bar, right_field)
        else:
            right_val = right_value
        condition_flags.append(_evaluate_condition(left_val, operator, right_val))
        if (j + 1) % _YIELD_BATCH == 0:
            time.sleep(0)

    return _build_segments_from_flags(
        bars, condition_flags, context_bars, gap_tolerance, symbol
    )


@router.get("/runs/{run_id}/conditional-segments")
def api_conditional_segments(
    run_id: str,
    left_field: str,
    operator: str,
    right_field: str | None = None,
    right_value: float | None = None,
    context_bars: int = 50,
    gap_tolerance: int = 0,
) -> dict:
    """Return conditional chart segments for a run."""
    if operator not in ("<=", ">=", "<", ">", "==", "!="):
        raise HTTPException(status_code=400, detail=f"Invalid operator: {operator}")
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"segments": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol
            """,
            (run_id,),
        )
        symbols = [row[0] for row in cursor.fetchall()]
        segments = []
        for symbol in symbols:
            segments.extend(
                _find_conditional_segments(
                    cursor,
                    run_id,
                    symbol,
                    left_field,
                    operator,
                    right_field,
                    right_value,
                    context_bars,
                    gap_tolerance,
                )
            )
    return {"segments": segments}


@router.post("/runs/{run_id}/conditional-segments")
def api_conditional_segments_multi(
    run_id: str,
    request: ConditionalSegmentsRequest,
) -> dict:
    """Return conditional chart segments for a run using multiple AND conditions."""
    valid_ops = ("<=", ">=", "<", ">", "==", "!=")
    for cond in request.conditions:
        if cond.operator not in valid_ops:
            raise HTTPException(
                status_code=400, detail=f"Invalid operator: {cond.operator}"
            )
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"segments": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol
            """,
            (run_id,),
        )
        symbols = [row[0] for row in cursor.fetchall()]
        segments = []
        if not request.conditions:
            # No conditions: one overview segment per symbol (no condition highlight)
            for symbol in symbols:
                cursor.execute(
                    "SELECT MIN(ts_event_ns), MAX(ts_event_ns), COUNT(*) FROM bars_processed"
                    " WHERE run_id = ? AND symbol = ?",
                    (run_id, symbol),
                )
                row = cursor.fetchone()
                if row and row[2] > 0:
                    segments.append(
                        {
                            "symbol": symbol,
                            "segment_num": 1,
                            "start_ts": str(row[0]),
                            "end_ts": str(row[1]),
                            "condition_start_ts": None,
                            "condition_end_ts": None,
                            "bar_count": row[2],
                            "condition_bar_count": 0,
                        }
                    )
        else:
            for symbol in symbols:
                segments.extend(
                    _find_multi_conditional_segments(
                        cursor,
                        run_id,
                        symbol,
                        request.conditions,
                        request.context_bars,
                        request.gap_tolerance,
                    )
                )
    return {"segments": segments}


@router.get("/runs/{run_id}/chart-segments")
def api_chart_segments(
    run_id: str,
    mode: str = "bars",
    bars_per_chart: int = 500,
    overlap: int = 100,
    time_period: str = "day",
) -> dict:
    """Return chart segment metadata for a run."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"segments": [], "bar_period": None}
    with conn_ctx as conn:
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
                segments.extend(_split_by_time(cursor, run_id, symbol, time_period))
            else:
                segments.extend(
                    _split_by_bars(cursor, run_id, symbol, bars_per_chart, overlap)
                )
    return {"segments": segments, "bar_period": bar_period}


@router.get("/sessions/{session_id}/chart-segments")
def api_session_chart_segments(
    session_id: str,
    mode: str = "bars",
    bars_per_chart: int = 500,
    overlap: int = 100,
    time_period: str = "day",
    run_ids: str | None = None,
) -> dict:
    """Return chart segments using the first completed run_id from a session."""
    if run_ids is not None:
        run_id_list = [r for r in run_ids.split(",") if r]
    else:
        run_id_list = []
    if not run_id_list:
        run_id_list = _get_session_run_ids(session_id)
    if not run_id_list:
        return {"segments": [], "bar_period": None}
    run_id = run_id_list[0]
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"segments": [], "bar_period": None}
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT bar_period FROM bars_processed WHERE run_id = ? LIMIT 1",
            (run_id,),
        )
        bar_period_row = cursor.fetchone()
        bar_period = bar_period_row[0] if bar_period_row else None
        cursor.execute(
            "SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol",
            (run_id,),
        )
        symbols = [row[0] for row in cursor.fetchall()]
        segments = []
        for symbol in symbols:
            if mode == "time":
                segments.extend(_split_by_time(cursor, run_id, symbol, time_period))
            else:
                segments.extend(
                    _split_by_bars(cursor, run_id, symbol, bars_per_chart, overlap)
                )
    return {"segments": segments, "bar_period": bar_period}


@router.post("/sessions/{session_id}/conditional-segments")
def api_session_conditional_segments(
    session_id: str,
    request: ConditionalSegmentsRequest,
) -> dict:
    """Return conditional segments using merged indicator data from all session runs."""
    if request.run_ids:
        run_ids = request.run_ids
    else:
        run_ids = _get_session_run_ids(session_id)
    if not run_ids:
        return {"segments": []}
    valid_ops = ("<=", ">=", "<", ">", "==", "!=")
    for cond in request.conditions:
        if cond.operator not in valid_ops:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400, detail=f"Invalid operator: {cond.operator}"
            )
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"segments": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        # Get symbols from first run
        cursor.execute(
            "SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol",
            (run_ids[0],),
        )
        symbols = [row[0] for row in cursor.fetchall()]
        segments = []
        if not request.conditions:
            for symbol in symbols:
                cursor.execute(
                    "SELECT MIN(ts_event_ns), MAX(ts_event_ns), COUNT(*) FROM bars_processed"
                    " WHERE run_id = ? AND symbol = ?",
                    (run_ids[0], symbol),
                )
                row = cursor.fetchone()
                if row and row[2] > 0:
                    segments.append(
                        {
                            "symbol": symbol,
                            "segment_num": 1,
                            "start_ts": str(row[0]),
                            "end_ts": str(row[1]),
                            "condition_start_ts": None,
                            "condition_end_ts": None,
                            "bar_count": row[2],
                            "condition_bar_count": 0,
                        }
                    )
        else:
            for symbol in symbols:
                bars = _load_bars_merged(cursor, run_ids, symbol)
                if not bars:
                    continue
                condition_flags = []
                for j, bar in enumerate(bars):
                    all_true = True
                    for cond in request.conditions:
                        left_val = _get_bar_field_value(bar, cond.left_field)
                        if cond.right_field:
                            right_val = _get_bar_field_value(bar, cond.right_field)
                        else:
                            right_val = cond.right_value
                        if not _evaluate_condition(left_val, cond.operator, right_val):
                            all_true = False
                            break
                    condition_flags.append(all_true)
                    if (j + 1) % _YIELD_BATCH == 0:
                        time.sleep(0)
                segments.extend(
                    _build_segments_from_flags(
                        bars,
                        condition_flags,
                        request.context_bars,
                        request.gap_tolerance,
                        symbol,
                    )
                )
    return {"segments": segments}


def _run_filter_job(
    filter_id: str,
    session_id: str,
    request: ConditionalSegmentsRequest,
) -> None:
    """Background thread target for a filter job."""
    job = _filter_jobs[filter_id]
    try:
        if request.run_ids:
            run_ids = request.run_ids
        else:
            run_ids = _get_session_run_ids(session_id)
        if not run_ids:
            with _filter_lock:
                job["status"] = "completed"
                job["progress"] = 1.0
                job["segments"] = []
            return

        conn_ctx = connect_runs()
        with conn_ctx as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol",
                (run_ids[0],),
            )
            symbols = [row[0] for row in cursor.fetchall()]
            segments: list[dict] = []

            if not request.conditions:
                for i, symbol in enumerate(symbols):
                    if job["cancel_event"].is_set():
                        with _filter_lock:
                            job["status"] = "cancelled"
                        return
                    cursor.execute(
                        "SELECT MIN(ts_event_ns), MAX(ts_event_ns), COUNT(*) "
                        "FROM bars_processed WHERE run_id = ? AND symbol = ?",
                        (run_ids[0], symbol),
                    )
                    row = cursor.fetchone()
                    if row and row[2] > 0:
                        segments.append(
                            {
                                "symbol": symbol,
                                "segment_num": 1,
                                "start_ts": str(row[0]),
                                "end_ts": str(row[1]),
                                "condition_start_ts": None,
                                "condition_end_ts": None,
                                "bar_count": row[2],
                                "condition_bar_count": 0,
                            }
                        )
                    with _filter_lock:
                        job["progress"] = (i + 1) / len(symbols)
            else:
                for i, symbol in enumerate(symbols):
                    if job["cancel_event"].is_set():
                        with _filter_lock:
                            job["status"] = "cancelled"
                        return
                    bars = _load_bars_merged(
                        cursor,
                        run_ids,
                        symbol,
                        cancel_event=job["cancel_event"],
                    )
                    if job["cancel_event"].is_set():
                        with _filter_lock:
                            job["status"] = "cancelled"
                        return
                    if not bars:
                        with _filter_lock:
                            job["progress"] = (i + 1) / len(symbols)
                        continue
                    condition_flags = []
                    cancel_ev = job["cancel_event"]
                    for j, bar in enumerate(bars):
                        all_true = True
                        for cond in request.conditions:
                            left_val = _get_bar_field_value(bar, cond.left_field)
                            if cond.right_field:
                                right_val = _get_bar_field_value(bar, cond.right_field)
                            else:
                                right_val = cond.right_value
                            if not _evaluate_condition(
                                left_val, cond.operator, right_val
                            ):
                                all_true = False
                                break
                        condition_flags.append(all_true)
                        if (j + 1) % _YIELD_BATCH == 0:
                            time.sleep(0)
                            if cancel_ev.is_set():
                                with _filter_lock:
                                    job["status"] = "cancelled"
                                return
                    segments.extend(
                        _build_segments_from_flags(
                            bars,
                            condition_flags,
                            request.context_bars,
                            request.gap_tolerance,
                            symbol,
                        )
                    )
                    with _filter_lock:
                        job["progress"] = (i + 1) / len(symbols)

        with _filter_lock:
            job["status"] = "completed"
            job["progress"] = 1.0
            job["segments"] = segments
    except Exception as exc:
        with _filter_lock:
            job["status"] = "error"
            job["error"] = str(exc)


@router.post("/sessions/{session_id}/start-filter")
def api_start_filter(session_id: str, request: ConditionalSegmentsRequest) -> dict:
    """Start a background filter job and return its ID immediately."""
    valid_ops = ("<=", ">=", "<", ">", "==", "!=")
    for cond in request.conditions:
        if cond.operator not in valid_ops:
            raise HTTPException(
                status_code=400, detail=f"Invalid operator: {cond.operator}"
            )
    filter_id = uuid.uuid4().hex[:12]
    job = {
        "status": "running",
        "progress": 0.0,
        "segments": None,
        "cancel_event": threading.Event(),
        "error": None,
    }
    with _filter_lock:
        _filter_jobs[filter_id] = job
    _filter_executor.submit(_run_filter_job, filter_id, session_id, request)
    return {"filter_id": filter_id}


@router.get("/filter-status/{filter_id}")
def api_filter_status(filter_id: str) -> dict:
    """Poll the status/progress of a background filter job."""
    with _filter_lock:
        job = _filter_jobs.get(filter_id)
    if not job:
        return {"status": "unknown", "progress": 0}
    result: dict = {"status": job["status"], "progress": job["progress"]}
    if job["status"] == "completed":
        result["segments"] = job["segments"] or []
        with _filter_lock:
            _filter_jobs.pop(filter_id, None)
    elif job["status"] in ("cancelled", "error"):
        if job["error"]:
            result["error"] = job["error"]
        with _filter_lock:
            _filter_jobs.pop(filter_id, None)
    return result


@router.post("/cancel-filter/{filter_id}")
def api_cancel_filter(filter_id: str) -> dict:
    """Cancel a running filter job."""
    with _filter_lock:
        job = _filter_jobs.get(filter_id)
    if not job:
        return {"status": "not_found"}
    job["cancel_event"].set()
    return {"status": "cancelling"}
