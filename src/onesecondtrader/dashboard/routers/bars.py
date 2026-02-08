"""
API endpoints for bar data retrieval.

Provides endpoints for fetching bar data and bar timestamps for a run.
"""

from __future__ import annotations

import json as json_module

from fastapi import APIRouter

from ..db import connect_runs, get_strategy_key
from ..chart_settings import load_chart_settings
from ..charting import _get_indicator_setting

router = APIRouter(prefix="/api", tags=["bars"])


@router.get("/runs/{run_id}/bar-timestamps")
async def api_run_bar_timestamps(run_id: str, symbol: str) -> dict:
    """Return list of bar timestamps for a run and symbol."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"timestamps": []}
    with conn_ctx as conn:
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
    return {"timestamps": timestamps}


@router.get("/runs/{run_id}/bars")
async def api_run_bars(run_id: str, symbol: str) -> dict:
    """Return bar data for a run and symbol in lightweight-charts format with indicators."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"bars": [], "indicators": {}}
    with conn_ctx as conn:
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

    strategy_key = get_strategy_key(run_id)
    chart_settings = load_chart_settings(strategy_key) or None

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
