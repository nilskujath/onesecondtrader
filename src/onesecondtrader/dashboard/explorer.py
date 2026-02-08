"""New exploration execution engine using the Orchestrator pattern.

Runs indicator computations through IndicatorExplorer strategy + Orchestrator,
ensuring identical computation behavior with backtesting.
"""

from __future__ import annotations

import enum
import inspect
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
from pydantic import BaseModel

from .db import get_runs_db_path, get_secmaster_path, connect_secmaster
from .explore import _cleanup_old_explorations

_executor = ThreadPoolExecutor(max_workers=1)

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


explorer_jobs: dict[str, str] = {}
_orchestrator_refs: dict[str, Any] = {}
_jobs_lock = threading.Lock()


def enqueue_exploration(request: ExplorerRequest, run_id: str) -> None:
    """Submit an exploration to the bounded thread pool."""
    with _jobs_lock:
        explorer_jobs[run_id] = "queued"
    _executor.submit(run_explorer, request, run_id)


def get_explorer_progress(run_id: str) -> float:
    """Return progress for an exploration run from the orchestrator ref."""
    with _jobs_lock:
        orch = _orchestrator_refs.get(run_id)
    if orch is not None:
        return orch.progress
    return 0.0


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
    """Execute an exploration in a background thread using the Orchestrator."""
    from onesecondtrader.brokers.simulated import SimulatedBroker
    from onesecondtrader.datafeeds.simulated import SimulatedDatafeed
    from onesecondtrader.models import BarPeriod
    from onesecondtrader.orchestrator import Orchestrator
    from onesecondtrader.strategies.base import ParamSpec
    from onesecondtrader.strategies.indicator_explorer import IndicatorExplorer

    try:
        with _jobs_lock:
            if explorer_jobs.get(run_id, "").startswith("error"):
                return
            explorer_jobs[run_id] = "running"

        # Resolve bar period
        bar_period_str = RTYPE_TO_BAR_PERIOD.get(request.rtype)
        if not bar_period_str:
            with _jobs_lock:
                explorer_jobs[run_id] = f"error: invalid rtype {request.rtype}"
            return
        bar_period = BarPeriod[bar_period_str]

        # Resolve publisher
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
        publisher_name, dataset = row

        # Instantiate indicators
        try:
            indicator_instances = _instantiate_indicators(request.indicators)
        except ValueError as e:
            with _jobs_lock:
                explorer_jobs[run_id] = f"error: {e}"
            return

        # Create configured strategy subclass
        configured_strategy = type(
            "_ConfiguredIndicatorExplorer",
            (IndicatorExplorer,),
            {
                "symbols": request.symbols,
                "parameters": {
                    "bar_period": ParamSpec(default=bar_period),
                },
            },
        )

        # Override setup to register the indicators
        _explorer_indicators = indicator_instances

        def custom_setup(self):
            for ind in _explorer_indicators:
                self.add_indicator(ind)

        configured_strategy.setup = custom_setup  # type: ignore[attr-defined]

        # Configure datafeed
        db_path = get_secmaster_path()
        datafeed_attrs: dict[str, str | int] = {
            "publisher_name": publisher_name,
            "dataset": dataset,
            "symbol_type": request.symbol_type,
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

        # Configure Orchestrator
        _run_id = run_id
        _request = request

        class ConfiguredOrchestrator(Orchestrator):
            db_path = get_runs_db_path()
            mode = "exploration"
            start_date = _request.start_date
            end_date = _request.end_date

            def _generate_run_id(self) -> str:
                return _run_id

            def _create_recorder(self, run_id):
                import pathlib
                from onesecondtrader.orchestrator.run_recorder import RunRecorder

                assert self._event_bus is not None
                config = {
                    "mode": "exploration",
                    "symbols": self._collect_symbols(),
                    "strategies": [s.name for s in self._strategy_classes],
                    "indicators": [
                        {"class_name": ic.class_name, "params": ic.params}
                        for ic in _request.indicators
                    ],
                    "rtype": _request.rtype,
                    "publisher_id": _request.publisher_id,
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                }
                indicator_names = ", ".join(ic.class_name for ic in _request.indicators)
                return RunRecorder(
                    event_bus=self._event_bus,
                    db_path=pathlib.Path(self.db_path),
                    run_id=run_id,
                    name=f"Explore: {indicator_names}",
                    config=config,
                )

        orchestrator = ConfiguredOrchestrator(
            strategies=[configured_strategy],
            broker=SimulatedBroker,
            datafeed=configured_datafeed,
        )
        with _jobs_lock:
            _orchestrator_refs[run_id] = orchestrator

        try:
            orchestrator.run()
            # Cleanup old exploration runs
            try:
                from .db import connect_runs

                with connect_runs() as conn:
                    _cleanup_old_explorations(conn)
            except Exception:
                pass

            with _jobs_lock:
                explorer_jobs[run_id] = "completed"
        except Exception as e:
            with _jobs_lock:
                explorer_jobs[run_id] = f"error: {e}"
        finally:
            with _jobs_lock:
                _orchestrator_refs.pop(run_id, None)

    except Exception as e:
        with _jobs_lock:
            explorer_jobs[run_id] = f"error: {e}"
