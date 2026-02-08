"""
Chart settings management for the dashboard.

Reads and writes per-run chart display settings from
``~/.onesecondtrader/chart_settings.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from .db import connect_presets

SETTINGS_PATH = Path.home() / ".onesecondtrader" / "chart_settings.json"

VALID_STYLES = {
    "line",
    "histogram",
    "dots",
    "dash1",
    "dash2",
    "dash3",
    "background1",
    "background2",
}
VALID_COLORS = {
    "black",
    "red",
    "blue",
    "green",
    "orange",
    "purple",
    "cyan",
    "magenta",
    "yellow",
    "teal",
}
VALID_WIDTHS = {"thin", "normal", "thick", "extra_thick"}

# Auto-cycling color palette for new indicators without saved settings
DEFAULT_COLOR_CYCLE = [
    "blue",
    "red",
    "green",
    "orange",
    "purple",
    "cyan",
    "magenta",
    "teal",
    "black",
    "yellow",
]


def _read_all() -> dict:
    """Read the entire settings file, returning empty dict on failure."""
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_all(data: dict) -> None:
    """Write the entire settings file, creating parent dirs as needed."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_chart_settings(run_id: str) -> dict:
    """
    Load chart settings for a run.

    Returns:
        Settings dict for the run, or empty dict if none exist.
    """
    all_settings = _read_all()
    return all_settings.get(run_id, {})


def save_chart_settings(run_id: str, settings: dict) -> None:
    """
    Save chart settings for a run.

    Parameters:
        run_id:
            Unique identifier of the backtest run.
        settings:
            Chart settings dict to persist.
    """
    all_settings = _read_all()
    all_settings[run_id] = settings
    _write_all(all_settings)


# ── Per-indicator global defaults (stored in presets.db) ──

_GLOBAL_KEY = "__global__"


def ensure_indicator_defaults_table() -> None:
    with connect_presets() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS indicator_defaults "
            "(name TEXT PRIMARY KEY, config TEXT NOT NULL)"
        )
        conn.commit()


def load_indicator_defaults() -> dict:
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, config FROM indicator_defaults")
        rows = cursor.fetchall()
    result: dict = {"indicators": {}}
    for name, config_json in rows:
        cfg = json.loads(config_json)
        if name == _GLOBAL_KEY:
            result.update(cfg)
        else:
            result["indicators"][name] = cfg
    return result


def save_indicator_default(name: str, settings: dict) -> None:
    with connect_presets() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO indicator_defaults (name, config) VALUES (?, ?)",
            (name, json.dumps(settings)),
        )
        conn.commit()


def save_global_defaults(
    chart_type: str | None = None, overlap: int | None = None
) -> None:
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT config FROM indicator_defaults WHERE name = ?", (_GLOBAL_KEY,)
        )
        row = cursor.fetchone()
        data = json.loads(row[0]) if row else {}
        if chart_type is not None:
            data["chart_type"] = chart_type
        if overlap is not None:
            data["overlap"] = overlap
        conn.execute(
            "INSERT OR REPLACE INTO indicator_defaults (name, config) VALUES (?, ?)",
            (_GLOBAL_KEY, json.dumps(data)),
        )
        conn.commit()
