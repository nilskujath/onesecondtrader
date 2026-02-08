"""
Dashboard-specific utilities for indicator discovery and registration lookup.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def get_registered_indicators() -> dict[str, type]:
    """
    Return all registered indicator classes.

    Returns:
        Dictionary mapping indicator class names to their class objects.
    """
    from onesecondtrader.indicators.base import _indicator_registry

    return dict(_indicator_registry)


def discover_indicators(directory: str | Path = "indicators") -> list[str]:
    """
    Import all Python files from a directory to register indicators.

    Any class inheriting from IndicatorBase in the imported files will be
    automatically registered via __init_subclass__.

    Parameters:
        directory:
            Path to the directory containing indicator files.
            Defaults to "indicators" relative to the current working directory.

    Returns:
        List of successfully imported module names.
    """
    import sys
    import types

    path = Path(directory)
    if not path.is_dir():
        return []

    if "indicators" not in sys.modules:
        sys.modules["indicators"] = types.ModuleType("indicators")

    imported = []
    for file in path.glob("*.py"):
        if file.name.startswith("_"):
            continue

        module_name = f"indicators.{file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            imported.append(file.stem)
        except Exception:
            del sys.modules[module_name]

    return imported
