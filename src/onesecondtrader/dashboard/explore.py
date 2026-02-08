"""
Exploration execution engine for the dashboard.

Provides models, job tracking, and the core function for running indicator
explorations on raw price data without requiring a strategy or backtest.
"""

from __future__ import annotations

import enum
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .db import get_runs_db_path, get_secmaster_path

_executor = ThreadPoolExecutor(max_workers=1)

RTYPE_TO_BAR_PERIOD = {32: "SECOND", 33: "MINUTE", 34: "HOUR", 35: "DAY"}

MAX_RECENT_EXPLORATIONS = 10


class IndicatorConfig(BaseModel):
    class_name: str
    params: dict[str, Any] = {}


class ExploreRequest(BaseModel):
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None
    indicators: list[IndicatorConfig]


explore_jobs: dict[str, str] = {}
_explore_progress: dict[str, float] = {}
_jobs_lock = threading.Lock()


def enqueue_exploration(request: ExploreRequest, run_id: str) -> None:
    """Submit an exploration to the bounded thread pool."""
    with _jobs_lock:
        explore_jobs[run_id] = "queued"
        _explore_progress[run_id] = 0.0
    _executor.submit(run_exploration, request, run_id)


def run_exploration(request: ExploreRequest, run_id: str) -> None:
    """Execute an exploration in a background thread."""
    from onesecondtrader.dashboard.indicators_util import get_registered_indicators
    from onesecondtrader.models import BarPeriod
    from onesecondtrader import events

    try:
        with _jobs_lock:
            if explore_jobs.get(run_id, "").startswith("error"):
                return
            explore_jobs[run_id] = "running"

        # Resolve publisher
        sm_path = get_secmaster_path()
        sm_conn = sqlite3.connect(sm_path)
        cursor = sm_conn.cursor()
        cursor.execute(
            "SELECT name, dataset FROM publishers WHERE publisher_id = ?",
            (request.publisher_id,),
        )
        row = cursor.fetchone()
        if not row:
            sm_conn.close()
            with _jobs_lock:
                explore_jobs[run_id] = (
                    f"error: publisher_id {request.publisher_id} not found"
                )
            return
        _publisher_name, _dataset = row  # noqa: F841 – validated only

        # Resolve bar period
        bar_period_str = RTYPE_TO_BAR_PERIOD.get(request.rtype)
        if not bar_period_str:
            sm_conn.close()
            with _jobs_lock:
                explore_jobs[run_id] = f"error: invalid rtype {request.rtype}"
            return
        bar_period = BarPeriod[bar_period_str]

        # Instantiate indicators
        registry = get_registered_indicators()
        indicator_instances = []
        for ind_cfg in request.indicators:
            cls = registry.get(ind_cfg.class_name)
            if cls is None:
                sm_conn.close()
                with _jobs_lock:
                    explore_jobs[run_id] = (
                        f"error: unknown indicator {ind_cfg.class_name}"
                    )
                return
            # Deserialize indicator_class and enum params
            params = dict(ind_cfg.params)
            import inspect

            sig = inspect.signature(cls)
            for pname, param in sig.parameters.items():
                if pname not in params:
                    continue
                ann = param.annotation
                ann_str = str(ann) if ann is not inspect.Parameter.empty else ""
                if "type[" in ann_str:
                    resolved = registry.get(params[pname])
                    if resolved is None:
                        sm_conn.close()
                        with _jobs_lock:
                            explore_jobs[run_id] = (
                                f"error: unknown source indicator {params[pname]}"
                            )
                        return
                    params[pname] = resolved
                    continue
                default = param.default
                if isinstance(default, enum.Enum):
                    enum_cls = type(default)
                    try:
                        params[pname] = enum_cls[params[pname]]
                    except (KeyError, TypeError):
                        pass
            source_kw = params.pop("source_kwargs", None)
            if isinstance(source_kw, dict) and source_kw:
                source_kw = dict(source_kw)
                # Find the resolved source class
                source_cls = None
                for pname_chk, param_chk in sig.parameters.items():
                    ann_chk = param_chk.annotation
                    ann_str_chk = (
                        str(ann_chk) if ann_chk is not inspect.Parameter.empty else ""
                    )
                    if "type[" in ann_str_chk and pname_chk in params:
                        source_cls = params[pname_chk]
                        break
                # Deserialize enum values in source_kw
                if source_cls is not None:
                    source_sig = inspect.signature(source_cls.__init__)
                    for sk_name in list(source_kw.keys()):
                        if sk_name in source_sig.parameters:
                            sk_default = source_sig.parameters[sk_name].default
                            if isinstance(sk_default, enum.Enum):
                                try:
                                    source_kw[sk_name] = type(sk_default)[
                                        source_kw[sk_name]
                                    ]
                                except (KeyError, TypeError):
                                    pass
                # Construct, then override _source with custom sub-params
                inst = cls(**params)
                if source_cls is not None:
                    inst._source = source_cls(max_history=inst.period, **source_kw)  # type: ignore[attr-defined]
                indicator_instances.append(inst)
            else:
                indicator_instances.append(cls(**params))

        # Build SQL query for raw bars
        symbols = request.symbols
        params_list: list = [request.publisher_id, "raw_symbol"]
        params_list.extend(symbols)
        params_list.append(request.rtype)

        ts_clauses = ""
        if request.start_date:
            start_ts = int(pd.Timestamp(request.start_date, tz="UTC").value)
            params_list.append(start_ts)
            ts_clauses += " AND o.ts_event >= ?"
        if request.end_date:
            end_dt = (
                pd.Timestamp(request.end_date, tz="UTC")
                + pd.Timedelta(days=1)
                - pd.Timedelta(1, unit="ns")
            )
            end_ts = int(end_dt.value)
            params_list.append(end_ts)
            ts_clauses += " AND o.ts_event <= ?"

        where_clause = f"""
            FROM ohlcv o
            JOIN instruments i ON i.instrument_id = o.instrument_id
            JOIN symbology s
              ON s.publisher_ref = i.publisher_ref
             AND s.source_instrument_id = i.source_instrument_id
             AND date(o.ts_event / 1000000000, 'unixepoch') >= s.start_date
             AND date(o.ts_event / 1000000000, 'unixepoch') < s.end_date
            WHERE i.publisher_ref = ?
              AND s.symbol_type = ?
              AND s.symbol IN ({",".join("?" * len(symbols))})
              AND o.rtype = ?
              {ts_clauses}
        """

        # Count total bars
        count_query = f"SELECT COUNT(*) {where_clause}"
        cursor.execute(count_query, params_list)
        total_bars = cursor.fetchone()[0]

        # Query bars
        query = f"""
            SELECT s.symbol, o.rtype, o.ts_event, o.open, o.high, o.low, o.close, o.volume
            {where_clause}
            ORDER BY o.ts_event, s.symbol
        """
        bar_rows = cursor.execute(query, params_list).fetchall()
        sm_conn.close()

        # Open runs DB, ensure required tables exist
        runs_db_path = get_runs_db_path()
        runs_conn = sqlite3.connect(runs_db_path, timeout=10)
        runs_conn.execute("PRAGMA journal_mode = WAL")
        runs_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ts_start INTEGER NOT NULL,
                ts_end INTEGER,
                status TEXT NOT NULL CHECK(status IN ('running', 'completed', 'failed', 'cancelled')),
                config TEXT,
                metadata TEXT
            )
        """
        )
        runs_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bars_processed (
                id INTEGER PRIMARY KEY,
                run_id TEXT NOT NULL,
                ts_event_ns INTEGER NOT NULL,
                ts_created_ns INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                bar_period TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER,
                indicators TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            )
        """
        )
        runs_conn.commit()

        # Insert run record
        config = {
            "mode": "exploration",
            "symbols": request.symbols,
            "indicators": [
                {"class_name": ic.class_name, "params": ic.params}
                for ic in request.indicators
            ],
            "rtype": request.rtype,
            "publisher_id": request.publisher_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
        indicator_names = ", ".join(ic.class_name for ic in request.indicators)
        run_name = f"Explore: {indicator_names}"
        ts_now = time.time_ns()
        runs_conn.execute(
            "INSERT INTO runs (run_id, name, ts_start, ts_end, status, config, metadata) VALUES (?, ?, ?, NULL, 'running', ?, NULL)",
            (run_id, run_name, ts_now, json.dumps(config)),
        )
        runs_conn.commit()

        # Process bars
        price_scale = 1e9
        batch = []
        bars_processed = 0

        for row in bar_rows:
            symbol, _rtype, ts_event, open_, high, low, close, volume = row

            bar_event = events.market.BarReceived(
                ts_event_ns=ts_event,
                symbol=symbol,
                bar_period=bar_period,
                open=open_ / price_scale,
                high=high / price_scale,
                low=low / price_scale,
                close=close / price_scale,
                volume=volume,
            )

            for ind in indicator_instances:
                ind.update(bar_event)

            ind_values = {}
            for ind in indicator_instances:
                val = ind.latest(symbol)
                ind_values[ind.name] = val if val == val else None  # NaN -> None

            batch.append(
                (
                    run_id,
                    ts_event,
                    ts_event,  # ts_created_ns = ts_event for exploration
                    symbol,
                    bar_period_str,
                    open_ / price_scale,
                    high / price_scale,
                    low / price_scale,
                    close / price_scale,
                    volume,
                    json.dumps(ind_values),
                )
            )

            bars_processed += 1
            if len(batch) >= 1000:
                runs_conn.executemany(
                    "INSERT INTO bars_processed (run_id, ts_event_ns, ts_created_ns, symbol, bar_period, open, high, low, close, volume, indicators) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    batch,
                )
                runs_conn.commit()
                batch.clear()
                with _jobs_lock:
                    _explore_progress[run_id] = (
                        bars_processed / total_bars if total_bars > 0 else 1.0
                    )

        # Flush remaining
        if batch:
            runs_conn.executemany(
                "INSERT INTO bars_processed (run_id, ts_event_ns, ts_created_ns, symbol, bar_period, open, high, low, close, volume, indicators) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            runs_conn.commit()

        # Mark completed
        runs_conn.execute(
            "UPDATE runs SET status = 'completed', ts_end = ? WHERE run_id = ?",
            (time.time_ns(), run_id),
        )
        runs_conn.commit()

        # Cleanup: keep only the N most recent exploration runs
        _cleanup_old_explorations(runs_conn)

        runs_conn.close()

        with _jobs_lock:
            explore_jobs[run_id] = "completed"
            _explore_progress[run_id] = 1.0

    except Exception as e:
        with _jobs_lock:
            explore_jobs[run_id] = f"error: {e}"


def _cleanup_old_explorations(conn: sqlite3.Connection) -> None:
    """Keep only the most recent exploration runs, deleting older ones."""
    from .db import CHILD_TABLES

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT run_id, config FROM runs
        ORDER BY ts_start DESC
        """
    )
    explore_run_ids = []
    for row in cursor.fetchall():
        try:
            config = json.loads(row[1]) if row[1] else {}
        except (json.JSONDecodeError, TypeError):
            config = {}
        if config.get("mode") == "exploration":
            explore_run_ids.append(row[0])

    if len(explore_run_ids) <= MAX_RECENT_EXPLORATIONS:
        return

    to_delete = explore_run_ids[MAX_RECENT_EXPLORATIONS:]
    placeholders = ",".join("?" for _ in to_delete)
    for table in CHILD_TABLES:
        cursor.execute(
            f"DELETE FROM {table} WHERE run_id IN ({placeholders})",
            to_delete,
        )
    cursor.execute(
        f"DELETE FROM runs WHERE run_id IN ({placeholders})",
        to_delete,
    )
    conn.commit()
