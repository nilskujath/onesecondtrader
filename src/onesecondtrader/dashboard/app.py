from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

from onesecondtrader.indicators.base import discover_indicators
from onesecondtrader.strategies.base import discover_strategies

from .pages import backtest_page, chart_page, performance_page
from .routers import (
    runs_router,
    strategies_router,
    secmaster_router,
    presets_router,
    backtest_router,
)

discover_indicators()
discover_strategies()

app = FastAPI(title="OneSecondTrader Dashboard")

app.include_router(runs_router)
app.include_router(strategies_router)
app.include_router(secmaster_router)
app.include_router(presets_router)
app.include_router(backtest_router)


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
