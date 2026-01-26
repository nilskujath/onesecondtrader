from __future__ import annotations

import pathlib
import sqlite3


def init_secmaster(db_path: pathlib.Path) -> None:
    """Initialize a new secmaster database at the specified path.

    Creates the database file with the secmaster schema (publishers, instruments,
    and ohlcv tables) but does not populate any data.

    Args:
        db_path: Path where the database file will be created.

    Raises:
        FileExistsError: If a database already exists at the path.
    """
    if db_path.exists():
        raise FileExistsError(f"Database already exists: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema_path.read_text())
    conn.commit()
    conn.close()
