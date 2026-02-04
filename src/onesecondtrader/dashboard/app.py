"""
FastAPI application providing the dashboard REST API and page routes.

The application exposes endpoints for:

- Serving the backtest configuration page
- Querying and deleting run history from the runs database
- Listing registered strategies and their parameter schemas
- Querying publishers, datasets, and symbol coverage from the security master
- Managing symbol presets for quick backtest configuration
- Executing backtests as background tasks

Environment Variables:
    RUNS_DB_PATH: Path to the runs SQLite database. Defaults to `runs.db`.
    SECMASTER_DB_PATH: Path to the security master SQLite database. Defaults to `secmaster.db`.
"""

from __future__ import annotations

import enum
import json
import os
import sqlite3

import pandas as pd
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from .pages import backtest_page
from . import registry

app = FastAPI(title="OneSecondTrader Dashboard")

_running_jobs: dict[str, str] = {}


def _get_runs_db_path() -> str:
    """Return the path to the runs database from environment or default."""
    return os.environ.get("RUNS_DB_PATH", "runs.db")


def _get_runs(limit: int = 50) -> list[dict]:
    """
    Fetch recent runs from the runs database.

    Parameters:
        limit:
            Maximum number of runs to return.

    Returns:
        List of run dictionaries with run_id, name, timestamps, status, config, and metadata.
    """
    db_path = _get_runs_db_path()
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


@app.get("/", response_class=RedirectResponse)
async def index():
    """Redirect root path to the backtest page."""
    return RedirectResponse(url="/backtest", status_code=302)


@app.get("/backtest", response_class=HTMLResponse)
async def backtest():
    """Serve the backtest configuration page."""
    return backtest_page()


@app.get("/api/runs")
async def api_runs():
    """Return the list of recent backtest runs."""
    runs = _get_runs()
    return {"runs": runs}


class DeleteRunsRequest(BaseModel):
    """Request model for deleting runs."""

    run_ids: list[str]


_CHILD_TABLES = [
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


@app.delete("/api/runs")
async def api_delete_runs(request: DeleteRunsRequest):
    """
    Delete runs and their associated data from the runs database.

    Parameters:
        request:
            Request containing list of run IDs to delete.

    Returns:
        Dictionary with count of deleted runs.
    """
    db_path = _get_runs_db_path()
    if not os.path.exists(db_path):
        return {"deleted": 0}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    deleted = 0
    for run_id in request.run_ids:
        for table in _CHILD_TABLES:
            cursor.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
        deleted += cursor.rowcount
    conn.commit()
    conn.close()
    return {"deleted": deleted}


@app.get("/api/strategies")
async def api_strategies():
    """Return the list of registered strategy classes."""
    from onesecondtrader.strategies import examples  # noqa: F401

    strategies = registry.get_strategies()
    return {
        "strategies": [
            {"id": name, "name": cls.name} for name, cls in strategies.items()
        ]
    }


@app.get("/api/strategies/{name}")
async def api_strategy_schema(name: str):
    """
    Return the parameter schema for a strategy.

    Parameters:
        name:
            Class name of the strategy.

    Returns:
        Strategy schema with parameters, or error if not found.
    """
    from onesecondtrader.strategies import examples  # noqa: F401

    schema = registry.get_strategy_schema(name)
    if schema is None:
        return {"error": "Strategy not found"}
    return schema


def _get_secmaster_path() -> str:
    """Return the path to the security master database from environment or default."""
    return os.environ.get("SECMASTER_DB_PATH", "secmaster.db")


@app.get("/api/secmaster/publishers")
async def api_secmaster_publishers(rtype: int | None = None):
    """
    Return list of unique publisher names from the security master.

    Parameters:
        rtype:
            Optional bar period rtype to filter publishers that have data for that period.

    Returns:
        Dictionary with list of publisher name strings.
    """
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"publishers": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if rtype is not None:
        cursor.execute(
            "SELECT DISTINCT p.name FROM publishers p "
            "JOIN symbol_coverage sc ON p.publisher_id = sc.publisher_id "
            "WHERE sc.rtype = ? ORDER BY p.name",
            (rtype,),
        )
    else:
        cursor.execute("SELECT DISTINCT name FROM publishers ORDER BY name")
    publishers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"publishers": publishers}


