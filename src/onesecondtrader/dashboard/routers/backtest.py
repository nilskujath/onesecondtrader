"""
API endpoints for backtest execution and status.

Provides endpoints for starting backtests and querying their status.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks

from ..backtest import (
    BacktestRequest,
    run_backtest,
    running_jobs,
    _orchestrator_refs,
    _running_metadata,
)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run")
async def api_backtest_run(
    request: BacktestRequest, background_tasks: BackgroundTasks
) -> dict:
    """Start a backtest in the background and return the run ID."""
    run_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_backtest, request, run_id)
    return {"run_id": run_id, "status": "started"}


@router.get("/running")
async def api_backtest_running() -> dict:
    """Return all currently running backtests with metadata and progress."""
    result = []
    for run_id, status in running_jobs.items():
        if status == "running":
            meta = _running_metadata.get(run_id, {})
            orch = _orchestrator_refs.get(run_id)
            progress = int(orch.progress * 100) if orch is not None else 0
            result.append(
                {
                    "run_id": run_id,
                    "progress": progress,
                    **meta,
                }
            )
    return {"running": result}


@router.get("/status/{run_id}")
async def api_backtest_status(run_id: str) -> dict:
    """Return the current status of a backtest job."""
    status = running_jobs.get(run_id, "not found")
    progress = 0
    if status == "running":
        orch = _orchestrator_refs.get(run_id)
        if orch is not None:
            progress = int(orch.progress * 100)
    elif status == "completed":
        progress = 100
    return {"run_id": run_id, "status": status, "progress": progress}
