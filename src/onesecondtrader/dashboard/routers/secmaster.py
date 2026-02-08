"""
API endpoints for security master database queries.

Provides endpoints for querying publishers, datasets, and symbol coverage information.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..db import connect_secmaster

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
    publisher_id: int | None = None, rtype: int | None = None
) -> dict:
    """Return symbol coverage data, optionally filtered by publisher_id and rtype."""
    try:
        conn_ctx = connect_secmaster()
    except FileNotFoundError:
        return {"symbols": []}
    with conn_ctx as conn:
        cursor = conn.cursor()
        if publisher_id is not None and rtype is not None:
            cursor.execute(
                "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
                "WHERE publisher_id = ? AND rtype = ? ORDER BY symbol",
                (publisher_id, rtype),
            )
        elif publisher_id is not None:
            cursor.execute(
                "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
                "WHERE publisher_id = ? ORDER BY symbol, rtype",
                (publisher_id,),
            )
        elif rtype is not None:
            cursor.execute(
                "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
                "WHERE rtype = ? ORDER BY symbol",
                (rtype,),
            )
        else:
            cursor.execute(
                "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage ORDER BY symbol, rtype"
            )
        symbols = [
            {
                "publisher_id": row[0],
                "symbol": row[1],
                "rtype": row[2],
                "min_ts": row[3],
                "max_ts": row[4],
            }
            for row in cursor.fetchall()
        ]
    return {"symbols": symbols}
