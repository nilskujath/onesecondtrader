"""API endpoints for train/dev/test data splits."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import connect_presets, connect_secmaster

router = APIRouter(prefix="/api/splits", tags=["splits"])

_backfill_done = False

_SPLIT_COLS = (
    "split_id, name, created_at, publisher_id, publisher_name, "
    "rtype, symbols, symbol_type, total_start, total_end, "
    "train_pct, dev_pct, train_end, dev_end, "
    "train_bars, dev_bars, test_bars"
)


class SplitCreateRequest(BaseModel):
    publisher_id: int
    publisher_name: str
    rtype: int
    symbols: list[str]
    symbol_type: str = "raw_symbol"
    total_start: str  # YYYY-MM-DD
    total_end: str  # YYYY-MM-DD
    train_pct: int  # e.g., 60
    dev_pct: int  # e.g., 20


def _compute_date_boundaries(
    total_start: str, total_end: str, train_pct: int, dev_pct: int
) -> tuple[str, str]:
    """Compute train_end and dev_end from percentage of calendar time."""
    start = date.fromisoformat(total_start)
    end = date.fromisoformat(total_end)
    total_days = (end - start).days
    if total_days <= 0:
        raise ValueError("total_end must be after total_start")
    train_days = round(total_days * train_pct / 100)
    dev_days = round(total_days * dev_pct / 100)
    train_end = start + timedelta(days=train_days)
    dev_end = train_end + timedelta(days=dev_days)
    return train_end.isoformat(), dev_end.isoformat()


def _make_split_name(symbols: list[str], created_at: str) -> str:
    """Generate a human-readable split name."""
    ts_part = created_at.replace(":", "-").replace("T", "_").split("+")[0]
    if len(symbols) == 1:
        return f"{symbols[0]}-{ts_part}"
    return f"{symbols[0]}+{len(symbols) - 1}-{ts_part}"


def _source_name(symbols: list[str], region: str, created_at: str) -> str:
    """Generate a source name for a split region."""
    ts_part = created_at.replace(":", "-").replace("T", "_").split("+")[0]
    if len(symbols) == 1:
        return f"{symbols[0]}-{region}-{ts_part}"
    return f"{symbols[0]}+{len(symbols) - 1}-{region}-{ts_part}"


def _count_bars_per_region(
    publisher_id: int,
    rtype: int,
    symbols: list[str],
    symbol_type: str,
    total_start: str,
    train_end: str,
    dev_end: str,
    total_end: str,
) -> tuple[int, int, int]:
    """Count bars in each train/dev/test region via a single secmaster query.

    Returns (train_bars, dev_bars, test_bars).
    """

    # Convert date strings to nanosecond timestamps
    def _date_to_ns(d: str) -> int:
        dt = datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp()) * 1_000_000_000

    start_ns = _date_to_ns(total_start)
    train_end_ns = _date_to_ns(train_end)
    dev_end_ns = _date_to_ns(dev_end)
    # end date is inclusive day, so add 1 day
    end_dt = datetime.strptime(total_end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_ns = (int(end_dt.timestamp()) + 86400) * 1_000_000_000 - 1

    placeholders = ",".join("?" * len(symbols))
    query = f"""
        SELECT
            SUM(CASE WHEN o.ts_event >= ? AND o.ts_event < ? THEN 1 ELSE 0 END),
            SUM(CASE WHEN o.ts_event >= ? AND o.ts_event < ? THEN 1 ELSE 0 END),
            SUM(CASE WHEN o.ts_event >= ? AND o.ts_event <= ? THEN 1 ELSE 0 END)
        FROM ohlcv o
        JOIN instruments i ON i.instrument_id = o.instrument_id
        JOIN symbology s
          ON s.publisher_ref = i.publisher_ref
         AND s.source_instrument_id = i.source_instrument_id
         AND date(o.ts_event / 1000000000, 'unixepoch') >= s.start_date
         AND date(o.ts_event / 1000000000, 'unixepoch') < s.end_date
        WHERE i.publisher_ref = ?
          AND s.symbol_type = ?
          AND s.symbol IN ({placeholders})
          AND o.rtype = ?
          AND o.ts_event >= ?
          AND o.ts_event <= ?
    """
    params: list = [
        # SUM boundaries: train, dev, test
        start_ns,
        train_end_ns,
        train_end_ns,
        dev_end_ns,
        dev_end_ns,
        end_ns,
        # WHERE clause
        publisher_id,
        symbol_type,
        *symbols,
        rtype,
        start_ns,
        end_ns,
    ]

    try:
        with connect_secmaster() as conn:
            row = conn.execute(query, params).fetchone()
        if row:
            return (row[0] or 0, row[1] or 0, row[2] or 0)
    except FileNotFoundError:
        pass
    return (0, 0, 0)


def _row_to_dict(row: tuple) -> dict:
    """Convert a database row (selected with _SPLIT_COLS) to a dict."""
    # Columns: 0=split_id, 1=name, 2=created_at, 3=publisher_id,
    # 4=publisher_name, 5=rtype, 6=symbols, 7=symbol_type,
    # 8=total_start, 9=total_end, 10=train_pct, 11=dev_pct,
    # 12=train_end, 13=dev_end, 14=train_bars, 15=dev_bars, 16=test_bars
    symbols = json.loads(row[6])
    created_at = row[2]
    return {
        "split_id": row[0],
        "name": row[1],
        "created_at": created_at,
        "publisher_id": row[3],
        "publisher_name": row[4],
        "rtype": row[5],
        "symbols": symbols,
        "symbol_type": row[7],
        "total_start": row[8],
        "total_end": row[9],
        "train_pct": row[10],
        "dev_pct": row[11],
        "train_end": row[12],
        "dev_end": row[13],
        "train_bars": row[14],
        "dev_bars": row[15],
        "test_bars": row[16],
        "sources": {
            "train": _source_name(symbols, "train", created_at),
            "dev": _source_name(symbols, "dev", created_at),
            "test": _source_name(symbols, "test", created_at),
        },
    }


def _backfill_bar_counts() -> None:
    """Backfill bar counts for splits that still have all-zero counts."""
    global _backfill_done
    if _backfill_done:
        return
    _backfill_done = True

    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {_SPLIT_COLS} FROM data_splits "
            "WHERE train_bars = 0 AND dev_bars = 0 AND test_bars = 0"
        )
        rows = cursor.fetchall()

    for row in rows:
        d = _row_to_dict(row)
        try:
            train_bars, dev_bars, test_bars = _count_bars_per_region(
                publisher_id=d["publisher_id"],
                rtype=d["rtype"],
                symbols=d["symbols"],
                symbol_type=d["symbol_type"],
                total_start=d["total_start"],
                train_end=d["train_end"],
                dev_end=d["dev_end"],
                total_end=d["total_end"],
            )
        except FileNotFoundError:
            continue
        if train_bars == 0 and dev_bars == 0 and test_bars == 0:
            continue
        with connect_presets() as conn:
            conn.execute(
                "UPDATE data_splits SET train_bars = ?, dev_bars = ?, test_bars = ? "
                "WHERE split_id = ?",
                (train_bars, dev_bars, test_bars, d["split_id"]),
            )
            conn.commit()


@router.get("")
async def list_splits() -> dict:
    """List all splits."""
    _backfill_bar_counts()
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {_SPLIT_COLS} FROM data_splits ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
    splits = [_row_to_dict(row) for row in rows]
    return {"splits": splits}


@router.post("")
async def create_split(request: SplitCreateRequest) -> dict:
    """Create a new data split."""
    if request.train_pct + request.dev_pct > 100:
        raise HTTPException(400, "train_pct + dev_pct cannot exceed 100")
    if request.train_pct < 1 or request.dev_pct < 1:
        raise HTTPException(400, "train_pct and dev_pct must be at least 1")
    test_pct = 100 - request.train_pct - request.dev_pct
    if test_pct < 1:
        raise HTTPException(400, "test_pct must be at least 1")

    train_end, dev_end = _compute_date_boundaries(
        request.total_start,
        request.total_end,
        request.train_pct,
        request.dev_pct,
    )

    train_bars, dev_bars, test_bars = _count_bars_per_region(
        publisher_id=request.publisher_id,
        rtype=request.rtype,
        symbols=request.symbols,
        symbol_type=request.symbol_type,
        total_start=request.total_start,
        train_end=train_end,
        dev_end=dev_end,
        total_end=request.total_end,
    )

    split_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    name = _make_split_name(request.symbols, now)
    symbols_json = json.dumps(request.symbols)

    with connect_presets() as conn:
        conn.execute(
            "INSERT INTO data_splits "
            "(split_id, name, created_at, publisher_id, publisher_name, rtype, "
            "symbols, symbol_type, total_start, total_end, train_pct, dev_pct, "
            "train_end, dev_end, train_bars, dev_bars, test_bars) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                split_id,
                name,
                now,
                request.publisher_id,
                request.publisher_name,
                request.rtype,
                symbols_json,
                request.symbol_type,
                request.total_start,
                request.total_end,
                request.train_pct,
                request.dev_pct,
                train_end,
                dev_end,
                train_bars,
                dev_bars,
                test_bars,
            ),
        )
        conn.commit()

    return {
        "split_id": split_id,
        "name": name,
        "train_end": train_end,
        "dev_end": dev_end,
    }


@router.get("/sources")
async def list_split_sources() -> list[dict]:
    """Flat list of all split-derived sources for data source pickers."""
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT {_SPLIT_COLS} FROM data_splits ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()

    sources = []
    for row in rows:
        d = _row_to_dict(row)
        regions = [
            ("train", d["total_start"], d["train_end"]),
            ("dev", d["train_end"], d["dev_end"]),
            ("test", d["dev_end"], d["total_end"]),
        ]
        for region, start, end in regions:
            sources.append(
                {
                    "source_name": _source_name(d["symbols"], region, d["created_at"]),
                    "split_id": d["split_id"],
                    "split_name": d["name"],
                    "region": region,
                    "publisher_id": d["publisher_id"],
                    "publisher_name": d["publisher_name"],
                    "rtype": d["rtype"],
                    "symbols": d["symbols"],
                    "symbol_type": d["symbol_type"],
                    "start_date": start,
                    "end_date": end,
                }
            )

    return sources


@router.delete("/{split_id}")
async def delete_split(split_id: str) -> dict:
    """Delete a split."""
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM data_splits WHERE split_id = ?", (split_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(404, "Split not found")
    return {"status": "deleted"}
