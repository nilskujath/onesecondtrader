"""
API endpoints for symbol preset management.

Provides CRUD endpoints for managing saved symbol presets in the security master database.
"""

from __future__ import annotations

import json
import os
import sqlite3

from fastapi import APIRouter
from pydantic import BaseModel

from ..db import get_secmaster_path

router = APIRouter(prefix="/api/presets", tags=["presets"])


def ensure_presets_table() -> None:
    """Create the symbol_presets table if it does not already exist."""
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
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
    conn.close()


@router.get("")
async def list_presets() -> dict:
    """Return list of all preset objects."""
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        return {"presets": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, rtype, publisher_name, publisher_id, symbols "
        "FROM symbol_presets ORDER BY name"
    )
    rows = cursor.fetchall()
    conn.close()
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
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        return {"error": "Preset not found"}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, rtype, publisher_name, publisher_id, symbols "
        "FROM symbol_presets WHERE name = ?",
        (name,),
    )
    row = cursor.fetchone()
    conn.close()
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
    db_path = get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
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
    conn.close()
    return {"status": "created", "name": request.name}


@router.put("/{name}")
async def update_preset(name: str, request: PresetRequest) -> dict:
    """Update an existing symbol preset."""
    db_path = get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
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
    conn.close()
    return {"status": "updated", "name": name}


@router.delete("/{name}")
async def delete_preset(name: str) -> dict:
    """Delete a symbol preset."""
    db_path = get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM symbol_presets WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "name": name}
