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


@router.get("")
async def list_presets() -> dict:
    """Return list of all preset names."""
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        return {"presets": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM symbol_presets ORDER BY name")
    presets = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"presets": presets}


@router.get("/{name}")
async def get_preset(name: str) -> dict:
    """Return symbols for a specific preset."""
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        return {"error": "Preset not found"}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT symbols FROM symbol_presets WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return {"error": "Preset not found"}
    return {"name": name, "symbols": json.loads(row[0])}


class PresetRequest(BaseModel):
    """
    Request model for creating or updating a preset.

    Attributes:
        name:
            Name of the preset.
        symbols:
            List of symbol strings in the preset.
    """

    name: str
    symbols: list[str]


@router.post("")
async def create_preset(request: PresetRequest) -> dict:
    """Create a new symbol preset."""
    db_path = get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO symbol_presets (name, symbols) VALUES (?, ?)",
        (request.name, json.dumps(request.symbols)),
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
        "UPDATE symbol_presets SET symbols = ? WHERE name = ?",
        (json.dumps(request.symbols), name),
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
