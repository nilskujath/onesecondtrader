"""
API endpoints for run management.

Provides endpoints for listing, deleting, and querying runs and their round-trips.
"""

from __future__ import annotations

import asyncio
import json as json_module
import logging
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..backtest import (
    cancel_backtest,
    running_jobs,
    _orchestrator_refs,
    _jobs_lock,
)
from ..db import get_runs, connect_runs, CHILD_TABLES
from ..roundtrips import get_roundtrips

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
        with connect_runs(timeout=10) as conn:
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
            return {"deleted": deleted}
    except FileNotFoundError:
        return {"deleted": 0}
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


@router.get("/runs/{run_id}/symbols")
async def api_run_symbols(run_id: str) -> dict:
    """Return list of symbols available in a run."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"symbols": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT symbol FROM bars_processed WHERE run_id = ? ORDER BY symbol
            """,
            (run_id,),
        )
        symbols = [row[0] for row in cursor.fetchall()]
    return {"symbols": symbols}


@router.get("/runs/{run_id}/indicators")
async def api_run_indicators(run_id: str) -> dict:
    """Return list of indicator names present in a run."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return {"indicators": []}
    with conn_ctx as conn:
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
    names: set[str] = set()
    for (indicators_json,) in rows:
        if indicators_json:
            indicators = json_module.loads(indicators_json)
            names.update(indicators.keys())
    return {"indicators": sorted(names)}
