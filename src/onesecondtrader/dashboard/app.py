from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from onesecondtrader.dashboard.indicators_util import discover_indicators
from onesecondtrader.strategies.base import discover_strategies

from .db import connect_runs
from .pages import backtest_page, explorer_page
from .routers import (
    runs_router,
    strategies_router,
    secmaster_router,
    presets_router,
    backtest_router,
    indicators_router,
    explore_router,
    explore_presets_router,
    condition_presets_router,
    explorer_router,
    charts_router,
    segments_router,
    bars_router,
    chart_settings_router,
)
from .routers.presets import ensure_presets_table
from .routers.explore import (
    ensure_explore_presets_table,
    ensure_condition_presets_table,
)

discover_indicators()
discover_strategies()

app = FastAPI(title="OneSecondTrader Dashboard")

_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

app.include_router(runs_router)
app.include_router(strategies_router)
app.include_router(secmaster_router)
app.include_router(presets_router)
app.include_router(backtest_router)
app.include_router(indicators_router)
app.include_router(explore_router)
app.include_router(explore_presets_router)
app.include_router(condition_presets_router)
app.include_router(explorer_router)
app.include_router(charts_router)
app.include_router(segments_router)
app.include_router(bars_router)
app.include_router(chart_settings_router)


def _cleanup_stale_runs() -> None:
    """Mark any leftover 'running' rows as 'aborted' on startup."""
    try:
        conn_ctx = connect_runs()
    except FileNotFoundError:
        return
    with conn_ctx as conn:
        conn.execute(
            "UPDATE runs SET status = 'cancelled', ts_end = ts_start WHERE status = 'running'"
        )
        conn.commit()


@app.on_event("startup")
async def startup():
    ensure_presets_table()
    ensure_explore_presets_table()
    ensure_condition_presets_table()
    _cleanup_stale_runs()


@app.get("/", response_class=RedirectResponse)
async def index():
    return RedirectResponse(url="/backtest", status_code=302)


@app.get("/backtest", response_class=HTMLResponse)
async def backtest():
    return backtest_page()


@app.get("/explorer", response_class=HTMLResponse)
async def explorer():
    return explorer_page()


@app.get("/health")
async def health():
    return {"status": "ok"}
