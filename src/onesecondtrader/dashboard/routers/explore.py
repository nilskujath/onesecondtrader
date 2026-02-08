"""
API endpoints for data exploration.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from ..db import connect_runs
from ..explore import (
    ExploreRequest,
    enqueue_exploration,
    explore_jobs,
    _explore_progress,
    _jobs_lock,
)
from ..presets import create_preset_routes

router = APIRouter(prefix="/api/explore", tags=["explore"])

# ── Preset routers (name+config schema) ──

explore_presets_router, ensure_explore_presets_table = create_preset_routes(
    table_name="explore_presets",
    prefix="/api/explore/presets",
    tag="explore-presets",
)

condition_presets_router, ensure_condition_presets_table = create_preset_routes(
    table_name="condition_presets",
    prefix="/api/explore/condition-presets",
    tag="condition-presets",
)


@router.post("/run")
async def api_explore_run(request: ExploreRequest) -> dict:
    """Start an exploration run."""
    if not request.symbols:
        return {"error": "No symbols selected"}
    if not request.indicators:
        return {"error": "No indicators selected"}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{ts}-{uuid.uuid4().hex[:8]}"
    enqueue_exploration(request, run_id)
    return {"run_id": run_id, "status": "queued"}


@router.get("/status/{run_id}")
async def api_explore_status(run_id: str) -> dict:
    """Return the status of an exploration run."""
    with _jobs_lock:
        status = explore_jobs.get(run_id)
        progress = _explore_progress.get(run_id, 0.0)
    if status is None:
        return {"status": "unknown", "progress": 0.0}
    return {"status": status, "progress": progress}


@router.get("/runs")
async def api_explore_runs() -> dict:
    """Return recent exploration runs."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"runs": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT run_id, name, ts_start, ts_end, status, config, metadata
            FROM runs
            ORDER BY ts_start DESC
            """
        )
        rows = cursor.fetchall()
    runs = []
    for row in rows:
        config = json.loads(row[5]) if row[5] else {}
        if config.get("mode") != "exploration":
            continue
        metadata = json.loads(row[6]) if row[6] else None
        runs.append(
            {
                "run_id": row[0],
                "name": row[1],
                "ts_start": row[2],
                "ts_end": row[3],
                "status": row[4],
                "config": config,
                "metadata": metadata,
            }
        )
    return {"runs": runs}
