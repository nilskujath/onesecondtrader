"""Exploration execution engine for the Explorer dashboard.

Runs indicator computations via direct bar iteration, bypassing the
Orchestrator/EventBus stack for speed while producing identical results.
"""

from __future__ import annotations

import enum
import hashlib
import inspect
import json as json_module
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .db import get_runs_db_path, connect_secmaster, connect_presets, connect_runs
from .explore import _cleanup_old_explorations

_executor = ThreadPoolExecutor(max_workers=2)

RTYPE_TO_BAR_PERIOD = {32: "SECOND", 33: "MINUTE", 34: "HOUR", 35: "DAY"}


class IndicatorConfig(BaseModel):
    class_name: str
    params: dict[str, Any] = {}


class ExplorerRequest(BaseModel):
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None
    indicators: list[IndicatorConfig]
    symbol_type: str = "raw_symbol"


class SingleIndicatorRequest(BaseModel):
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None
    indicator: IndicatorConfig
    symbol_type: str = "raw_symbol"
    session_id: str


def compute_session_id(
    publisher_id: int,
    rtype: int,
    symbols: list[str],
    start_date: str | None,
    end_date: str | None,
    symbol_type: str,
) -> str:
    """Deterministic SHA-256 hash of the data source config."""
    key = json_module.dumps(
        {
            "publisher_id": publisher_id,
            "rtype": rtype,
            "symbols": sorted(symbols),
            "start_date": start_date,
            "end_date": end_date,
            "symbol_type": symbol_type,
        },
        sort_keys=True,
    )
    return hashlib.sha256(key.encode()).hexdigest()


def find_cached_run(
    session_id: str, class_name: str, params: dict, indicator_name: str | None = None
) -> str | None:
    """Query session_indicators for a completed run with matching params that still exists in runs.db."""
    params_canonical = json_module.dumps(params, sort_keys=True)
    with connect_presets() as conn:
        cursor = conn.cursor()
        if indicator_name:
            cursor.execute(
                """
                SELECT run_id FROM session_indicators
                WHERE session_id = ? AND class_name = ? AND params_canonical = ?
                  AND indicator_name = ? AND status = 'completed'
                ORDER BY rowid DESC LIMIT 1
                """,
                (session_id, class_name, params_canonical, indicator_name),
            )
        else:
            cursor.execute(
                """
                SELECT run_id FROM session_indicators
                WHERE session_id = ? AND class_name = ? AND params_canonical = ? AND status = 'completed'
                ORDER BY rowid DESC LIMIT 1
                """,
                (session_id, class_name, params_canonical),
            )
        row = cursor.fetchone()
    if not row:
        return None
    run_id = row[0]
    # Verify run still exists in runs.db
    try:
        with connect_runs() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,))
            run_row = cursor.fetchone()
            if run_row and run_row[0] == "completed":
                return run_id
    except FileNotFoundError:
        pass
    return None


def create_or_get_session(
    publisher_id: int,
    rtype: int,
    symbols: list[str],
    start_date: str | None,
    end_date: str | None,
    symbol_type: str,
) -> tuple[str, list[dict]]:
    """Create or retrieve a session. Returns (session_id, cached_indicators)."""
    session_id = compute_session_id(
        publisher_id, rtype, symbols, start_date, end_date, symbol_type
    )
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id FROM explorer_sessions WHERE session_id = ?",
            (session_id,),
        )
        if not cursor.fetchone():
            conn.execute(
                """
                INSERT INTO explorer_sessions
                (session_id, publisher_id, rtype, symbols, start_date, end_date, symbol_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    publisher_id,
                    rtype,
                    json_module.dumps(sorted(symbols)),
                    start_date,
                    end_date,
                    symbol_type,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        # Get cached indicators
        cursor.execute(
            """
            SELECT class_name, params_canonical, run_id, status, indicator_name
            FROM session_indicators
            WHERE session_id = ?
            """,
            (session_id,),
        )
        cached = [
            {
                "class_name": r[0],
                "params": json_module.loads(r[1]),
                "run_id": r[2],
                "status": r[3],
                "indicator_name": r[4],
            }
            for r in cursor.fetchall()
        ]
    return session_id, cached


def enqueue_single_indicator(request: SingleIndicatorRequest, run_id: str) -> None:
    """Run a single indicator within a session by converting to ExplorerRequest."""
    params_canonical = json_module.dumps(request.indicator.params, sort_keys=True)

    # Compute indicator name from current code
    indicator_name = None
    try:
        instances = _instantiate_indicators([request.indicator])
        if instances:
            indicator_name = instances[0].name
    except Exception:
        pass

    with connect_presets() as conn:
        conn.execute(
            """
            INSERT INTO session_indicators
            (session_id, run_id, class_name, params_canonical, status, indicator_name)
            VALUES (?, ?, ?, ?, 'running', ?)
            """,
            (
                request.session_id,
                run_id,
                request.indicator.class_name,
                params_canonical,
                indicator_name,
            ),
        )
        conn.commit()

    explorer_req = ExplorerRequest(
        symbols=request.symbols,
        rtype=request.rtype,
        publisher_id=request.publisher_id,
        start_date=request.start_date,
        end_date=request.end_date,
        indicators=[request.indicator],
        symbol_type=request.symbol_type,
    )

    def _run_and_update():
        run_explorer(explorer_req, run_id)
        with _jobs_lock:
            status = explorer_jobs.get(run_id, "unknown")
        final_status = "completed" if status == "completed" else status
        with connect_presets() as conn:
            conn.execute(
                "UPDATE session_indicators SET status = ? WHERE run_id = ?",
                (final_status, run_id),
            )
            conn.commit()

    with _jobs_lock:
        explorer_jobs[run_id] = "queued"
        _cancel_events[run_id] = threading.Event()
    _executor.submit(_run_and_update)


def get_session_indicators(session_id: str) -> list[dict]:
    """Get all indicator runs in a session."""
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT class_name, params_canonical, run_id, status, indicator_name
            FROM session_indicators
            WHERE session_id = ?
            """,
            (session_id,),
        )
        return [
            {
                "class_name": r[0],
                "params": json_module.loads(r[1]),
                "run_id": r[2],
                "status": r[3],
                "indicator_name": r[4],
            }
            for r in cursor.fetchall()
        ]


