from __future__ import annotations

import os
import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from onesecondtrader.indicators.base import discover_indicators
from onesecondtrader.strategies.base import discover_strategies

from .db import get_runs_db_path
from .pages import backtest_page, chart_page, performance_page
from .routers import (
    runs_router,
    strategies_router,
    secmaster_router,
    presets_router,
    backtest_router,
)
from .routers.presets import ensure_presets_table

discover_indicators()
discover_strategies()

app = FastAPI(title="OneSecondTrader Dashboard")

app.include_router(runs_router)
app.include_router(strategies_router)
app.include_router(secmaster_router)
app.include_router(presets_router)
app.include_router(backtest_router)


def _cleanup_stale_runs() -> None:
    """Mark any leftover 'running' rows as 'aborted' on startup."""
    db_path = get_runs_db_path()
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE runs SET status = 'cancelled', ts_end = ts_start WHERE status = 'running'"
    )
    conn.commit()
    conn.close()


@app.on_event("startup")
async def startup():
    ensure_presets_table()
    _cleanup_stale_runs()


@app.get("/", response_class=RedirectResponse)
async def index():
    return RedirectResponse(url="/backtest", status_code=302)


@app.get("/backtest", response_class=HTMLResponse)
async def backtest():
    return backtest_page()


@app.get("/performance", response_class=HTMLResponse)
async def performance():
    return performance_page()


@app.get("/chart", response_class=HTMLResponse)
async def chart():
    return chart_page()


@app.get("/health")
async def health():
    return {"status": "ok"}
