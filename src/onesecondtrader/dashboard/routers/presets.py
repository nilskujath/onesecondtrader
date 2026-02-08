"""
API endpoints for symbol preset management.

Provides CRUD endpoints for managing saved symbol presets in the security master database.
"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import connect_presets

router = APIRouter(prefix="/api/presets", tags=["presets"])


def ensure_presets_table() -> None:
    """Create the symbol_presets table if it does not already exist."""
    with connect_presets() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS symbol_presets (
                name TEXT PRIMARY KEY,
                rtype INTEGER NOT NULL,
                publisher_name TEXT NOT NULL,
                publisher_id INTEGER NOT NULL,
                symbols TEXT NOT NULL
            )
            """
        )
        conn.commit()


@router.get("")
async def list_presets() -> dict:
    """Return list of all preset objects."""
    with connect_presets() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, rtype, publisher_name, publisher_id, symbols "
            "FROM symbol_presets ORDER BY name"
        )
        rows = cursor.fetchall()
    presets = [
        {
            "name": row["name"],
            "rtype": row["rtype"],
            "publisher_name": row["publisher_name"],
            "publisher_id": row["publisher_id"],
            "symbols": json.loads(row["symbols"]),
        }
        for row in rows
    ]
    return {"presets": presets}


@router.get("/{name}")
async def get_preset(name: str) -> dict:
    """Return all fields for a specific preset."""
    with connect_presets() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, rtype, publisher_name, publisher_id, symbols "
            "FROM symbol_presets WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
    if row is None:
        return {"error": "Preset not found"}
    return {
        "name": row["name"],
        "rtype": row["rtype"],
        "publisher_name": row["publisher_name"],
        "publisher_id": row["publisher_id"],
        "symbols": json.loads(row["symbols"]),
    }


class PresetRequest(BaseModel):
    """
    Request model for creating or updating a preset.

    Attributes:
        name:
            Name of the preset.
        rtype:
            Bar period rtype value.
        publisher_name:
            Name of the publisher.
        publisher_id:
            ID of the publisher dataset.
        symbols:
            List of symbol strings in the preset.
    """

    name: str
    rtype: int
    publisher_name: str
    publisher_id: int
    symbols: list[str]


@router.post("")
async def create_preset(request: PresetRequest) -> dict:
    """Create a new symbol preset."""
    with connect_presets() as conn:
        conn.execute(
            "INSERT INTO symbol_presets (name, rtype, publisher_name, publisher_id, symbols) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                request.name,
                request.rtype,
                request.publisher_name,
                request.publisher_id,
                json.dumps(request.symbols),
            ),
        )
        conn.commit()
    return {"status": "created", "name": request.name}


@router.put("/{name}")
async def update_preset(name: str, request: PresetRequest) -> dict:
    """Update an existing symbol preset."""
    with connect_presets() as conn:
        conn.execute(
            "UPDATE symbol_presets SET rtype = ?, publisher_name = ?, publisher_id = ?, "
            "symbols = ? WHERE name = ?",
            (
                request.rtype,
                request.publisher_name,
                request.publisher_id,
                json.dumps(request.symbols),
                name,
            ),
        )
        conn.commit()
    return {"status": "updated", "name": name}


@router.delete("/{name}")
async def delete_preset(name: str) -> dict:
    """Delete a symbol preset."""
    with connect_presets() as conn:
        conn.execute("DELETE FROM symbol_presets WHERE name = ?", (name,))
        conn.commit()
    return {"status": "deleted", "name": name}
