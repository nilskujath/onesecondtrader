"""
API endpoints for backtest execution and status.

Provides endpoints for starting backtests and querying their status.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from ..backtest import (
    BacktestRequest,
    enqueue_backtest,
    running_jobs,
    _orchestrator_refs,
    _running_metadata,
    _jobs_lock,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run")
async def api_backtest_run(request: BacktestRequest) -> dict:
    """Enqueue a backtest and return the run ID."""
    run_id = str(uuid.uuid4())
    enqueue_backtest(request, run_id)
    return {"run_id": run_id, "status": "queued"}


@router.get("/running")
async def api_backtest_running() -> dict:
    """Return all currently running backtests with metadata and progress."""
    result = []
    with _jobs_lock:
        items = list(running_jobs.items())
        meta_snapshot = dict(_running_metadata)
        orch_snapshot = dict(_orchestrator_refs)
    for run_id, status in items:
        if status in ("running", "queued"):
            meta = meta_snapshot.get(run_id, {})
            orch = orch_snapshot.get(run_id)
            progress = int(orch.progress * 100) if orch is not None else 0
            result.append(
                {
                    "run_id": run_id,
                    "status": status,
                    "progress": progress,
                    **meta,
                }
            )
    return {"running": result}


@router.get("/status/{run_id}")
async def api_backtest_status(run_id: str) -> dict:
    """Return the current status of a backtest job."""
    with _jobs_lock:
        status = running_jobs.get(run_id, "not found")
        orch = _orchestrator_refs.get(run_id)
    progress = 0
    if status == "running":
        if orch is not None:
            progress = int(orch.progress * 100)
    elif status == "completed":
        progress = 100
    return {"run_id": run_id, "status": status, "progress": progress}
