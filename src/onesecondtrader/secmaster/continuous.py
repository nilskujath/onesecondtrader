"""
Build continuous contract symbology from individual futures contract data.

Supports multiple roll rules:
  - Calendar (.c.) — rolls based on contract expiry dates
  - Volume (.v.) — rolls when the next contract's daily volume exceeds the current
  - Open interest (.n.) — deferred, raises NotImplementedError

Usage:
    python -m onesecondtrader.secmaster.continuous \
        --db secmaster.db \
        --publisher-id 1 \
        --root MNQ \
        --rule c \
        --roll-offset 0
"""

from __future__ import annotations

import argparse
import datetime
import logging
import pathlib
import re
import sqlite3

logger = logging.getLogger(__name__)

_MONTH_CODES = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}

# Regex: root symbol (letters) + month code (single letter) + year digit(s)
_FUTURES_RE = re.compile(r"^([A-Z]+)([FGHJKMNQUVXZ])(\d{1,2})$")


def _parse_futures_symbol(symbol: str) -> tuple[str, int, int] | None:
    """Parse 'MNQH5' -> ('MNQ', 3, 2025). Returns None for spreads or unparseable symbols."""
    m = _FUTURES_RE.match(symbol)
    if m is None:
        return None
    root = m.group(1)
    month = _MONTH_CODES[m.group(2)]
    year_short = int(m.group(3))
    # Map 1-digit year: 0-9. Use 2020s decade for 0-6, 2010s for 7-9
    # For 2-digit years, use directly
    if year_short < 10:
        year = 2020 + year_short if year_short <= 6 else 2010 + year_short
    else:
        year = 2000 + year_short
    return root, month, year


def _third_friday(year: int, month: int) -> datetime.date:
    """Return the 3rd Friday of the given month."""
    # Find the first day of the month
    first_day = datetime.date(year, month, 1)
    # weekday: Monday=0, Friday=4
    first_friday = first_day + datetime.timedelta(days=(4 - first_day.weekday()) % 7)
    third_friday = first_friday + datetime.timedelta(weeks=2)
    return third_friday