@app.get("/api/secmaster/publishers/{name}/datasets")
async def api_secmaster_datasets(name: str, rtype: int | None = None):
    """
    Return datasets for a publisher from the security master.

    Parameters:
        name:
            Publisher name to get datasets for.
        rtype:
            Optional bar period rtype to filter datasets that have data for that period.

    Returns:
        Dictionary with list of dataset objects containing publisher_id and dataset name.
    """
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"datasets": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if rtype is not None:
        cursor.execute(
            "SELECT DISTINCT p.publisher_id, p.dataset FROM publishers p "
            "JOIN symbol_coverage sc ON p.publisher_id = sc.publisher_id "
            "WHERE p.name = ? AND sc.rtype = ? ORDER BY p.dataset",
            (name, rtype),
        )
    else:
        cursor.execute(
            "SELECT publisher_id, dataset FROM publishers WHERE name = ? ORDER BY dataset",
            (name,),
        )
    datasets = [
        {"publisher_id": row[0], "dataset": row[1]} for row in cursor.fetchall()
    ]
    conn.close()
    return {"datasets": datasets}


@app.get("/api/secmaster/symbols_coverage")
async def api_secmaster_symbols_coverage(
    publisher_id: int | None = None, rtype: int | None = None
):
    """
    Return symbol coverage data from the security master.

    Parameters:
        publisher_id:
            Optional publisher ID to filter symbols.
        rtype:
            Optional bar period rtype to filter symbols.

    Returns:
        Dictionary with list of symbol coverage objects containing publisher_id,
        symbol, rtype, min_ts, and max_ts.
    """
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"symbols": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if publisher_id is not None and rtype is not None:
        cursor.execute(
            "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
            "WHERE publisher_id = ? AND rtype = ? ORDER BY symbol",
            (publisher_id, rtype),
        )
    elif publisher_id is not None:
        cursor.execute(
            "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
            "WHERE publisher_id = ? ORDER BY symbol, rtype",
            (publisher_id,),
        )
    elif rtype is not None:
        cursor.execute(
            "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage "
            "WHERE rtype = ? ORDER BY symbol",
            (rtype,),
        )
    else:
        cursor.execute(
            "SELECT publisher_id, symbol, rtype, min_ts, max_ts FROM symbol_coverage ORDER BY symbol, rtype"
        )
    symbols = [
        {
            "publisher_id": row[0],
            "symbol": row[1],
            "rtype": row[2],
            "min_ts": row[3],
            "max_ts": row[4],
        }
        for row in cursor.fetchall()
    ]
    conn.close()
    return {"symbols": symbols}


@app.get("/api/presets")
async def list_presets():
    """Return list of all symbol preset names."""
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"presets": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM symbol_presets ORDER BY name")
    presets = [row[0] for row in cursor.fetchall()]
    conn.close()
    return {"presets": presets}


@app.get("/api/presets/{name}")
async def get_preset(name: str):
    """
    Return a symbol preset by name.

    Parameters:
        name:
            Name of the preset to retrieve.

    Returns:
        Dictionary with preset name and list of symbols, or error if not found.
    """
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"error": "Preset not found"}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT symbols FROM symbol_presets WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return {"error": "Preset not found"}
    return {"name": name, "symbols": json.loads(row[0])}


class PresetRequest(BaseModel):
    """Request model for creating or updating a symbol preset."""

    name: str
    symbols: list[str]


@app.post("/api/presets")
async def create_preset(request: PresetRequest):
    """
    Create a new symbol preset.

    Parameters:
        request:
            Request containing preset name and list of symbols.

    Returns:
        Dictionary with status and preset name.
    """
    db_path = _get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO symbol_presets (name, symbols) VALUES (?, ?)",
        (request.name, json.dumps(request.symbols)),
    )
    conn.commit()
    conn.close()
    return {"status": "created", "name": request.name}


@app.put("/api/presets/{name}")
async def update_preset(name: str, request: PresetRequest):
    """
    Update an existing symbol preset.

    Parameters:
        name:
            Name of the preset to update.
        request:
            Request containing new symbols list.

    Returns:
        Dictionary with status and preset name.
    """
    db_path = _get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE symbol_presets SET symbols = ? WHERE name = ?",
        (json.dumps(request.symbols), name),
    )
    conn.commit()
    conn.close()
    return {"status": "updated", "name": name}


@app.delete("/api/presets/{name}")
async def delete_preset(name: str):
    """
    Delete a symbol preset.

    Parameters:
        name:
            Name of the preset to delete.

    Returns:
        Dictionary with status and preset name.
    """
    db_path = _get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM symbol_presets WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "name": name}


class BacktestRequest(BaseModel):
    """Request model for running a backtest."""

    strategy: str
    strategy_params: dict
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None


