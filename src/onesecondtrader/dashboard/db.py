"""
Database access utilities for the dashboard.

Provides functions for accessing the runs database and security master database,
including path resolution from environment variables and common query operations.
"""

from __future__ import annotations

import json
import os
import sqlite3


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


def get_runs(limit: int = 50) -> list[dict]:
    """
    Fetch recent runs from the runs database.

    Parameters:
        limit:
            Maximum number of runs to return.

    Returns:
        List of run dictionaries with run_id, name, timestamps, status, config, and metadata.
    """
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
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
    conn.close()
    runs = []
    for row in rows:
        config = json.loads(row[5]) if row[5] else None
        metadata = json.loads(row[6]) if row[6] else None
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