def _discover_contracts(
    con: sqlite3.Connection,
    publisher_id: int,
    root_symbol: str,
) -> list[dict]:
    """
    Discover individual outright contracts from symbology for a given root symbol.

    Returns a list of dicts with keys: symbol, root, month, year, expiry,
    source_instrument_id, start_date, end_date.
    """
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT DISTINCT symbol, source_instrument_id, start_date, end_date
        FROM symbology
        WHERE publisher_ref = ?
          AND symbol_type = 'raw_symbol'
          AND symbol LIKE ? || '%'
        ORDER BY symbol
        """,
        (publisher_id, root_symbol),
    )
    contracts = []
    for row in cursor.fetchall():
        symbol, source_instrument_id, start_date, end_date = row
        if "-" in symbol:
            continue  # Skip spreads
        parsed = _parse_futures_symbol(symbol)
        if parsed is None:
            continue
        r, month, year = parsed
        if r != root_symbol:
            continue
        expiry = _third_friday(year, month)
        contracts.append(
            {
                "symbol": symbol,
                "root": r,
                "month": month,
                "year": year,
                "expiry": expiry,
                "source_instrument_id": source_instrument_id,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    # Sort by expiry date
    contracts.sort(key=lambda c: c["expiry"])
    return contracts


def _get_or_create_continuous_instrument(
    con: sqlite3.Connection,
    publisher_id: int,
    continuous_symbol: str,
) -> None:
    """Ensure an instrument record exists for the continuous symbol mapping."""
    cursor = con.cursor()
    cursor.execute(
        "SELECT instrument_id FROM instruments "
        "WHERE publisher_ref = ? AND symbol = ? AND symbol_type = 'continuous'",
        (publisher_id, continuous_symbol),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO instruments (publisher_ref, symbol, symbol_type) "
            "VALUES (?, ?, 'continuous')",
            (publisher_id, continuous_symbol),
        )


def build_continuous_symbology(
    db_path: pathlib.Path,
    publisher_id: int,
    root_symbol: str,
    roll_rule: str = "c",
    roll_offset_days: int = 0,
    rebuild_coverage: bool = True,
) -> int:
    """
    Build front-month continuous symbology from individual contract data.

    Creates symbology entries mapping '{root}.{rule}.0' to the correct
    underlying contract for each roll period.

    Parameters:
        db_path:
            Path to the security master SQLite database.
        publisher_id:
            Publisher ID for the futures data.
        root_symbol:
            Root symbol (e.g., 'MNQ').
        roll_rule:
            Roll rule: 'c' = calendar, 'v' = volume, 'n' = open interest.
        roll_offset_days:
            For calendar roll: days before expiry to roll.
        rebuild_coverage:
            Whether to rebuild symbol_coverage after creating entries.
            Set to False when calling in a loop to avoid redundant rebuilds.

    Returns:
        The number of symbology entries created.
    """
    if roll_rule == "c":
        return _build_calendar_continuous(
            db_path,
            publisher_id,
            root_symbol,
            roll_offset_days,
            rebuild_coverage=rebuild_coverage,
        )
    elif roll_rule == "v":
        return _build_volume_continuous(
            db_path,
            publisher_id,
            root_symbol,
            rebuild_coverage=rebuild_coverage,
        )
    elif roll_rule == "n":
        raise NotImplementedError(
            "Open interest roll (.n.) requires OI data not currently stored in OHLCV. "
            "This can be added when OI data becomes available."
        )
    else:
        raise ValueError(f"Unknown roll rule: {roll_rule!r}. Use 'c', 'v', or 'n'.")


def _build_calendar_continuous(
    db_path: pathlib.Path,
    publisher_id: int,
    root_symbol: str,
    roll_offset_days: int,
    rebuild_coverage: bool = True,
) -> int:
    """Build continuous symbology using calendar-based roll (3rd Friday of contract month)."""
    from .utils import _assert_secmaster_db, rebuild_symbol_coverage

    continuous_symbol = f"{root_symbol}.c.0"
    logger.info(
        "Building calendar continuous symbology: %s (offset=%d days)",
        continuous_symbol,
        roll_offset_days,
    )

    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        _assert_secmaster_db(con)

        contracts = _discover_contracts(con, publisher_id, root_symbol)
        if not contracts:
            logger.warning("No contracts found for root symbol %s", root_symbol)
            return 0

        logger.info("Discovered %d contracts for %s", len(contracts), root_symbol)

        # Delete existing continuous symbology for this symbol
        con.execute(
            "DELETE FROM symbology WHERE publisher_ref = ? AND symbol = ? AND symbol_type = 'continuous'",
            (publisher_id, continuous_symbol),
        )

        # Build front-month periods
        # For each contract, the front-month period is:
        #   start = previous contract's (expiry - offset) [or contract's own start_date for the first]
        #   end = this contract's (expiry - offset)
        entries = []
        for i, contract in enumerate(contracts):
            roll_date = contract["expiry"] - datetime.timedelta(days=roll_offset_days)

            if i == 0:
                # First contract: start from its symbology start_date
                period_start = contract["start_date"]
            else:
                # Start from previous contract's roll date
                prev_roll = contracts[i - 1]["expiry"] - datetime.timedelta(
                    days=roll_offset_days
                )
                period_start = prev_roll.isoformat()

            period_end = roll_date.isoformat()

            # Skip if period is empty or inverted
            if period_start >= period_end:
                continue

            entries.append(
                (
                    publisher_id,
                    continuous_symbol,
                    "continuous",
                    contract["source_instrument_id"],
                    period_start,
                    period_end,
                )
            )

        if not entries:
            logger.warning("No valid front-month periods generated")
            return 0

        # Ensure instrument records exist for the continuous symbol
        # Use the first contract's source_instrument_id for the instrument record
        _get_or_create_continuous_instrument(con, publisher_id, continuous_symbol)

        # Insert symbology entries
        con.executemany(
            "INSERT OR REPLACE INTO symbology "
            "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            entries,
        )
        con.commit()

        logger.info(
            "Created %d continuous symbology entries for %s",
            len(entries),
            continuous_symbol,
        )
    finally:
        con.close()

    if rebuild_coverage:
        rebuild_symbol_coverage(db_path)

    return len(entries)


def _build_volume_continuous(
    db_path: pathlib.Path,
    publisher_id: int,
    root_symbol: str,
    rebuild_coverage: bool = True,
) -> int:
    """Build continuous symbology using volume-based roll detection."""
    from .utils import _assert_secmaster_db, rebuild_symbol_coverage

    continuous_symbol = f"{root_symbol}.v.0"
    logger.info("Building volume continuous symbology: %s", continuous_symbol)

    con = sqlite3.connect(str(db_path))
    try:
        con.execute("PRAGMA foreign_keys = ON;")
        _assert_secmaster_db(con)

        contracts = _discover_contracts(con, publisher_id, root_symbol)
        if len(contracts) < 2:
            logger.warning(
                "Need at least 2 contracts for volume roll, found %d",
                len(contracts),
            )
            return 0

        logger.info("Discovered %d contracts for %s", len(contracts), root_symbol)

        # Delete existing continuous symbology for this symbol
        con.execute(
            "DELETE FROM symbology WHERE publisher_ref = ? AND symbol = ? AND symbol_type = 'continuous'",
            (publisher_id, continuous_symbol),
        )

        # For each pair of consecutive contracts, find the volume crossover date
        # by comparing daily volumes
        entries: list[tuple[int, str, str, int, str, str]] = []
        for i in range(len(contracts) - 1):
            current = contracts[i]
            next_contract = contracts[i + 1]

            # Get daily volumes for both contracts in the overlap period
            # The overlap period is from next_contract's start to current's expiry
            cursor = con.cursor()
            cursor.execute(
                """
                SELECT
                    date(o.ts_event / 1000000000, 'unixepoch') AS trade_date,
                    SUM(o.volume) AS daily_volume
                FROM ohlcv o
                JOIN instruments i ON i.instrument_id = o.instrument_id
                WHERE i.publisher_ref = ?
                  AND i.source_instrument_id = ?
                  AND o.rtype IN (32, 33, 34, 35)
                GROUP BY trade_date
                ORDER BY trade_date
                """,
                (publisher_id, current["source_instrument_id"]),
            )
            current_volumes = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT
                    date(o.ts_event / 1000000000, 'unixepoch') AS trade_date,
                    SUM(o.volume) AS daily_volume
                FROM ohlcv o
                JOIN instruments i ON i.instrument_id = o.instrument_id
                WHERE i.publisher_ref = ?
                  AND i.source_instrument_id = ?
                  AND o.rtype IN (32, 33, 34, 35)
                GROUP BY trade_date
                ORDER BY trade_date
                """,
                (publisher_id, next_contract["source_instrument_id"]),
            )
            next_volumes = {row[0]: row[1] for row in cursor.fetchall()}

            # Find the first date where next contract's volume exceeds current
            all_dates = sorted(set(current_volumes.keys()) & set(next_volumes.keys()))
            roll_date_str = None
            for d in all_dates:
                if next_volumes[d] > current_volumes.get(d, 0):
                    roll_date_str = d
                    break

            if roll_date_str is None:
                # Fall back to expiry date if no volume crossover detected
                roll_date_str = current["expiry"].isoformat()

            if i == 0:
                period_start = current["start_date"]
            else:
                # Previous entry's end date
                period_start = entries[-1][5] if entries else current["start_date"]

            period_end = roll_date_str

            if period_start >= period_end:
                continue

            entries.append(
                (
                    publisher_id,
                    continuous_symbol,
                    "continuous",
                    current["source_instrument_id"],
                    period_start,
                    period_end,
                )
            )

        # Add the last contract (from last roll to its end)
        if entries and len(contracts) > 0:
            last_contract = contracts[-1]
            last_period_start = entries[-1][5]
            last_period_end = last_contract["end_date"]
            if last_period_start < last_period_end:
                entries.append(
                    (
                        publisher_id,
                        continuous_symbol,
                        "continuous",
                        last_contract["source_instrument_id"],
                        last_period_start,
                        last_period_end,
                    )
                )

        if not entries:
            logger.warning("No valid front-month periods generated")
            return 0

        # Ensure instrument record exists
        _get_or_create_continuous_instrument(con, publisher_id, continuous_symbol)

        # Insert symbology entries
        con.executemany(
            "INSERT OR REPLACE INTO symbology "
            "(publisher_ref, symbol, symbol_type, source_instrument_id, start_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            entries,
        )
        con.commit()

        logger.info(
            "Created %d volume-roll continuous symbology entries for %s",
            len(entries),
            continuous_symbol,
        )
    finally:
        con.close()

    if rebuild_coverage:
        rebuild_symbol_coverage(db_path)

    return len(entries)


