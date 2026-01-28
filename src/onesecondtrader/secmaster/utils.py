from __future__ import annotations

import json
import pathlib
import sqlite3
import tempfile
import zipfile

import databento
from tqdm import tqdm


BATCH_SIZE = 10000


def create_secmaster_db(db_path: pathlib.Path) -> pathlib.Path:
    """
    Initialize a new secmaster database at the specified path.

    Creates the database file with the schema defined in ./schema.sql but does not
    populate any data.

    Args:
        db_path: Path where the database file will be created.

    Returns:
        The path where the database was created.

    Raises:
        FileExistsError: If a database already exists at the path.
    """

    if db_path.exists():
        raise FileExistsError(f"Database already exists: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(db_path))

    schema_path = pathlib.Path(__file__).parent / "schema.sql"
    connection.executescript(schema_path.read_text())

    connection.commit()
    connection.close()
    return db_path


def ingest_symbology(json_path: pathlib.Path, db_path: pathlib.Path) -> int:
    """
    Ingest symbology mappings from a Databento symbology.json file into the database.

    Parses the symbology.json file which maps ticker symbols to instrument IDs with
    date ranges, and inserts the mappings into the symbology table.

    Args:
        json_path: Path to the symbology.json file.
        db_path: Path to the secmaster SQLite database.

    Returns:
        The number of symbology records inserted.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        sqlite3.Error: If a database error occurs during ingestion.
    """
    connection = sqlite3.connect(str(db_path))
    _enable_bulk_loading(connection)
    try:
        count = _ingest_symbology_with_connection(json_path, connection)
        connection.commit()
    finally:
        _disable_bulk_loading(connection)
        connection.close()
    return count


def _ingest_symbology_with_connection(
    json_path: pathlib.Path, connection: sqlite3.Connection
) -> int:
    """
    Ingest symbology using an existing connection. Uses batch inserts for performance.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    result = data.get("result", {})
    cursor = connection.cursor()

    batch = []
    count = 0
    for symbol, mappings in result.items():
        for mapping in mappings:
            batch.append((symbol, int(mapping["s"]), mapping["d0"], mapping["d1"]))
            count += 1
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(
                    "INSERT OR REPLACE INTO symbology "
                    "(symbol, instrument_id, start_date, end_date) "
                    "VALUES (?, ?, ?, ?)",
                    batch,
                )
                batch.clear()

    if batch:
        cursor.executemany(
            "INSERT OR REPLACE INTO symbology "
            "(symbol, instrument_id, start_date, end_date) "
            "VALUES (?, ?, ?, ?)",
            batch,
        )

    return count


def _enable_bulk_loading(connection: sqlite3.Connection) -> None:
    """
    Configure SQLite for fast bulk loading.

    Disables safety features that slow down bulk inserts. The tradeoff is that if the
    process crashes or power fails during import, the database may be corrupted and
    need to be recreated. This is acceptable for bulk imports where the source data
    is preserved and the import can be re-run.

    Settings:
        - synchronous=OFF: Don't wait for disk writes to complete
        - journal_mode=OFF: Disable rollback journal (no crash recovery)
        - cache_size=-64000: Use 64MB of memory for cache (negative = KB)
    """
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA cache_size = -64000")


def _disable_bulk_loading(connection: sqlite3.Connection) -> None:
    """
    Restore SQLite to safe default settings after bulk loading.
    """
    connection.execute("PRAGMA synchronous = FULL")
    connection.execute("PRAGMA journal_mode = DELETE")
    connection.execute("PRAGMA cache_size = -2000")


def ingest_dbzip(zip_path: pathlib.Path, db_path: pathlib.Path) -> tuple[int, int]:
    """
    Ingest market data from a Databento zip archive into the secmaster database.

    Extracts all `.dbn.zst` files from the zip and ingests each one. Also ingests
    symbology.json if present in the archive.

    Uses optimized SQLite settings for fast bulk loading. These settings disable
    crash recovery, so if the import is interrupted, the database may need to be
    recreated. The source zip file is not modified.

    Args:
        zip_path: Path to the zip archive containing DBN files.
        db_path: Path to the secmaster SQLite database.

    Returns:
        A tuple of (dbn_record_count, symbology_record_count).
    """
    dbn_count = 0
    symbology_count = 0

    connection = sqlite3.connect(str(db_path))
    _enable_bulk_loading(connection)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            dbn_files = [
                n for n in namelist if n.endswith(".dbn.zst") or n.endswith(".dbn")
            ]
            with tempfile.TemporaryDirectory() as tmpdir:
                for name in tqdm(dbn_files, desc="Ingesting DBN files", unit="file"):
                    zf.extract(name, tmpdir)
                    extracted_path = pathlib.Path(tmpdir) / name
                    dbn_count += _ingest_dbn_with_connection(extracted_path, connection)

                if "symbology.json" in namelist:
                    zf.extract("symbology.json", tmpdir)
                    symbology_path = pathlib.Path(tmpdir) / "symbology.json"
                    symbology_count = _ingest_symbology_with_connection(
                        symbology_path, connection
                    )

        connection.commit()
    finally:
        _disable_bulk_loading(connection)
        connection.close()

    update_meta(db_path)
    update_symbol_coverage(db_path)
    return dbn_count, symbology_count


def ingest_dbn(dbn_path: pathlib.Path, db_path: pathlib.Path) -> int:
    """
    Ingest market data from a Databento Binary Encoding (DBN) file into the secmaster database.

    Reads records from the DBN file and inserts them into the appropriate tables based on
    their record type (rtype). Supports both uncompressed `.dbn` files and zstd-compressed
    `.dbn.zst` files.

    Args:
        dbn_path: Path to the DBN file to ingest.
        db_path: Path to the secmaster SQLite database.

    Returns:
        The number of records successfully ingested.

    Raises:
        FileNotFoundError: If the DBN file does not exist.
        sqlite3.Error: If a database error occurs during ingestion.
    """
    connection = sqlite3.connect(str(db_path))
    _enable_bulk_loading(connection)
    try:
        count = _ingest_dbn_with_connection(dbn_path, connection)
        connection.commit()
    finally:
        _disable_bulk_loading(connection)
        connection.close()
    update_meta(db_path)
    update_symbol_coverage(db_path)
    return count


def _ingest_dbn_with_connection(
    dbn_path: pathlib.Path, connection: sqlite3.Connection
) -> int:
    """
    Ingest DBN file using an existing connection. Uses batch inserts for performance.
    """
    store = databento.DBNStore.from_file(dbn_path)
    cursor = connection.cursor()

    batches: dict[str, list[tuple]] = {
        "ohlcv": [],
        "trades": [],
        "quotes": [],
        "bbo": [],
        "mbo": [],
        "mbp10": [],
        "imbalance": [],
        "statistics": [],
        "status": [],
        "instruments": [],
    }

    count = 0
    for record in store:
        match record:
            case databento.OHLCVMsg():
                batches["ohlcv"].append(_ohlcv_to_tuple(record))
            case databento.TradeMsg():
                batches["trades"].append(_trade_to_tuple(record))
            case databento.MBP1Msg():
                batches["quotes"].append(_quote_to_tuple(record))
            case databento.BBOMsg():
                batches["bbo"].append(_bbo_to_tuple(record))
            case databento.MBOMsg():
                batches["mbo"].append(_mbo_to_tuple(record))
            case databento.MBP10Msg():
                batches["mbp10"].append(_mbp10_to_tuple(record))
            case databento.ImbalanceMsg():
                batches["imbalance"].append(_imbalance_to_tuple(record))
            case databento.StatMsg():
                batches["statistics"].append(_statistics_to_tuple(record))
            case databento.StatusMsg():
                batches["status"].append(_status_to_tuple(record))
            case databento.InstrumentDefMsg():
                batches["instruments"].append(_instrument_to_tuple(record))
        count += 1

        if count % BATCH_SIZE == 0:
            _flush_batches(cursor, batches)

    _flush_batches(cursor, batches)
    return count


def _flush_batches(cursor: sqlite3.Cursor, batches: dict) -> None:
    """Flush all non-empty batches to the database using executemany."""
    if batches["ohlcv"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO ohlcv "
            "(instrument_id, rtype, ts_event, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            batches["ohlcv"],
        )
        batches["ohlcv"].clear()

    if batches["trades"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO trades "
            "(instrument_id, ts_event, ts_recv, price, size, action, side, flags, depth, ts_in_delta, sequence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["trades"],
        )
        batches["trades"].clear()

    if batches["quotes"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO quotes "
            "(instrument_id, ts_event, ts_recv, price, size, action, side, flags, depth, ts_in_delta, sequence, "
            "bid_px, ask_px, bid_sz, ask_sz, bid_ct, ask_ct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["quotes"],
        )
        batches["quotes"].clear()

    if batches["bbo"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO bbo "
            "(instrument_id, rtype, ts_event, ts_recv, price, size, side, flags, sequence, "
            "bid_px, ask_px, bid_sz, ask_sz, bid_ct, ask_ct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["bbo"],
        )
        batches["bbo"].clear()

    if batches["mbo"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO mbo "
            "(instrument_id, ts_event, ts_recv, order_id, price, size, flags, channel_id, action, side, ts_in_delta, sequence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["mbo"],
        )
        batches["mbo"].clear()

    if batches["mbp10"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO mbp10 "
            "(instrument_id, ts_event, ts_recv, price, size, action, side, flags, depth, ts_in_delta, sequence, "
            "bid_px_00, bid_px_01, bid_px_02, bid_px_03, bid_px_04, bid_px_05, bid_px_06, bid_px_07, bid_px_08, bid_px_09, "
            "ask_px_00, ask_px_01, ask_px_02, ask_px_03, ask_px_04, ask_px_05, ask_px_06, ask_px_07, ask_px_08, ask_px_09, "
            "bid_sz_00, bid_sz_01, bid_sz_02, bid_sz_03, bid_sz_04, bid_sz_05, bid_sz_06, bid_sz_07, bid_sz_08, bid_sz_09, "
            "ask_sz_00, ask_sz_01, ask_sz_02, ask_sz_03, ask_sz_04, ask_sz_05, ask_sz_06, ask_sz_07, ask_sz_08, ask_sz_09, "
            "bid_ct_00, bid_ct_01, bid_ct_02, bid_ct_03, bid_ct_04, bid_ct_05, bid_ct_06, bid_ct_07, bid_ct_08, bid_ct_09, "
            "ask_ct_00, ask_ct_01, ask_ct_02, ask_ct_03, ask_ct_04, ask_ct_05, ask_ct_06, ask_ct_07, ask_ct_08, ask_ct_09) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["mbp10"],
        )
        batches["mbp10"].clear()

    if batches["imbalance"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO imbalance "
            "(instrument_id, ts_event, ts_recv, ref_price, auction_time, cont_book_clr_price, auct_interest_clr_price, "
            "ssr_filling_price, ind_match_price, upper_collar, lower_collar, paired_qty, total_imbalance_qty, "
            "market_imbalance_qty, unpaired_qty, auction_type, side, auction_status, freeze_status, num_extensions, "
            "unpaired_side, significant_imbalance) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["imbalance"],
        )
        batches["imbalance"].clear()

    if batches["statistics"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO statistics "
            "(instrument_id, ts_event, ts_recv, ts_ref, price, quantity, sequence, ts_in_delta, stat_type, channel_id, "
            "update_action, stat_flags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["statistics"],
        )
        batches["statistics"].clear()

    if batches["status"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO status "
            "(instrument_id, ts_event, ts_recv, action, reason, trading_event, is_trading, is_quoting, is_short_sell_restricted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["status"],
        )
        batches["status"].clear()

    if batches["instruments"]:
        cursor.executemany(
            "INSERT OR REPLACE INTO instruments "
            "(publisher_id, raw_instrument_id, raw_symbol, instrument_class, security_type, asset, cfi, exchange, currency, "
            "strike_price, strike_price_currency, expiration, activation, maturity_year, maturity_month, maturity_day, "
            "contract_multiplier, unit_of_measure, unit_of_measure_qty, underlying, display_factor, high_limit_price, "
            "low_limit_price, min_price_increment, security_group, ts_recv) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batches["instruments"],
        )
        batches["instruments"].clear()


def _ohlcv_to_tuple(record: databento.OHLCVMsg) -> tuple:
    return (
        record.instrument_id,
        record.rtype.value,
        record.ts_event,
        record.open,
        record.high,
        record.low,
        record.close,
        record.volume,
    )


def _trade_to_tuple(record: databento.TradeMsg) -> tuple:
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.price,
        record.size,
        str(record.action),
        str(record.side),
        record.flags,
        record.depth,
        record.ts_in_delta,
        record.sequence,
    )


def _quote_to_tuple(record: databento.MBP1Msg) -> tuple:
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.price,
        record.size,
        str(record.action),
        str(record.side),
        record.flags,
        record.depth,
        record.ts_in_delta,
        record.sequence,
        record.levels[0].bid_px,
        record.levels[0].ask_px,
        record.levels[0].bid_sz,
        record.levels[0].ask_sz,
        record.levels[0].bid_ct,
        record.levels[0].ask_ct,
    )


def _bbo_to_tuple(record: databento.BBOMsg) -> tuple:
    return (
        record.instrument_id,
        record.rtype.value,
        record.ts_event,
        record.ts_recv,
        record.price,
        record.size,
        str(record.side),
        record.flags,
        record.sequence,
        record.levels[0].bid_px,
        record.levels[0].ask_px,
        record.levels[0].bid_sz,
        record.levels[0].ask_sz,
        record.levels[0].bid_ct,
        record.levels[0].ask_ct,
    )


def _mbo_to_tuple(record: databento.MBOMsg) -> tuple:
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.order_id,
        record.price,
        record.size,
        record.flags,
        record.channel_id,
        str(record.action),
        str(record.side),
        record.ts_in_delta,
        record.sequence,
    )


def _mbp10_to_tuple(record: databento.MBP10Msg) -> tuple:
    levels = record.levels
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.price,
        record.size,
        str(record.action),
        str(record.side),
        record.flags,
        record.depth,
        record.ts_in_delta,
        record.sequence,
        levels[0].bid_px,
        levels[1].bid_px,
        levels[2].bid_px,
        levels[3].bid_px,
        levels[4].bid_px,
        levels[5].bid_px,
        levels[6].bid_px,
        levels[7].bid_px,
        levels[8].bid_px,
        levels[9].bid_px,
        levels[0].ask_px,
        levels[1].ask_px,
        levels[2].ask_px,
        levels[3].ask_px,
        levels[4].ask_px,
        levels[5].ask_px,
        levels[6].ask_px,
        levels[7].ask_px,
        levels[8].ask_px,
        levels[9].ask_px,
        levels[0].bid_sz,
        levels[1].bid_sz,
        levels[2].bid_sz,
        levels[3].bid_sz,
        levels[4].bid_sz,
        levels[5].bid_sz,
        levels[6].bid_sz,
        levels[7].bid_sz,
        levels[8].bid_sz,
        levels[9].bid_sz,
        levels[0].ask_sz,
        levels[1].ask_sz,
        levels[2].ask_sz,
        levels[3].ask_sz,
        levels[4].ask_sz,
        levels[5].ask_sz,
        levels[6].ask_sz,
        levels[7].ask_sz,
        levels[8].ask_sz,
        levels[9].ask_sz,
        levels[0].bid_ct,
        levels[1].bid_ct,
        levels[2].bid_ct,
        levels[3].bid_ct,
        levels[4].bid_ct,
        levels[5].bid_ct,
        levels[6].bid_ct,
        levels[7].bid_ct,
        levels[8].bid_ct,
        levels[9].bid_ct,
        levels[0].ask_ct,
        levels[1].ask_ct,
        levels[2].ask_ct,
        levels[3].ask_ct,
        levels[4].ask_ct,
        levels[5].ask_ct,
        levels[6].ask_ct,
        levels[7].ask_ct,
        levels[8].ask_ct,
        levels[9].ask_ct,
    )


def _imbalance_to_tuple(record: databento.ImbalanceMsg) -> tuple:
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.ref_price,
        record.auction_time,
        record.cont_book_clr_price,
        record.auct_interest_clr_price,
        record.ssr_filling_price,
        record.ind_match_price,
        record.upper_collar,
        record.lower_collar,
        record.paired_qty,
        record.total_imbalance_qty,
        record.market_imbalance_qty,
        record.unpaired_qty,
        str(record.auction_type),
        str(record.side),
        record.auction_status,
        record.freeze_status,
        record.num_extensions,
        str(record.unpaired_side),
        str(record.significant_imbalance),
    )


def _statistics_to_tuple(record: databento.StatMsg) -> tuple:
    stat_type = record.stat_type
    update_action = record.update_action
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        record.ts_ref,
        record.price,
        record.quantity,
        record.sequence,
        record.ts_in_delta,
        stat_type.value if hasattr(stat_type, "value") else stat_type,
        record.channel_id,
        update_action.value if hasattr(update_action, "value") else update_action,
        record.stat_flags,
    )


def _status_to_tuple(record: databento.StatusMsg) -> tuple:
    action = record.action
    reason = record.reason
    trading_event = record.trading_event
    return (
        record.instrument_id,
        record.ts_event,
        record.ts_recv,
        action.value if hasattr(action, "value") else action,
        reason.value if hasattr(reason, "value") else reason,
        trading_event.value if hasattr(trading_event, "value") else trading_event,
        str(record.is_trading),
        str(record.is_quoting),
        str(record.is_short_sell_restricted),
    )


def _instrument_to_tuple(record: databento.InstrumentDefMsg) -> tuple:
    return (
        record.publisher_id,
        record.instrument_id,
        record.raw_symbol,
        str(record.instrument_class),
        record.security_type,
        record.asset,
        record.cfi,
        record.exchange,
        record.currency,
        record.strike_price,
        record.strike_price_currency,
        record.expiration,
        record.activation,
        record.maturity_year,
        record.maturity_month,
        record.maturity_day,
        record.contract_multiplier,
        record.unit_of_measure,
        record.unit_of_measure_qty,
        record.underlying,
        record.display_factor,
        record.high_limit_price,
        record.low_limit_price,
        record.min_price_increment,
        record.group,
        record.ts_recv,
    )


def update_meta(db_path: pathlib.Path) -> None:
    """
    Compute and store aggregate statistics in the meta table.

    This function runs expensive COUNT/MIN/MAX queries once and stores the results
    in the meta table for fast retrieval by the dashboard.

    Args:
        db_path: Path to the secmaster SQLite database.
    """
    import time

    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(DISTINCT instrument_id) FROM symbology")
    symbol_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ohlcv")
    ohlcv_count = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(ts_event), MAX(ts_event) FROM ohlcv")
    row = cursor.fetchone()
    min_ts, max_ts = row[0] or 0, row[1] or 0

    cursor.execute("SELECT DISTINCT rtype FROM ohlcv ORDER BY rtype")
    rtypes = ",".join(str(r[0]) for r in cursor.fetchall())

    stats = [
        ("symbol_count", str(symbol_count)),
        ("ohlcv_record_count", str(ohlcv_count)),
        ("ohlcv_min_ts", str(min_ts)),
        ("ohlcv_max_ts", str(max_ts)),
        ("ohlcv_schemas", rtypes),
        ("last_updated", str(int(time.time()))),
    ]

    cursor.executemany(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        stats,
    )

    connection.commit()
    connection.close()


def update_symbol_coverage(db_path: pathlib.Path) -> int:
    """
    Compute and store per-symbol coverage statistics in the symbol_coverage table.

    This function aggregates OHLCV data per instrument_id/rtype first (fast, uses
    primary key), then joins with symbology to get symbols.

    Args:
        db_path: Path to the secmaster SQLite database.

    Returns:
        The number of symbol/rtype combinations stored.
    """
    connection = sqlite3.connect(str(db_path))
    cursor = connection.cursor()

    cursor.execute("DELETE FROM symbol_coverage")

    cursor.execute(
        """
        INSERT INTO symbol_coverage (symbol, rtype, min_ts, max_ts, record_count)
        SELECT s.symbol, agg.rtype, MIN(agg.min_ts), MAX(agg.max_ts), SUM(agg.cnt)
        FROM (
            SELECT instrument_id, rtype, MIN(ts_event) as min_ts, MAX(ts_event) as max_ts, COUNT(*) as cnt
            FROM ohlcv
            GROUP BY instrument_id, rtype
        ) agg
        JOIN (
            SELECT DISTINCT instrument_id, symbol FROM symbology
        ) s ON agg.instrument_id = s.instrument_id
        GROUP BY s.symbol, agg.rtype
    """
    )

    count = cursor.rowcount
    connection.commit()
    connection.close()
    return count
