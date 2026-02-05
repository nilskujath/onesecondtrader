"""
API endpoints for backtest execution and status.

Provides endpoints for starting backtests and querying their status.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks

from ..backtest import BacktestRequest, run_backtest, running_jobs

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run")
async def api_backtest_run(
    request: BacktestRequest, background_tasks: BackgroundTasks
) -> dict:
    """Start a backtest in the background and return the run ID."""
    run_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(run_backtest, request, run_id)
    return {"run_id": run_id, "status": "started"}


@router.get("/status/{run_id}")
async def api_backtest_status(run_id: str) -> dict:
    """Return the current status of a backtest job."""
    status = running_jobs.get(run_id, "not found")
    return {"run_id": run_id, "status": status}