def _discover_root_symbols(
    con: sqlite3.Connection,
    publisher_id: int,
) -> set[str]:
    """
    Discover unique futures root symbols from symbology for a given publisher.

    Queries all raw_symbol entries, parses each with _FUTURES_RE,
    and collects unique root symbols. Skips spreads (symbols containing '-').

    Returns:
        Set of root symbol strings (e.g., {'MNQ', 'ES'}).
    """
    cursor = con.cursor()
    cursor.execute(
        """
        SELECT DISTINCT symbol
        FROM symbology
        WHERE publisher_ref = ?
          AND symbol_type = 'raw_symbol'
        """,
        (publisher_id,),
    )
    roots: set[str] = set()
    for (symbol,) in cursor.fetchall():
        if "-" in symbol:
            continue
        parsed = _parse_futures_symbol(symbol)
        if parsed is not None:
            roots.add(parsed[0])
    return roots


def build_all_continuous(
    db_path: pathlib.Path,
    publisher_id: int,
    rebuild_coverage: bool = True,
) -> int:
    """
    Build calendar-roll and volume-roll continuous symbology for every
    futures root symbol discovered in the given publisher's symbology.

    Safe to call on datasets with no futures — returns 0.

    Parameters:
        db_path:
            Path to the security master SQLite database.
        publisher_id:
            Publisher ID to scan for futures root symbols.
        rebuild_coverage:
            Whether to rebuild symbol_coverage once at the end.

    Returns:
        Total number of continuous symbology entries created.
    """
    from .utils import rebuild_symbol_coverage

    con = sqlite3.connect(str(db_path))
    try:
        roots = _discover_root_symbols(con, publisher_id)
    finally:
        con.close()

    if not roots:
        logger.info("No futures root symbols found for publisher_id=%d", publisher_id)
        return 0

    logger.info(
        "Discovered %d futures root symbol(s) for publisher_id=%d: %s",
        len(roots),
        publisher_id,
        ", ".join(sorted(roots)),
    )

    total = 0
    for root in sorted(roots):
        for rule in ("c", "v"):
            try:
                count = build_continuous_symbology(
                    db_path,
                    publisher_id,
                    root,
                    roll_rule=rule,
                    rebuild_coverage=False,
                )
                total += count
            except Exception:
                logger.exception(
                    "Failed to build %s continuous for root=%s", rule, root
                )

    if rebuild_coverage:
        rebuild_symbol_coverage(db_path)

    logger.info(
        "Built continuous symbology: %d root symbol(s), %d total entries",
        len(roots),
        total,
    )
    return total


def main() -> None:
    """CLI entry point for building continuous symbology."""
    parser = argparse.ArgumentParser(
        description="Build continuous contract symbology from individual futures data"
    )
    parser.add_argument(
        "--db",
        required=True,
        type=pathlib.Path,
        help="Path to secmaster.db",
    )
    parser.add_argument(
        "--publisher-id",
        required=True,
        type=int,
        help="Publisher ID for the futures data",
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Root symbol (e.g., MNQ)",
    )
    parser.add_argument(
        "--rule",
        default="c",
        choices=["c", "v", "n"],
        help="Roll rule: c=calendar, v=volume, n=open interest (default: c)",
    )
    parser.add_argument(
        "--roll-offset",
        default=0,
        type=int,
        help="Days before expiry to roll (calendar rule only, default: 0)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    count = build_continuous_symbology(
        db_path=args.db,
        publisher_id=args.publisher_id,
        root_symbol=args.root,
        roll_rule=args.rule,
        roll_offset_days=args.roll_offset,
    )
    print(f"Created {count} continuous symbology entries")


if __name__ == "__main__":
    main()
