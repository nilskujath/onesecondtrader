"""
API endpoints for strategy discovery and schema retrieval.

Provides endpoints for listing available strategies and retrieving their parameter schemas.
"""

from __future__ import annotations

from fastapi import APIRouter

from .. import registry

router = APIRouter(prefix="/api", tags=["strategies"])


@router.get("/strategies")
async def api_strategies() -> dict:
    """Return list of available strategy classes."""
    strategies = registry.get_strategies()
    return {
        "strategies": [
            {"id": name, "name": cls.name} for name, cls in strategies.items()
        ]
    }


@router.get("/strategies/{name}")
async def api_strategy_schema(name: str) -> dict:
    """Return parameter schema for a specific strategy."""
    schema = registry.get_strategy_schema(name)
    if schema is None:
        return {"error": "Strategy not found"}
    return schema
