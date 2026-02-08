"""API endpoints for the new Explorer tab."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from ..explorer import (
    ExplorerRequest,
    enqueue_exploration,
    explorer_jobs,
    get_explorer_progress,
    _jobs_lock,
)

router = APIRouter(prefix="/api/explorer", tags=["explorer"])


@router.post("/run")
async def api_explorer_run(request: ExplorerRequest) -> dict:
    """Start an exploration run using the Orchestrator."""
    if not request.symbols:
        return {"error": "No symbols selected"}
    if not request.indicators:
        return {"error": "No indicators selected"}
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{ts}-{uuid.uuid4().hex[:8]}"
    enqueue_exploration(request, run_id)
    return {"run_id": run_id, "status": "queued"}


@router.get("/status/{run_id}")
async def api_explorer_status(run_id: str) -> dict:
    """Return the status and progress of an exploration run."""
    with _jobs_lock:
        status = explorer_jobs.get(run_id)
    if status is None:
        return {"status": "unknown", "progress": 0.0}
    progress = get_explorer_progress(run_id)
    if status == "completed":
        progress = 1.0
    return {"status": status, "progress": progress}
