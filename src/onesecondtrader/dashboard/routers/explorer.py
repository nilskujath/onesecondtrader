"""API endpoints for the new Explorer tab."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..explorer import (
    ExplorerRequest,
    SingleIndicatorRequest,
    IndicatorConfig,
    enqueue_exploration,
    enqueue_single_indicator,
    cancel_run,
    explorer_jobs,
    get_explorer_progress,
    create_or_get_session,
    find_cached_run,
    get_session_indicators,
    get_session_run_ids,
    _instantiate_indicators,
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


@router.post("/cancel/{run_id}")
async def api_cancel_run(run_id: str) -> dict:
    """Cancel a running exploration."""
    success = cancel_run(run_id)
    if success:
        return {"status": "cancelled"}
    with _jobs_lock:
        current = explorer_jobs.get(run_id)
    if current is None:
        return {"status": "unknown"}
    return {"status": current}


class SessionRequest(BaseModel):
    publisher_id: int
    rtype: int
    symbols: list[str]
    start_date: str | None = None
    end_date: str | None = None
    symbol_type: str = "raw_symbol"


@router.post("/session")
async def api_create_session(request: SessionRequest) -> dict:
    """Create or retrieve a session. Returns session_id and cached indicators."""
    session_id, cached = create_or_get_session(
        publisher_id=request.publisher_id,
        rtype=request.rtype,
        symbols=request.symbols,
        start_date=request.start_date,
        end_date=request.end_date,
        symbol_type=request.symbol_type,
    )
    return {
        "session_id": session_id,
        "cached_indicators": cached,
    }


class RunSingleRequest(BaseModel):
    session_id: str
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None
    indicator: IndicatorConfig
    symbol_type: str = "raw_symbol"


@router.post("/run-single")
async def api_run_single(request: RunSingleRequest) -> dict:
    """Run a single indicator within a session. Checks cache first."""
    # Compute current indicator name for cache validation
    indicator_name = None
    try:
        instances = _instantiate_indicators([request.indicator])
        if instances:
            indicator_name = instances[0].name
    except Exception:
        pass

    # Check cache
    cached_run_id = find_cached_run(
        request.session_id,
        request.indicator.class_name,
        request.indicator.params,
        indicator_name=indicator_name,
    )
    if cached_run_id:
        return {
            "run_id": cached_run_id,
            "status": "completed",
            "cached": True,
            "indicator_name": indicator_name,
        }

    # Create new run
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = f"{ts}-{uuid.uuid4().hex[:8]}"

    single_req = SingleIndicatorRequest(
        symbols=request.symbols,
        rtype=request.rtype,
        publisher_id=request.publisher_id,
        start_date=request.start_date,
        end_date=request.end_date,
        indicator=request.indicator,
        symbol_type=request.symbol_type,
        session_id=request.session_id,
    )
    enqueue_single_indicator(single_req, run_id)
    return {
        "run_id": run_id,
        "status": "queued",
        "cached": False,
        "indicator_name": indicator_name,
    }


@router.get("/session/{session_id}/indicators")
async def api_session_indicators(session_id: str) -> dict:
    """Returns all indicator runs in session with statuses and run_ids."""
    indicators = get_session_indicators(session_id)
    return {"indicators": indicators}


@router.get("/session/{session_id}/run-ids")
async def api_session_run_ids(session_id: str) -> dict:
    """Returns completed run_ids for chart endpoints."""
    run_ids = get_session_run_ids(session_id)
    return {"run_ids": run_ids}
