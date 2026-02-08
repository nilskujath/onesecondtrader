"""
API endpoints for security master database queries.

Provides endpoints for querying publishers, datasets, and symbol coverage information.
"""

from __future__ import annotations

import pathlib

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import connect_secmaster, get_secmaster_path

router = APIRouter(prefix="/api/secmaster", tags=["secmaster"])


@router.get("/publishers")
async def api_secmaster_publishers(rtype: int | None = None) -> dict:
    """Return list of publishers, optionally filtered by rtype."""
    try:
        conn_ctx = connect_secmaster()
    except FileNotFoundError:
        return {"publishers": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        if rtype is not None:
            cursor.execute(
                "SELECT DISTINCT p.name FROM publishers p "
                "JOIN symbol_coverage sc ON p.publisher_id = sc.publisher_id "
                "WHERE sc.rtype = ? ORDER BY p.name",
                (rtype,),
            )
        else:
            cursor.execute("SELECT DISTINCT name FROM publishers ORDER BY name")
        publishers = [row[0] for row in cursor.fetchall()]
    return {"publishers": publishers}


@router.get("/publishers/{name}/datasets")
async def api_secmaster_datasets(name: str, rtype: int | None = None) -> dict:
    """Return datasets for a publisher, optionally filtered by rtype."""
    try:
        conn_ctx = connect_secmaster()
    except FileNotFoundError:
        return {"datasets": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        if rtype is not None:
            cursor.execute(
                "SELECT DISTINCT p.publisher_id, p.dataset FROM publishers p "
                "JOIN symbol_coverage sc ON p.publisher_id = sc.publisher_id "
                "WHERE p.name = ? AND sc.rtype = ? ORDER BY p.dataset",
                (name, rtype),
            )
        else:
            cursor.execute(
                "SELECT publisher_id, dataset FROM publishers WHERE name = ? ORDER BY dataset",
                (name,),
            )
        datasets = [
            {"publisher_id": row[0], "dataset": row[1]} for row in cursor.fetchall()
        ]
    return {"datasets": datasets}


@router.get("/symbols_coverage")
async def api_secmaster_symbols_coverage(
    publisher_id: int | None = None,
    rtype: int | None = None,
    symbol_type: str | None = None,
) -> dict:
    """Return symbol coverage data, optionally filtered by publisher_id, rtype, and symbol_type."""
    try:
        conn_ctx = connect_secmaster()
    except FileNotFoundError:
        return {"symbols": []}

    # Check if symbol_type column exists (handles pre-migration DBs)
    with conn_ctx as conn:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(symbol_coverage)").fetchall()
        }
        has_symbol_type = "symbol_type" in cols

        select_cols = "publisher_id, symbol, rtype, min_ts, max_ts"
        if has_symbol_type:
            select_cols = "publisher_id, symbol, symbol_type, rtype, min_ts, max_ts"

        conditions = []
        params: list = []
        if publisher_id is not None:
            conditions.append("publisher_id = ?")
            params.append(publisher_id)
        if rtype is not None:
            conditions.append("rtype = ?")
            params.append(rtype)
        if symbol_type is not None and has_symbol_type:
            conditions.append("symbol_type = ?")
            params.append(symbol_type)

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        query = (
            f"SELECT {select_cols} FROM symbol_coverage{where} ORDER BY symbol, rtype"
        )

        cursor = conn.cursor()
        cursor.execute(query, params)
        if has_symbol_type:
            symbols = [
                {
                    "publisher_id": row[0],
                    "symbol": row[1],
                    "symbol_type": row[2],
                    "rtype": row[3],
                    "min_ts": row[4],
                    "max_ts": row[5],
                }
                for row in cursor.fetchall()
            ]
        else:
            symbols = [
                {
                    "publisher_id": row[0],
                    "symbol": row[1],
                    "symbol_type": "raw_symbol",
                    "rtype": row[2],
                    "min_ts": row[3],
                    "max_ts": row[4],
                }
                for row in cursor.fetchall()
            ]
    return {"symbols": symbols}


class BuildContinuousRequest(BaseModel):
    publisher_id: int
    root_symbol: str
    roll_rule: str = "c"
    roll_offset_days: int = 0


@router.post("/build-continuous")
async def api_build_continuous(request: BuildContinuousRequest) -> dict:
    """Build continuous contract symbology from individual contract data."""
    from onesecondtrader.secmaster.continuous import build_continuous_symbology

    db_path = pathlib.Path(get_secmaster_path())
    count = build_continuous_symbology(
        db_path=db_path,
        publisher_id=request.publisher_id,
        root_symbol=request.root_symbol,
        roll_rule=request.roll_rule,
        roll_offset_days=request.roll_offset_days,
    )
    return {"status": "ok", "entries_created": count}
