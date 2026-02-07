"""
Chart settings management for the dashboard.

Reads and writes per-run chart display settings from
``~/.onesecondtrader/chart_settings.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

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
