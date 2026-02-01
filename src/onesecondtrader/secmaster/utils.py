from __future__ import annotations

import pathlib
import sqlite3


def create_secmaster_db(db_path: pathlib.Path, schema_version: int = 1) -> pathlib.Path:
    """
    Create a new security master SQLite database using a selected schema version.

    The database file is created at the given path and initialized by executing the SQL script located in the `schema_versions` directory adjacent to this module.

    The function expects the schema script to set `PRAGMA user_version` to the corresponding schema version and verifies this after execution.

    Parameters:
        db_path:
            Filesystem path at which the SQLite database file will be created.
        schema_version:
            Version number selecting the schema script to apply.

    Returns:
        The path to the created database file.

    Raises:
        FileExistsError:
            If a file already exists at `db_path`.
        FileNotFoundError:
            If the schema script for `schema_version` does not exist.
        sqlite3.DatabaseError:
            If the applied schema does not set the expected `user_version`
            or if SQLite fails while executing the schema.
    """
    if db_path.exists():
        raise FileExistsError(f"Database already exists: {db_path}")

    schema_path = (
        pathlib.Path(__file__).resolve().parent
        / "schema_versions"
        / f"secmaster_schema_v{schema_version}.sql"
    )

    if not schema_path.is_file():
        raise FileNotFoundError(
            f"Schema version {schema_version} not found: {schema_path}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = schema_path.read_text(encoding="utf-8")

    with sqlite3.connect(str(db_path)) as con:
        con.execute("PRAGMA foreign_keys = ON;")
        con.executescript(schema_sql)

        row = con.execute("PRAGMA user_version;").fetchone()
        actual_version = int(row[0]) if row else 0

        if actual_version != schema_version:
            raise sqlite3.DatabaseError(
                f"Schema script set user_version={actual_version}, "
                f"expected {schema_version}"
            )

    return db_path
