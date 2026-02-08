"""Factory for name+config preset CRUD routers.

Provides ``create_preset_routes`` which generates a FastAPI router with
standard CRUD endpoints (list, create, update, delete) for any table
that uses the ``(name TEXT PRIMARY KEY, config TEXT NOT NULL)`` schema.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable

from fastapi import APIRouter
from pydantic import BaseModel

from .db import connect_presets


class _PresetRequest(BaseModel):
    name: str
    config: dict


def create_preset_routes(
    table_name: str,
    prefix: str,
    tag: str,
) -> tuple[APIRouter, Callable[[], None]]:
    """Return ``(router, ensure_table_fn)`` for a name+config preset table.

    Parameters:
        table_name: SQLite table name (e.g. ``"explore_presets"``).
        prefix:     URL prefix for the router (e.g. ``"/api/explore/presets"``).
        tag:        OpenAPI tag for the endpoints.
    """
    router = APIRouter(prefix=prefix, tags=[tag])

    def ensure_table() -> None:
        with connect_presets() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(name TEXT PRIMARY KEY, config TEXT NOT NULL)"
            )
            conn.commit()

    @router.get("")
    async def list_presets() -> dict:
        with connect_presets() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(f"SELECT name, config FROM {table_name} ORDER BY name")
            rows = cursor.fetchall()
        return {
            "presets": [
                {"name": row["name"], "config": json.loads(row["config"])}
                for row in rows
            ]
        }

    @router.post("")
    async def create_preset(request: _PresetRequest) -> dict:
        with connect_presets() as conn:
            conn.execute(
                f"INSERT INTO {table_name} (name, config) VALUES (?, ?)",
                (request.name, json.dumps(request.config)),
            )
            conn.commit()
        return {"status": "created", "name": request.name}

    @router.put("/{name}")
    async def update_preset(name: str, request: _PresetRequest) -> dict:
        with connect_presets() as conn:
            conn.execute(
                f"UPDATE {table_name} SET config = ? WHERE name = ?",
                (json.dumps(request.config), name),
            )
            conn.commit()
        return {"status": "updated", "name": name}

    @router.delete("/{name}")
    async def delete_preset(name: str) -> dict:
        with connect_presets() as conn:
            conn.execute(f"DELETE FROM {table_name} WHERE name = ?", (name,))
            conn.commit()
        return {"status": "deleted", "name": name}

    return router, ensure_table