def _deserialize_params(params: dict, param_specs: dict) -> dict:
    """
    Deserialize strategy parameters from JSON values to Python types.

    Converts enum string names back to enum instances based on parameter specifications.

    Parameters:
        params:
            Dictionary of parameter names to JSON-serialized values.
        param_specs:
            Dictionary of parameter names to ParamSpec objects.

    Returns:
        Dictionary of parameter names to deserialized Python values.
    """
    result = {}
    for name, value in params.items():
        spec = param_specs.get(name)
        if spec is None:
            result[name] = value
            continue
        if isinstance(spec.default, enum.Enum):
            enum_cls = type(spec.default)
            result[name] = enum_cls[value]
        else:
            result[name] = value
    return result


_RTYPE_TO_BAR_PERIOD = {32: "SECOND", 33: "MINUTE", 34: "HOUR", 35: "DAY"}


def _run_backtest(request: BacktestRequest, run_id: str) -> None:
    """
    Execute a backtest as a background task.

    Creates configured strategy, datafeed, and orchestrator instances based on the
    request parameters and runs the backtest. Updates job status in _running_jobs.

    Parameters:
        request:
            Backtest configuration including strategy, symbols, and date range.
        run_id:
            Unique identifier for tracking job status.
    """
    from onesecondtrader.brokers.simulated import SimulatedBroker
    from onesecondtrader.datafeeds.simulated import SimulatedDatafeed
    from onesecondtrader.models import BarPeriod
    from onesecondtrader.orchestrator import Orchestrator
    from onesecondtrader.strategies import examples  # noqa: F401
    from onesecondtrader.strategies.base import ParamSpec

    try:
        _running_jobs[run_id] = "running"

        strategy_cls = registry.get_strategies().get(request.strategy)
        if not strategy_cls:
            _running_jobs[run_id] = "error: invalid strategy"
            return

        bar_period = BarPeriod[_RTYPE_TO_BAR_PERIOD[request.rtype]]

        deserialized_params = _deserialize_params(
            request.strategy_params, getattr(strategy_cls, "parameters", {})
        )

        updated_parameters = {}
        for name, spec in strategy_cls.parameters.items():
            if name == "bar_period":
                updated_parameters[name] = ParamSpec(default=bar_period)
            elif name in deserialized_params:
                updated_parameters[name] = type(spec)(
                    default=deserialized_params[name],
                    **{k: v for k, v in spec.__dict__.items() if k != "default"},
                )
            else:
                updated_parameters[name] = spec

        configured_strategy = type(
            f"Configured{request.strategy}",
            (strategy_cls,),
            {"symbols": request.symbols, "parameters": updated_parameters},
        )

        datafeed_attrs: dict[str, str | int] = {
            "publisher_name": "databento",
            "dataset": "XNAS.ITCH",
            "symbol_type": "raw_symbol",
            "db_path": _get_secmaster_path(),
        }
        if request.start_date:
            datafeed_attrs["start_ts"] = int(
                pd.Timestamp(request.start_date, tz="UTC").value
            )
        if request.end_date:
            end_dt = (
                pd.Timestamp(request.end_date, tz="UTC")
                + pd.Timedelta(days=1)
                - pd.Timedelta(1, unit="ns")
            )
            datafeed_attrs["end_ts"] = int(end_dt.value)

        configured_datafeed = type(
            "ConfiguredDatafeed", (SimulatedDatafeed,), datafeed_attrs
        )

        class ConfiguredOrchestrator(Orchestrator):
            db_path = _get_runs_db_path()
            mode = "backtest"
            start_date = request.start_date
            end_date = request.end_date

        orchestrator = ConfiguredOrchestrator(
            strategies=[configured_strategy],
            broker=SimulatedBroker,
            datafeed=configured_datafeed,
        )
        orchestrator.run()
        _running_jobs[run_id] = "completed"
    except Exception as e:
        _running_jobs[run_id] = f"error: {e}"


@app.post("/api/backtest/run")
async def api_backtest_run(request: BacktestRequest, background_tasks: BackgroundTasks):
    """
    Start a backtest as a background task.

    Parameters:
        request:
            Backtest configuration.
        background_tasks:
            FastAPI background tasks manager.

    Returns:
        Dictionary with run_id and initial status.
    """
    import uuid

    run_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_backtest, request, run_id)
    return {"run_id": run_id, "status": "started"}


@app.get("/api/backtest/status/{run_id}")
async def api_backtest_status(run_id: str):
    """
    Get the status of a running or completed backtest.

    Parameters:
        run_id:
            Unique identifier of the backtest job.

    Returns:
        Dictionary with run_id and current status.
    """
    status = _running_jobs.get(run_id, "not found")
    return {"run_id": run_id, "status": status}


@app.get("/health")
async def health():
    """Return health check status."""
    return {"status": "ok"}