def get_session_run_ids(session_id: str) -> list[str]:
    """Get completed run_ids for a session."""
    with connect_presets() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT run_id FROM session_indicators
            WHERE session_id = ? AND status = 'completed'
            ORDER BY rowid
            """,
            (session_id,),
        )
        return [r[0] for r in cursor.fetchall()]


explorer_jobs: dict[str, str] = {}
_orchestrator_refs: dict[str, Any] = {}
_cancel_events: dict[str, threading.Event] = {}
_jobs_lock = threading.Lock()


class _ProgressTracker:
    """Lightweight progress tracker that duck-types with Orchestrator.progress."""

    def __init__(self, total: int) -> None:
        self._total = total
        self._processed = 0

    @property
    def progress(self) -> float:
        if self._total <= 0:
            return 0.0
        return min(self._processed / self._total, 1.0)

    def advance(self, n: int = 1) -> None:
        self._processed += n


def enqueue_exploration(request: ExplorerRequest, run_id: str) -> None:
    """Submit an exploration to the bounded thread pool."""
    with _jobs_lock:
        explorer_jobs[run_id] = "queued"
        _cancel_events[run_id] = threading.Event()
    _executor.submit(run_explorer, request, run_id)


def get_explorer_progress(run_id: str) -> float:
    """Return progress for an exploration run from the orchestrator ref."""
    with _jobs_lock:
        orch = _orchestrator_refs.get(run_id)
    if orch is not None:
        return orch.progress
    return 0.0


def cancel_run(run_id: str) -> bool:
    """Signal cancellation for a running exploration. Returns True if signal was sent."""
    with _jobs_lock:
        cancel_ev = _cancel_events.get(run_id)
        if cancel_ev is None:
            return False
        cancel_ev.set()
        explorer_jobs[run_id] = "cancelled"
    return True


def _instantiate_indicators(
    indicator_configs: list[IndicatorConfig],
) -> list:
    """Instantiate indicator objects from config, resolving classes and enums."""
    from onesecondtrader.dashboard.indicators_util import get_registered_indicators

    registry = get_registered_indicators()
    instances = []

    for ind_cfg in indicator_configs:
        cls = registry.get(ind_cfg.class_name)
        if cls is None:
            raise ValueError(f"Unknown indicator: {ind_cfg.class_name}")

        params = dict(ind_cfg.params)
        sig = inspect.signature(cls)

        # First pass: identify indicator_class params and their linked kwargs
        indicator_class_params = {}
        linked_kwargs = {}
        for pname, param in sig.parameters.items():
            ann = param.annotation
            ann_str = str(ann) if ann is not inspect.Parameter.empty else ""
            if "type[" in ann_str:
                indicator_class_params[pname] = param
                # Look for X_kwargs pattern
                kwargs_name = f"{pname}_kwargs"
                if kwargs_name in sig.parameters:
                    linked_kwargs[pname] = kwargs_name

        # Second pass: resolve all params
        for pname, param in sig.parameters.items():
            if pname not in params:
                continue
            ann = param.annotation
            ann_str = str(ann) if ann is not inspect.Parameter.empty else ""

            if "type[" in ann_str:
                # Resolve indicator class from registry
                resolved = registry.get(params[pname])
                if resolved is None:
                    raise ValueError(f"Unknown source indicator: {params[pname]}")
                params[pname] = resolved
            else:
                # Resolve enum values
                default = param.default
                if isinstance(default, enum.Enum):
                    enum_cls = type(default)
                    try:
                        params[pname] = enum_cls[params[pname]]
                    except (KeyError, TypeError):
                        pass

        # Third pass: resolve enum values inside kwargs dicts
        for ic_pname, kw_name in linked_kwargs.items():
            kw_dict = params.get(kw_name)
            if not isinstance(kw_dict, dict) or not kw_dict:
                continue
            kw_dict = dict(kw_dict)
            params[kw_name] = kw_dict
            source_cls = params.get(ic_pname)
            if source_cls is None or not callable(source_cls):
                continue
            source_sig = inspect.signature(source_cls.__init__)
            for sk_name in list(kw_dict.keys()):
                if sk_name in source_sig.parameters:
                    sk_default = source_sig.parameters[sk_name].default
                    if isinstance(sk_default, enum.Enum):
                        try:
                            kw_dict[sk_name] = type(sk_default)[kw_dict[sk_name]]
                        except (KeyError, TypeError):
                            pass

        # Handle legacy source_kwargs for indicators that use **source_kwargs
        source_kw = params.pop("source_kwargs", None)
        if isinstance(source_kw, dict) and source_kw:
            source_kw = dict(source_kw)
            # Find the indicator_class param to resolve enums in source_kw
            source_cls = None
            for ic_pname in indicator_class_params:
                if ic_pname in params and callable(params[ic_pname]):
                    source_cls = params[ic_pname]
                    break
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
            # Build instance, then override _source with custom sub-params
            inst = cls(**params)
            if source_cls is not None:
                inst._source = source_cls(max_history=inst.period, **source_kw)  # type: ignore[attr-defined]
            instances.append(inst)
        else:
            instances.append(cls(**params))

    return instances


def run_explorer(request: ExplorerRequest, run_id: str) -> None:
    """Execute an exploration in a background thread via direct iteration.

    Bypasses the Orchestrator/EventBus stack and iterates bars directly,
    calling ``IndicatorBase.update()`` / ``IndicatorBase.latest()`` per bar.
    This eliminates per-bar overhead (event publishing, thread
    synchronisation, idle-polling) while producing identical results.
    """
    import sqlite3
    import time

    from onesecondtrader import events
    from onesecondtrader.models import BarPeriod

    INSERT_SQL = (
        "INSERT INTO bars_processed"
        " (run_id, ts_event_ns, ts_created_ns, symbol, bar_period,"
        " open, high, low, close, volume, indicators)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    BATCH_SIZE = 1000

    runs_conn: sqlite3.Connection | None = None

    try:
        with _jobs_lock:
            if explorer_jobs.get(run_id, "").startswith("error"):
                return
            explorer_jobs[run_id] = "running"

        # -- Phase 1: Resolve bar period --
        bar_period_str = RTYPE_TO_BAR_PERIOD.get(request.rtype)
        if not bar_period_str:
            with _jobs_lock:
                explorer_jobs[run_id] = f"error: invalid rtype {request.rtype}"
            return
        bar_period = BarPeriod[bar_period_str]

        # -- Phase 2: Resolve publisher --
        with connect_secmaster() as sm_conn:
            cursor = sm_conn.cursor()
            cursor.execute(
                "SELECT name, dataset FROM publishers WHERE publisher_id = ?",
                (request.publisher_id,),
            )
            row = cursor.fetchone()
        if not row:
            with _jobs_lock:
                explorer_jobs[run_id] = (
                    f"error: publisher_id {request.publisher_id} not found"
                )
            return

        # -- Phase 3: Instantiate indicators --
        try:
            indicator_instances = _instantiate_indicators(request.indicators)
        except ValueError as e:
            with _jobs_lock:
                explorer_jobs[run_id] = f"error: {e}"
            return

        # -- Phase 4: Build secmaster query --
        symbols = request.symbols
        params_list: list = [request.publisher_id, request.symbol_type]
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

        # -- Phase 5: Count total bars for progress --
        with connect_secmaster() as sm_conn:
            cursor = sm_conn.cursor()
            count_query = f"SELECT COUNT(*) {where_clause}"
            cursor.execute(count_query, params_list)
            total_bars = cursor.fetchone()[0]

        # -- Phase 6: Register progress tracker --
        tracker = _ProgressTracker(total_bars)
        with _jobs_lock:
            _orchestrator_refs[run_id] = tracker

        # -- Phase 7: Open runs.db, ensure schema, insert run record --
        runs_db_path = get_runs_db_path()
        runs_conn = sqlite3.connect(runs_db_path, timeout=10)
        runs_conn.execute("PRAGMA journal_mode = WAL")
        runs_conn.execute("PRAGMA synchronous = NORMAL")
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
        runs_conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bars_processed_run_symbol_ts"
            " ON bars_processed (run_id, symbol, ts_event_ns)"
        )
        runs_conn.commit()

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
            "INSERT INTO runs (run_id, name, ts_start, ts_end, status, config, metadata)"
            " VALUES (?, ?, ?, NULL, 'running', ?, NULL)",
            (run_id, run_name, ts_now, json_module.dumps(config)),
        )
        runs_conn.commit()

        # -- Phase 8: Direct iteration loop --
        query = f"""
            SELECT s.symbol, o.rtype, o.ts_event, o.open, o.high, o.low, o.close, o.volume
            {where_clause}
            ORDER BY o.ts_event, s.symbol
        """

        price_scale = 1e9
        batch: list[tuple] = []
        bars_processed_count = 0

        # Check for cancellation before starting iteration
        with _jobs_lock:
            cancel_ev = _cancel_events.get(run_id)
        if cancel_ev is not None and cancel_ev.is_set():
            runs_conn.execute(
                "UPDATE runs SET status = 'cancelled', ts_end = ? WHERE run_id = ?",
                (time.time_ns(), run_id),
            )
            runs_conn.commit()
            with _jobs_lock:
                explorer_jobs[run_id] = "cancelled"
            return

        with connect_secmaster() as sm_conn:
            cursor = sm_conn.cursor()
            for row in cursor.execute(query, params_list):
                symbol, _rtype, ts_event, open_, high, low, close, volume = row

                bar_event = events.market.BarReceived(
                    ts_event_ns=ts_event,
                    ts_created_ns=ts_event,
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
                    ind_values[ind.name] = val if val == val else None  # NaN → None

                batch.append(
                    (
                        run_id,
                        ts_event,
                        ts_event,
                        symbol,
                        bar_period_str,
                        open_ / price_scale,
                        high / price_scale,
                        low / price_scale,
                        close / price_scale,
                        volume,
                        json_module.dumps(ind_values),
                    )
                )

                bars_processed_count += 1
                if len(batch) >= BATCH_SIZE:
                    runs_conn.executemany(INSERT_SQL, batch)
                    runs_conn.commit()
                    batch.clear()
                    tracker.advance(BATCH_SIZE)

                    # Check for cancellation after each batch
                    with _jobs_lock:
                        cancel_ev = _cancel_events.get(run_id)
                    if cancel_ev is not None and cancel_ev.is_set():
                        runs_conn.execute(
                            "DELETE FROM bars_processed WHERE run_id = ?", (run_id,)
                        )
                        runs_conn.execute(
                            "UPDATE runs SET status = 'cancelled', ts_end = ? WHERE run_id = ?",
                            (time.time_ns(), run_id),
                        )
                        runs_conn.commit()
                        with _jobs_lock:
                            explorer_jobs[run_id] = "cancelled"
                        return

        # Flush remaining
        if batch:
            runs_conn.executemany(INSERT_SQL, batch)
            runs_conn.commit()
            tracker.advance(len(batch))

        # -- Phase 9: Mark completed, cleanup --
        runs_conn.execute(
            "UPDATE runs SET status = 'completed', ts_end = ? WHERE run_id = ?",
            (time.time_ns(), run_id),
        )
        runs_conn.commit()

        try:
            _cleanup_old_explorations(runs_conn)
        except Exception:
            pass

        runs_conn.close()
        runs_conn = None

        with _jobs_lock:
            explorer_jobs[run_id] = "completed"

    except Exception as e:
        with _jobs_lock:
            explorer_jobs[run_id] = f"error: {e}"
        if runs_conn is not None:
            try:
                runs_conn.execute(
                    "UPDATE runs SET status = 'failed', ts_end = ? WHERE run_id = ?",
                    (time.time_ns(), run_id),
                )
                runs_conn.commit()
            except Exception:
                pass
    finally:
        if runs_conn is not None:
            try:
                runs_conn.close()
            except Exception:
                pass
        with _jobs_lock:
            _orchestrator_refs.pop(run_id, None)
            _cancel_events.pop(run_id, None)
