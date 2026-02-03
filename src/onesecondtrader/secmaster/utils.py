from __future__ import annotations

import json
import logging
import pathlib
import shutil
import sqlite3
import tempfile
import zipfile

import databento


BATCH_SIZE = 10000
LOG_EVERY_OHLCV = 1_000_000
LOG_EVERY_SYMBOLOGY = 50_000

logger = logging.getLogger(__name__)


def create_secmaster_db(db_path: pathlib.Path, schema_version: int = 1) -> pathlib.Path:
    """
    Create a new security master SQLite database using a selected schema version.

    The database file is created at the given path and initialized by executing the SQL script
    located in the `schema_versions` directory adjacent to this module.

    The function expects the schema script to set `PRAGMA user_version` to the corresponding
    schema version and verifies this after execution.

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
            If the applied schema does not set the expected `user_version` or if SQLite fails
            while executing the schema.
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
                f"Schema script set user_version={actual_version}, expected {schema_version}"
            )

    return db_path


def ingest_databento_zip(
    zip_path: pathlib.Path,
    db_path: pathlib.Path,
    publisher_name: str = "databento",
    symbol_type: str = "raw_symbol",
    dataset: str | None = None,
) -> tuple[int, int]:
    """
    Ingest market data from a Databento zip archive into the security master database.

    The archive may contain one or more DBN files and an optional `symbology.json`. The function
    ingests OHLCV records from DBN files into `ohlcv` and ingests symbol-to-instrument mappings
    into `symbology`.

    The publisher namespace is created if absent. Publisher identity is determined by the pair
    `(publisher_name, dataset)`, where `dataset` is extracted from `metadata.json` in the archive.

    Ingestion is idempotent with respect to primary keys: existing `ohlcv` and `symbology` rows are
    left unchanged.

    Parameters:
        zip_path:
            Path to the Databento zip archive.
        db_path:
            Path to the security master SQLite database.
        publisher_name:
            Vendor name stored in `publishers.name`. The dataset is derived from archive metadata.
        symbol_type:
            Symbol scheme stored in `symbology.symbol_type` for symbols found in `symbology.json`.
        dataset:
            Optional dataset override. If provided, it is used when `metadata.json` is missing or
            does not specify a dataset.

    Returns:
        A tuple of (ohlcv_record_count_seen, symbology_record_count_seen).
    """
    ohlcv_count = 0
    symbology_count = 0

    logger.info("Opening Databento archive: %s", zip_path)

    if not db_path.is_file():
        raise FileNotFoundError(f"Security master DB not found: {db_path}")

    con = sqlite3.connect(str(db_path))

    try:
        con.execute("PRAGMA foreign_keys = ON;")
        _assert_secmaster_db(con)
        _enable_bulk_loading(con)

        with con:
            with zipfile.ZipFile(zip_path, "r") as zf:
                dataset, venue = _extract_dataset_info(zf, dataset_override=dataset)
                logger.info(
                    "Publisher resolved: name=%s dataset=%s venue=%s",
                    publisher_name,
                    dataset,
                    venue,
                )
                publisher_id = _get_or_create_publisher(
                    con, publisher_name, dataset, venue
                )

                with tempfile.TemporaryDirectory() as tmpdir:
                    dbn_files = [
                        n
                        for n in zf.namelist()
                        if n.endswith(".dbn.zst") or n.endswith(".dbn")
                    ]
                    symbology_member = _zip_find_member(zf, "symbology.json")

                    if not dbn_files and symbology_member is None:
                        raise ValueError(
                            "Archive contains no DBN files and no symbology.json"
                        )

                    logger.info("Found %d DBN file(s) in archive", len(dbn_files))

                    for name in dbn_files:
                        extracted_path = _zip_member_to_tempfile(zf, name, tmpdir)
                        try:
                            logger.info("Ingesting DBN file: %s", extracted_path.name)
                            ohlcv_count += _ingest_dbn(
                                extracted_path, con, publisher_id
                            )
                        finally:
                            try:
                                extracted_path.unlink()
                            except FileNotFoundError:
                                pass

                    if symbology_member is not None:
                        symbology_path = _zip_member_to_tempfile(
                            zf, symbology_member, tmpdir
                        )
                        try:
                            logger.info("Ingesting symbology.json")
                            symbology_count += _ingest_symbology(
                                symbology_path,
                                con,
                                publisher_id,
                                symbol_type=symbol_type,
                            )
                        finally:
                            try:
                                symbology_path.unlink()
                            except FileNotFoundError:
                                pass
                    else:
                        logger.info("No symbology.json present in archive")
    finally:
        try:
            _disable_bulk_loading(con)
        finally:
            con.close()

    logger.info(
        "Finished zip ingestion: %s (%d OHLCV records, %d symbology records)",
        zip_path.name,
        ohlcv_count,
        symbology_count,
    )

    return ohlcv_count, symbology_count


def ingest_databento_dbn(
    dbn_path: pathlib.Path,
    db_path: pathlib.Path,
    publisher_name: str = "databento",
) -> int:
    """
    Ingest market data from a Databento DBN file into the security master database.

    Reads OHLCV records from the DBN file and inserts them into `ohlcv`. The publisher namespace
    is created if absent. Publisher identity is determined by the pair `(publisher_name, dataset)`,
    where `dataset` is read from DBN metadata.

    Ingestion is idempotent with respect to primary keys: existing bars are left unchanged.

    Parameters:
        dbn_path:
            Path to the DBN file (.dbn or .dbn.zst).
        db_path:
            Path to the security master SQLite database.
        publisher_name:
            Vendor name stored in `publishers.name`. The dataset is derived from DBN metadata.

    Returns:
        The number of OHLCV records seen in the DBN stream.
    """
    logger.info("Starting DBN ingestion: %s", dbn_path)

    if not db_path.is_file():
        raise FileNotFoundError(f"Security master DB not found: {db_path}")

    con = sqlite3.connect(str(db_path))

    try:
        con.execute("PRAGMA foreign_keys = ON;")
        _assert_secmaster_db(con)
        _enable_bulk_loading(con)

        with con:
            store = databento.DBNStore.from_file(dbn_path)
            dataset = store.metadata.dataset
            if not dataset:
                raise ValueError(f"DBN metadata missing dataset: {dbn_path}")
            venue = dataset.split(".")[0] if "." in dataset else None

            logger.info(
                "Publisher resolved: name=%s dataset=%s venue=%s",
                publisher_name,
                dataset,
                venue,
            )

            publisher_id = _get_or_create_publisher(con, publisher_name, dataset, venue)
            count = _ingest_dbn(dbn_path, con, publisher_id)
    finally:
        try:
            _disable_bulk_loading(con)
        finally:
            con.close()

    logger.info("Finished DBN ingestion: %s (%d OHLCV records)", dbn_path.name, count)

    return count


def _extract_dataset_info(
    zf: zipfile.ZipFile,
    dataset_override: str | None = None,
) -> tuple[str, str | None]:
    metadata_member = _zip_find_member(zf, "metadata.json")
    if metadata_member is None:
        if dataset_override is None:
            raise ValueError(
                "Archive is missing metadata.json and no dataset override was provided"
            )
        dataset = dataset_override
    else:
        with zf.open(metadata_member) as f:
            metadata = json.load(f)
        dataset = metadata.get("query", {}).get("dataset")
        if not dataset:
            if dataset_override is None:
                raise ValueError(
                    f"metadata.json is missing query.dataset (member={metadata_member!r})"
                )
            dataset = dataset_override

    venue = dataset.split(".")[0] if "." in dataset else None
    return dataset, venue


def _zip_find_member(
    zf: zipfile.ZipFile,
    basename: str,
    allow_multiple: bool = False,
) -> str | None:
    candidates = [
        name
        for name in zf.namelist()
        if name == basename or name.endswith("/" + basename)
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    candidates = sorted(candidates)
    if not allow_multiple:
        raise ValueError(f"Multiple {basename} members found in archive: {candidates}")

    selected = candidates[0]
    logger.warning("Multiple %s found in archive; using %s", basename, selected)
    return selected


def _zip_member_to_tempfile(
    zf: zipfile.ZipFile,
    member_name: str,
    tmpdir: str,
) -> pathlib.Path:
    suffix = "".join(pathlib.PurePosixPath(member_name).suffixes)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        suffix=suffix,
        delete=False,
        dir=tmpdir,
    ) as tmp:
        with zf.open(member_name) as src:
            shutil.copyfileobj(src, tmp)
        return pathlib.Path(tmp.name)


def _get_or_create_publisher(
    con: sqlite3.Connection,
    name: str,
    dataset: str,
    venue: str | None,
) -> int:
    cursor = con.cursor()
    cursor.execute(
        "SELECT publisher_id FROM publishers WHERE name = ? AND dataset = ?",
        (name, dataset),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO publishers (name, dataset, venue) VALUES (?, ?, ?)",
        (name, dataset, venue),
    )
    return cursor.lastrowid  # type: ignore[return-value]


def _get_or_create_instrument(
    con: sqlite3.Connection,
    publisher_id: int,
    source_instrument_id: int,
) -> int:
    cursor = con.cursor()
    cursor.execute(
        "SELECT instrument_id FROM instruments WHERE publisher_ref = ? AND source_instrument_id = ?",
        (publisher_id, source_instrument_id),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO instruments (publisher_ref, source_instrument_id) VALUES (?, ?)",
        (publisher_id, source_instrument_id),
    )
    return cursor.lastrowid  # type: ignore[return-value]


def _assert_secmaster_db(
    con: sqlite3.Connection, expected_user_version: int = 1
) -> None:
    row = con.execute("PRAGMA user_version;").fetchone()
    user_version = int(row[0]) if row else 0
    if user_version != expected_user_version:
        raise sqlite3.DatabaseError(
            "Security master schema user_version="
            f"{user_version} does not match expected {expected_user_version}"
        )

    required = {"publishers", "instruments", "ohlcv", "symbology"}
    present = {
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing = sorted(required - present)
    if missing:
        raise sqlite3.DatabaseError(
            f"Security master schema missing required tables: {', '.join(missing)}"
        )


def _ingest_dbn(
    dbn_path: pathlib.Path,
    con: sqlite3.Connection,
    publisher_id: int,
) -> int:
    store = databento.DBNStore.from_file(dbn_path)
    cursor = con.cursor()

    instrument_cache: dict[int, int] = {}
    batch: list[tuple] = []
    count = 0

    logger.info("Streaming OHLCV records from: %s", dbn_path.name)

    for record in store:
        if not isinstance(record, databento.OHLCVMsg):
            continue

        source_id = record.instrument_id
        if source_id not in instrument_cache:
            instrument_cache[source_id] = _get_or_create_instrument(
                con, publisher_id, source_id
            )
        internal_id = instrument_cache[source_id]

        rtype_val = (
            record.rtype.value if hasattr(record.rtype, "value") else record.rtype
        )

        batch.append(
            (
                internal_id,
                rtype_val,
                record.ts_event,
                record.open,
                record.high,
                record.low,
                record.close,
                record.volume,
            )
        )
        count += 1

        if count % LOG_EVERY_OHLCV == 0:
            logger.info("Ingested %d OHLCV records from %s", count, dbn_path.name)

        if len(batch) >= BATCH_SIZE:
            cursor.executemany(
                "INSERT OR IGNORE INTO ohlcv "
                "(instrument_id, rtype, ts_event, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            batch.clear()

    if batch:
        cursor.executemany(
            "INSERT OR IGNORE INTO ohlcv "
            "(instrument_id, rtype, ts_event, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            batch,
        )

    logger.info("Completed OHLCV ingest from %s (%d records)", dbn_path.name, count)

    return count


def _ingest_symbology(
    json_path: pathlib.Path,
    con: sqlite3.Connection,
    publisher_id: int,
    symbol_type: str = "raw_symbol",
) -> int:
    if not isinstance(symbol_type, str) or not symbol_type:
        raise ValueError("symbol_type must be a non-empty string")

    with open(json_path, "r") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("symbology.json root must be a JSON object")

    result = data.get("result", {})
    if not isinstance(result, dict):
        raise ValueError("symbology.json['result'] must be an object")
    cursor = con.cursor()

    batch: list[tuple] = []
    count = 0

    logger.info("Streaming symbology mappings from: %s", json_path.name)

    instrument_cache: set[int] = set()

    for symbol, mappings in result.items():
        if not isinstance(mappings, list):
            raise ValueError(
                f"symbology.json mappings must be a list for symbol={symbol!r}"
            )

        for i, mapping in enumerate(mappings):
            if not isinstance(mapping, dict):
                raise ValueError(
                    f"symbology.json mapping must be an object at symbol={symbol!r} index={i}"
                )

            missing_keys = [k for k in ("s", "d0", "d1") if k not in mapping]
            if missing_keys:
                raise ValueError(
                    "symbology.json mapping missing key(s) "
                    f"{missing_keys} at symbol={symbol!r} index={i}"
                )

            source_id = int(mapping["s"])

            if source_id not in instrument_cache:
                _get_or_create_instrument(con, publisher_id, source_id)
                instrument_cache.add(source_id)

            batch.append(
                (
                    publisher_id,
                    symbol,
                    symbol_type,
                    source_id,
                    mapping["d0"],
                    mapping["d1"],
                )
            )
            count += 1

            if count % LOG_EVERY_SYMBOLOGY == 0:
                logger.info(
                    "Ingested %d symbology mappings from %s", count, json_path.name
                )

            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR IGNORE INTO symbology "
                    "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    batch,
                )
                batch.clear()

    if batch:
        cursor.executemany(
            "INSERT OR IGNORE INTO symbology "
            "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            batch,
        )

    logger.info(
        "Completed symbology ingest from %s (%d mappings)", json_path.name, count
    )

    return count


def _enable_bulk_loading(con: sqlite3.Connection) -> None:
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA synchronous = NORMAL")
    con.execute("PRAGMA cache_size = -64000")


def _disable_bulk_loading(con: sqlite3.Connection) -> None:
    con.execute("PRAGMA synchronous = FULL")
    con.execute("PRAGMA journal_mode = DELETE")
    con.execute("PRAGMA cache_size = -2000")
