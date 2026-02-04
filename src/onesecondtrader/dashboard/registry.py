"""
Strategy discovery and parameter schema extraction.

Provides utilities for discovering registered strategy classes and extracting their
parameter specifications into JSON-serializable schemas for the dashboard UI.
"""

from __future__ import annotations

import enum

from onesecondtrader.strategies.base import StrategyBase, ParamSpec


def _get_subclasses(base: type) -> dict[str, type]:
    """
    Recursively collect all non-private subclasses of a base class.

    Excludes classes with names starting with underscore or "Configured" (dynamically
    created strategy configurations).

    Parameters:
        base:
            Base class to find subclasses of.

    Returns:
        Dictionary mapping class names to class objects.
    """
    result = {}
    for cls in base.__subclasses__():
        if not cls.__name__.startswith("_") and not cls.__name__.startswith(
            "Configured"
        ):
            result[cls.__name__] = cls
        result.update(_get_subclasses(cls))
    return result


def get_strategies() -> dict[str, type[StrategyBase]]:
    """
    Get all registered strategy classes.

    Returns:
        Dictionary mapping strategy class names to their class objects.
    """
    return _get_subclasses(StrategyBase)


def get_param_schema(params: dict[str, ParamSpec]) -> list[dict]:
    """
    Convert strategy parameter specifications to a JSON-serializable schema.

    Parameters:
        params:
            Dictionary mapping parameter names to their specifications.

    Returns:
        List of parameter schema dictionaries with keys: name, default, type,
        and optionally min, max, step, choices.
    """
    schema: list[dict] = []
    for name, spec in params.items():
        param_info: dict = {
            "name": name,
            "default": _serialize_value(spec.default),
            "type": _get_type_name(spec.default),
        }
        if spec.min is not None:
            param_info["min"] = spec.min
        if spec.max is not None:
            param_info["max"] = spec.max
        if spec.step is not None:
            param_info["step"] = spec.step
        choices = spec.resolved_choices
        if choices is not None:
            param_info["choices"] = [_serialize_value(c) for c in choices]
        schema.append(param_info)
    return schema


def _serialize_value(value: object) -> str | int | float | bool:
    """
    Serialize a parameter value for JSON output.

    Enum values are converted to their name strings.

    Parameters:
        value:
            Value to serialize.

    Returns:
        JSON-serializable representation of the value.
    """
    if isinstance(value, enum.Enum):
        return value.name
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return value
    return str(value)


def _get_type_name(value: object) -> str:
    """
    Determine the type name for a parameter value.

    Parameters:
        value:
            Value to determine type of.

    Returns:
        Type name string: enum, bool, int, float, str, or unknown.
    """
    if isinstance(value, enum.Enum):
        return "enum"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return "unknown"


def get_strategy_schema(name: str) -> dict | None:
    """
    Get the full schema for a strategy by name.

    Parameters:
        name:
            Class name of the strategy.

    Returns:
        Dictionary with strategy name and parameter schema, or None if not found.
    """
    cls = get_strategies().get(name)
    if cls is None:
        return None
    return {
        "name": name,
        "parameters": get_param_schema(getattr(cls, "parameters", {})),
    }
