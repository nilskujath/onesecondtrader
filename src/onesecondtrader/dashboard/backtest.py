"""
Backtest execution logic for the dashboard.

Provides the request model, job tracking, and execution function for running
backtests from the dashboard UI.
"""

from __future__ import annotations

import enum
import sqlite3
import threading
import time
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .db import get_runs_db_path, get_secmaster_path
from . import registry


class BacktestRequest(BaseModel):
    """
    Request model for backtest execution.

    Attributes:
        strategy:
            Name of the strategy class to run.
        strategy_params:
            Dictionary of parameter overrides for the strategy.
        symbols:
            List of instrument symbols to trade.
        rtype:
            Bar period rtype code (32=second, 33=minute, 34=hour, 35=day).
        publisher_id:
            Publisher ID for data source selection.
        start_date:
            Optional start date in YYYY-MM-DD format.
        end_date:
            Optional end date in YYYY-MM-DD format.
    """

    strategy: str
    strategy_params: dict
    symbols: list[str]
    rtype: int
    publisher_id: int
    start_date: str | None = None
    end_date: str | None = None


running_jobs: dict[str, str] = {}
_orchestrator_refs: dict[str, Any] = {}
_running_metadata: dict[str, dict] = {}
_jobs_lock = threading.Lock()

RTYPE_TO_BAR_PERIOD = {32: "SECOND", 33: "MINUTE", 34: "HOUR", 35: "DAY"}


def deserialize_params(params: dict, param_specs: dict) -> dict:
    """
    Deserialize strategy parameters, converting enum strings to enum values.

    Parameters:
        params:
            Dictionary of parameter names to values from the request.
        param_specs:
            Dictionary of parameter names to ParamSpec instances.

    Returns:
        Dictionary with enum strings converted to their enum values.
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


def _ensure_db_status(db_run_id: str | None, status: str) -> None:
    """Force-update the run status in SQLite using a fresh connection."""
    if not db_run_id:
        return
    try:
        conn = sqlite3.connect(get_runs_db_path())
        conn.execute(
            "UPDATE runs SET status = ?, ts_end = ? WHERE run_id = ? AND status = 'running'",
            (status, time.time_ns(), db_run_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def run_backtest(request: BacktestRequest, run_id: str) -> None:
    """
    Execute a backtest in a background task.

    Configures and runs an Orchestrator with the specified strategy, symbols,
    and data source. Updates running_jobs with status during execution.

    Parameters:
        request:
            Backtest configuration from the API request.
        run_id:
            Unique identifier for tracking this backtest job.
    """
    from onesecondtrader.brokers.simulated import SimulatedBroker
    from onesecondtrader.datafeeds.simulated import SimulatedDatafeed
    from onesecondtrader.models import BarPeriod
    from onesecondtrader.orchestrator import Orchestrator
    from onesecondtrader.strategies import examples  # noqa: F401
    from onesecondtrader.strategies.base import ParamSpec

    try:
        with _jobs_lock:
            running_jobs[run_id] = "running"
            _running_metadata[run_id] = {
                "strategy": request.strategy,
                "symbols": request.symbols,
                "start_date": request.start_date,
                "end_date": request.end_date,
            }

        strategy_cls = registry.get_strategies().get(request.strategy)
        if not strategy_cls:
            with _jobs_lock:
                running_jobs[run_id] = "error: invalid strategy"
            return

        bar_period = BarPeriod[RTYPE_TO_BAR_PERIOD[request.rtype]]

        deserialized_params = deserialize_params(
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
            f"_Configured{request.strategy}",
            (strategy_cls,),
            {"symbols": request.symbols, "parameters": updated_parameters},
        )

        db_path = get_secmaster_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, dataset FROM publishers WHERE publisher_id = ?",
            (request.publisher_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            with _jobs_lock:
                running_jobs[run_id] = (
                    f"error: publisher_id {request.publisher_id} not found"
                )
            return
        publisher_name, dataset = row

        datafeed_attrs: dict[str, str | int] = {
            "publisher_name": publisher_name,
            "dataset": dataset,
            "symbol_type": "raw_symbol",
            "db_path": db_path,
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
            db_path = get_runs_db_path()
            mode = "backtest"
            start_date = request.start_date
            end_date = request.end_date

        orchestrator = ConfiguredOrchestrator(
            strategies=[configured_strategy],
            broker=SimulatedBroker,
            datafeed=configured_datafeed,
        )
        with _jobs_lock:
            _orchestrator_refs[run_id] = orchestrator
        try:
            orchestrator.run()
            _ensure_db_status(orchestrator.run_id, "completed")
            with _jobs_lock:
                running_jobs[run_id] = "completed"
        except Exception as e:
            _ensure_db_status(getattr(orchestrator, "run_id", None), "failed")
            with _jobs_lock:
                running_jobs[run_id] = f"error: {e}"
        finally:
            with _jobs_lock:
                _orchestrator_refs.pop(run_id, None)
                _running_metadata.pop(run_id, None)
    except Exception as e:
        with _jobs_lock:
            running_jobs[run_id] = f"error: {e}"
