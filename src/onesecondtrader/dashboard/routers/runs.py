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
from ..charting import generate_chart_image

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
