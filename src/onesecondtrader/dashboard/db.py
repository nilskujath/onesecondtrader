"""
Database access utilities for the dashboard.

Provides functions for accessing the runs database and security master database,
including path resolution from environment variables and common query operations.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
from collections.abc import Generator


def get_runs_db_path() -> str:
    """
    Return the path to the runs database from environment or default.

    Returns:
        Path to the runs SQLite database file.
    """
    return os.environ.get("RUNS_DB_PATH", "runs.db")


def get_secmaster_path() -> str:
    """
    Return the path to the security master database from environment or default.

    Returns:
        Path to the security master SQLite database file.
    """
    return os.environ.get("SECMASTER_DB_PATH", "secmaster.db")


@contextlib.contextmanager
def connect_runs(
    *,
    timeout: float = 5.0,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for connecting to the runs database.

    Yields a connection that is automatically closed on exit (even on exceptions).
    Raises ``FileNotFoundError`` when the database file does not exist.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


@contextlib.contextmanager
def connect_secmaster(
    *,
    timeout: float = 5.0,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for connecting to the security master database.

    Yields a connection that is automatically closed on exit (even on exceptions).
    Raises ``FileNotFoundError`` when the database file does not exist.
    """
    db_path = get_secmaster_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn = sqlite3.connect(db_path, timeout=timeout)
    try:
        yield conn
    finally:
        conn.close()


def get_runs(limit: int = 50) -> list[dict]:
    """
    Fetch recent runs from the runs database.

    Parameters:
        limit:
            Maximum number of runs to return.

    Returns:
        List of run dictionaries with run_id, name, timestamps, status, config, and metadata.
    """
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return []
    with conn_ctx as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT run_id, name, ts_start, ts_end, status, config, metadata
            FROM runs
            ORDER BY ts_start DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
    runs = []
    for row in rows:
        config = json.loads(row[5]) if row[5] else None
        metadata = json.loads(row[6]) if row[6] else None
        # Filter out exploration runs from normal run lists
        if isinstance(config, dict) and config.get("mode") == "exploration":
            continue
        runs.append(
            {
                "run_id": row[0],
                "name": row[1],
                "ts_start": row[2],
                "ts_end": row[3],
                "status": row[4],
                "config": config,
                "metadata": metadata,
            }
        )
    return runs


def get_strategy_key(run_id: str) -> str:
    """Derive a strategy class key from a run's config for settings persistence.

    Queries the runs table, extracts ``config["strategies"]``, and returns
    a deterministic comma-joined sorted string.  Falls back to *run_id*
    when no strategies list is found.
    """
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return run_id
    try:
        with conn_ctx as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT config FROM runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
        if row and row[0]:
            config = json.loads(row[0])
            if config.get("mode") == "exploration":
                indicators = config.get("indicators", [])
                parts = []
                for ind in sorted(indicators, key=lambda x: x.get("class_name", "")):
                    name = ind.get("class_name", "")
                    params = ind.get("params", {})
                    param_str = ",".join(f"{k}={v}" for k, v in sorted(params.items()))
                    parts.append(f"{name}({param_str})" if param_str else name)
                return "explore:" + ",".join(parts) if parts else run_id
            strategies = config.get("strategies")
            if strategies and isinstance(strategies, list):
                return ",".join(sorted(strategies))
    except Exception:
        pass
    return run_id


CHILD_TABLES = [
    "bars",
    "bars_processed",
    "order_submissions",
    "order_cancellations",
    "order_modifications",
    "orders_accepted",
    "orders_rejected",
    "cancellations_accepted",
    "cancellations_rejected",
    "modifications_accepted",
    "modifications_rejected",
    "fills",
    "expirations",
]
