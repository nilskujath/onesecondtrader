from __future__ import annotations

import enum
import os
import sqlite3

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from onesecondtrader.orchestrator import Orchestrator
from onesecondtrader.connectors.brokers import SimulatedBroker
from onesecondtrader.connectors.datafeeds import SimulatedDatafeed
from . import registry

app = FastAPI(title="OneSecondTrader Dashboard")

_running_jobs: dict[str, str] = {}

RTYPE_TO_BAR_PERIOD = {32: "SECOND", 33: "MINUTE", 34: "HOUR", 35: "DAY"}
BAR_PERIOD_TO_RTYPE = {"SECOND": 32, "MINUTE": 33, "HOUR": 34, "DAY": 35}
BAR_PERIOD_ENUM_TO_NAME = {1: "SECOND", 2: "MINUTE", 3: "HOUR", 4: "DAY"}


def _normalize_bar_period(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        if value in BAR_PERIOD_TO_RTYPE:
            return value
        try:
            value = int(value)
        except ValueError:
            return value
    if isinstance(value, int):
        return BAR_PERIOD_ENUM_TO_NAME.get(value, str(value))
    return str(value)


def _get_secmaster_path() -> str:
    return os.environ.get("SECMASTER_DB_PATH", "secmaster.db")


def _get_available_symbols(bar_period: str | None = None) -> list[str]:
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if bar_period and bar_period in BAR_PERIOD_TO_RTYPE:
        rtype = BAR_PERIOD_TO_RTYPE[bar_period]
        cursor.execute(
            "SELECT DISTINCT symbol FROM symbol_coverage WHERE rtype = ? ORDER BY symbol",
            (rtype,),
        )
    else:
        cursor.execute("SELECT DISTINCT symbol FROM symbol_coverage ORDER BY symbol")
    symbols = [row[0] for row in cursor.fetchall()]
    conn.close()
    return symbols


def _get_symbols_with_coverage(bar_period: str) -> list[dict]:
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path) or bar_period not in BAR_PERIOD_TO_RTYPE:
        return []

    rtype = BAR_PERIOD_TO_RTYPE[bar_period]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT symbol, min_ts, max_ts FROM symbol_coverage WHERE rtype = ? ORDER BY symbol",
        (rtype,),
    )
    symbols = [
        {"symbol": row[0], "min_ts": row[1], "max_ts": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return symbols


def _get_available_bar_periods() -> list[str]:
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT rtype FROM symbol_coverage ORDER BY rtype")
    periods = [
        RTYPE_TO_BAR_PERIOD[row[0]]
        for row in cursor.fetchall()
        if row[0] in RTYPE_TO_BAR_PERIOD
    ]
    conn.close()
    return periods


BASE_STYLE = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
    display: flex;
}
.sidebar {
    width: 220px;
    background: #161b22;
    border-right: 1px solid #30363d;
    min-height: 100vh;
    position: fixed;
    left: 0;
    top: 0;
    display: flex;
    flex-direction: column;
}
.sidebar-header {
    padding: 20px 16px;
    border-bottom: 1px solid #30363d;
}
.sidebar-header h1 {
    font-size: 16px;
    font-weight: 600;
    color: #e6edf3;
}
.sidebar-nav {
    padding: 12px 8px;
    flex: 1;
}
.sidebar-nav a {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    color: #8b949e;
    text-decoration: none;
    font-size: 14px;
    border-radius: 6px;
    margin-bottom: 2px;
}
.sidebar-nav a:hover {
    background: #21262d;
    color: #e6edf3;
}
.sidebar-nav a.active {
    background: #21262d;
    color: #e6edf3;
}
.sidebar-nav svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
}
.main-content {
    margin-left: 220px;
    flex: 1;
    min-height: 100vh;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 24px;
}
.card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 16px;
}
.card h2 {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 16px;
    color: #e6edf3;
}
.empty-state {
    text-align: center;
    padding: 48px;
    color: #8b949e;
}
.empty-state p { margin-top: 8px; font-size: 14px; }
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}
.badge-green { background: #238636; color: #fff; }
.badge-yellow { background: #9e6a03; color: #fff; }
.badge-red { background: #da3633; color: #fff; }
"""


SIDEBAR_HTML = """
<aside class="sidebar">
    <div class="sidebar-header">
        <h1>OneSecondTrader</h1>
    </div>
    <nav class="sidebar-nav">
        <a href="/" class="{runs_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            Runs
        </a>
        <a href="/backtest" class="{backtest_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            Backtest
        </a>
        <a href="/secmaster" class="{secmaster_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
            Securities Master
        </a>
    </nav>
</aside>
"""


RUNS_STYLE = """
.runs-table { width: 100%; border-collapse: collapse; }
.runs-table th, .runs-table td { padding: 12px; text-align: left; border-bottom: 1px solid #30363d; }
.runs-table th { font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: 500; }
.runs-table tbody tr { cursor: pointer; }
.runs-table tbody tr:hover { background: #21262d; }
.runs-table .symbols { font-family: monospace; font-size: 12px; color: #8b949e; }
.runs-table .date-range { font-size: 12px; color: #8b949e; }
.runs-table .delete-btn { background: none; border: none; cursor: pointer; padding: 4px 8px; color: #8b949e; font-size: 16px; border-radius: 4px; }
.runs-table .delete-btn:hover { background: #f8514926; color: #f85149; }
.runs-table .actions { text-align: center; width: 50px; }
"""

RUNS_SCRIPT = """
async function deleteRun(runId, event) {
    event.stopPropagation();
    if (!confirm('Delete this run? This cannot be undone.')) return;
    const res = await fetch(`/api/run/${runId}`, { method: 'DELETE' });
    if (res.ok) loadRuns();
    else alert('Failed to delete run');
}
async function loadRuns() {
    const container = document.getElementById('runs-content');
    const res = await fetch('/api/runs');
    const data = await res.json();
    if (!data.runs || data.runs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No runs yet.</p>
                <p>Run a strategy with RunRecorder to see results here.</p>
            </div>
        `;
        return;
    }
    const rows = data.runs.map(r => {
        const statusClass = r.status === 'completed' ? 'badge-green' : r.status === 'running' ? 'badge-yellow' : 'badge-red';
        const createdAt = r.created_at ? r.created_at.split('T')[0] + ' ' + r.created_at.split('T')[1].split('.')[0] : '-';
        const dateRange = r.first_bar && r.last_bar
            ? r.first_bar.split('T')[0] + ' → ' + r.last_bar.split('T')[0]
            : '-';
        return `<tr onclick="window.location='/run/${r.run_id}'">
            <td>${createdAt}</td>
            <td>${r.strategy}</td>
            <td class="symbols">${r.symbols.length}</td>
            <td>${r.bar_period || '-'}</td>
            <td class="date-range">${dateRange}</td>
            <td><span class="badge ${statusClass}">${r.status}</span></td>
            <td class="actions"><button class="delete-btn" onclick="deleteRun('${r.run_id}', event)" title="Delete run">🗑</button></td>
        </tr>`;
    }).join('');
    container.innerHTML = `
        <table class="runs-table">
            <thead><tr><th>Created</th><th>Strategy</th><th>Symbols</th><th>Bar Period</th><th>Date Range</th><th>Status</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}
document.addEventListener('DOMContentLoaded', loadRuns);
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    sidebar = SIDEBAR_HTML.format(
        runs_active="active", backtest_active="", secmaster_active=""
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OneSecondTrader Dashboard</title>
        <style>{BASE_STYLE}{RUNS_STYLE}</style>
    </head>
    <body>
        {sidebar}
        <main class="main-content">
            <div class="container">
                <div class="card">
                    <h2>Recent Runs</h2>
                    <div id="runs-content">
                        <p style="color: #8b949e;">Loading...</p>
                    </div>
                </div>
            </div>
        </main>
        <script>{RUNS_SCRIPT}</script>
    </body>
    </html>
    """


RUN_DETAIL_STYLE = """
.run-header { margin-bottom: 24px; }
.run-header h2 { margin-bottom: 8px; }
.run-meta { display: flex; gap: 24px; flex-wrap: wrap; color: #8b949e; font-size: 14px; }
.run-meta span { display: flex; align-items: center; gap: 6px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }
.stat-card .label { font-size: 12px; color: #8b949e; margin-bottom: 4px; }
.stat-card .value { font-size: 24px; font-weight: 600; }
.back-link { color: #58a6ff; text-decoration: none; font-size: 14px; display: inline-block; margin-bottom: 16px; }
.back-link:hover { text-decoration: underline; }
.positions-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
.positions-table th { text-align: left; padding: 12px 8px; border-bottom: 1px solid #30363d; color: #8b949e; font-weight: 500; }
.positions-table td { padding: 10px 8px; border-bottom: 1px solid #21262d; }
.positions-table tr:hover { background: #161b22; }
.pnl-positive { color: #3fb950; }
.pnl-negative { color: #f85149; }
.side-long { color: #3fb950; }
.side-short { color: #f85149; }
.positions-summary { display: flex; gap: 24px; margin-bottom: 16px; padding: 12px; background: #161b22; border-radius: 6px; }
.positions-summary .item { display: flex; flex-direction: column; }
.positions-summary .item-label { font-size: 11px; color: #8b949e; text-transform: uppercase; }
.positions-summary .item-value { font-size: 18px; font-weight: 600; }
.positions-filter { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.positions-filter select { background: #21262d; border: 1px solid #30363d; border-radius: 6px; padding: 8px 12px; color: #c9d1d9; font-size: 14px; min-width: 150px; }
.positions-filter select:focus { outline: none; border-color: #58a6ff; }
.positions-filter label { color: #8b949e; font-size: 14px; }
"""

RUN_DETAIL_SCRIPT = """
let allPositions = [];
function formatTime(ts) {
    if (!ts) return '-';
    return ts.split('T')[0] + ' ' + ts.split('T')[1].split('.')[0];
}
function formatPnl(pnl) {
    const cls = pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
    const sign = pnl >= 0 ? '+' : '';
    return `<span class="${cls}">${sign}$${pnl.toFixed(2)}</span>`;
}
function computeSummary(positions) {
    const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0);
    const winners = positions.filter(p => p.pnl > 0).length;
    const losers = positions.filter(p => p.pnl < 0).length;
    const winRate = positions.length > 0 ? winners / positions.length : 0;
    return { total_positions: positions.length, total_pnl: totalPnl, winners, losers, win_rate: winRate };
}
function renderPositions(positions, selectedSymbol) {
    const filtered = selectedSymbol ? positions.filter(p => p.symbol === selectedSymbol) : positions;
    const s = computeSummary(filtered);
    const winRate = s.win_rate ? (s.win_rate * 100).toFixed(1) + '%' : '-';
    const summaryPnlClass = s.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
    document.getElementById('summary-pnl').className = 'item-value ' + summaryPnlClass;
    document.getElementById('summary-pnl').textContent = (s.total_pnl >= 0 ? '+' : '') + '$' + s.total_pnl.toFixed(2);
    document.getElementById('summary-positions').textContent = s.total_positions;
    document.getElementById('summary-winners').textContent = s.winners;
    document.getElementById('summary-losers').textContent = s.losers;
    document.getElementById('summary-winrate').textContent = winRate;
    const tbody = document.getElementById('positions-tbody');
    tbody.innerHTML = filtered.map((p, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>${p.symbol}</td>
            <td class="${p.side === 'LONG' ? 'side-long' : 'side-short'}">${p.side}</td>
            <td>${p.quantity}</td>
            <td>${formatTime(p.entry_time)}</td>
            <td>${formatTime(p.exit_time)}</td>
            <td>$${p.avg_entry_price.toFixed(2)}</td>
            <td>$${p.avg_exit_price.toFixed(2)}</td>
            <td>${formatPnl(p.pnl)}</td>
        </tr>
    `).join('');
}
function onSymbolFilterChange() {
    const sel = document.getElementById('symbol-filter');
    renderPositions(allPositions, sel.value);
}
async function loadRunDetail() {
    const runId = window.location.pathname.split('/run/')[1];
    const container = document.getElementById('run-content');
    const [runRes, posRes] = await Promise.all([
        fetch(`/api/run/${runId}`),
        fetch(`/api/run/${runId}/positions`)
    ]);
    if (!runRes.ok) {
        container.innerHTML = '<p style="color: #f85149;">Run not found.</p>';
        return;
    }
    const r = await runRes.json();
    const posData = await posRes.json();
    allPositions = posData.positions || [];
    const statusClass = r.status === 'completed' ? 'badge-green' : r.status === 'running' ? 'badge-yellow' : 'badge-red';
    const createdAt = formatTime(r.created_at);
    const dateRange = r.first_bar && r.last_bar
        ? r.first_bar.split('T')[0] + ' → ' + r.last_bar.split('T')[0]
        : '-';
    const symbols = [...new Set(allPositions.map(p => p.symbol))].sort();
    const s = computeSummary(allPositions);
    const winRate = s.win_rate ? (s.win_rate * 100).toFixed(1) + '%' : '-';
    let positionsHtml = '';
    if (allPositions.length > 0) {
        const summaryPnlClass = s.total_pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
        const symbolOptions = symbols.map(sym => `<option value="${sym}">${sym}</option>`).join('');
        positionsHtml = `
            <div class="card" style="margin-top: 24px;">
                <h3>Positions (Round-Trip Trades)</h3>
                <div class="positions-filter">
                    <label for="symbol-filter">Filter by Symbol:</label>
                    <select id="symbol-filter" onchange="onSymbolFilterChange()">
                        <option value="">All Symbols</option>
                        ${symbolOptions}
                    </select>
                </div>
                <div class="positions-summary">
                    <div class="item">
                        <span class="item-label">Total P&L</span>
                        <span id="summary-pnl" class="item-value ${summaryPnlClass}">${s.total_pnl >= 0 ? '+' : ''}$${s.total_pnl.toFixed(2)}</span>
                    </div>
                    <div class="item">
                        <span class="item-label">Positions</span>
                        <span id="summary-positions" class="item-value">${s.total_positions}</span>
                    </div>
                    <div class="item">
                        <span class="item-label">Winners</span>
                        <span id="summary-winners" class="item-value pnl-positive">${s.winners}</span>
                    </div>
                    <div class="item">
                        <span class="item-label">Losers</span>
                        <span id="summary-losers" class="item-value pnl-negative">${s.losers}</span>
                    </div>
                    <div class="item">
                        <span class="item-label">Win Rate</span>
                        <span id="summary-winrate" class="item-value">${winRate}</span>
                    </div>
                </div>
                <table class="positions-table">
                    <thead>
                        <tr>
                            <th>#</th><th>Symbol</th><th>Side</th><th>Qty</th>
                            <th>Entry Time</th><th>Exit Time</th><th>Avg Entry</th><th>Avg Exit</th><th>P&L</th>
                        </tr>
                    </thead>
                    <tbody id="positions-tbody"></tbody>
                </table>
            </div>
        `;
    } else {
        positionsHtml = `
            <div class="card" style="margin-top: 24px;">
                <h3>Positions (Round-Trip Trades)</h3>
                <p style="color: #8b949e;">No completed positions.</p>
            </div>
        `;
    }

    container.innerHTML = `
        <a href="/" class="back-link">← Back to Runs</a>
        <div class="run-header">
            <h2>${r.strategy}</h2>
            <div class="run-meta">
                <span><span class="badge ${statusClass}">${r.status}</span></span>
                <span>Created: ${createdAt}</span>
                <span>Mode: ${r.mode}</span>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Symbols</div>
                <div class="value">${r.symbols.length}</div>
            </div>
            <div class="stat-card">
                <div class="label">Bar Period</div>
                <div class="value">${r.bar_period || '-'}</div>
            </div>
            <div class="stat-card">
                <div class="label">Total Bars</div>
                <div class="value">${r.bar_count || 0}</div>
            </div>
            <div class="stat-card">
                <div class="label">Date Range</div>
                <div class="value" style="font-size: 14px;">${dateRange}</div>
            </div>
        </div>
        <div class="card">
            <h3>Symbols</h3>
            <p style="color: #8b949e; font-family: monospace;">${r.symbols.join(', ') || 'None'}</p>
        </div>
        ${positionsHtml}
    `;
    if (allPositions.length > 0) {
        renderPositions(allPositions, '');
    }
}
document.addEventListener('DOMContentLoaded', loadRunDetail);
"""


@app.get("/run/{run_id}", response_class=HTMLResponse)
async def run_detail_page(run_id: str):
    sidebar = SIDEBAR_HTML.format(
        runs_active="active", backtest_active="", secmaster_active=""
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Run Detail - OneSecondTrader</title>
        <style>{BASE_STYLE}{RUN_DETAIL_STYLE}</style>
    </head>
    <body>
        {sidebar}
        <main class="main-content">
            <div class="container">
                <div id="run-content">
                    <p style="color: #8b949e;">Loading...</p>
                </div>
            </div>
        </main>
        <script>{RUN_DETAIL_SCRIPT}</script>
    </body>
    </html>
    """


def _get_runs_db_path() -> str:
    return os.environ.get("RUNS_DB_PATH", "runs.db")


def _get_recent_runs(limit: int = 50) -> list[dict]:
    import json

    db_path = _get_runs_db_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            r.run_id,
            r.strategy,
            r.symbols,
            r.bar_period,
            r.mode,
            r.status,
            r.created_at,
            r.completed_at,
            COUNT(b.id) as bar_count,
            MIN(b.ts_event) as first_bar,
            MAX(b.ts_event) as last_bar
        FROM runs r
        LEFT JOIN bars b ON r.run_id = b.run_id
        GROUP BY r.run_id
        ORDER BY r.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    runs = []
    for row in cursor.fetchall():
        runs.append(
            {
                "run_id": row[0],
                "strategy": row[1],
                "symbols": json.loads(row[2]) if row[2] else [],
                "bar_period": _normalize_bar_period(row[3]),
                "mode": row[4],
                "status": row[5],
                "created_at": row[6],
                "completed_at": row[7],
                "bar_count": row[8],
                "first_bar": row[9],
                "last_bar": row[10],
            }
        )
    conn.close()
    return runs


@app.get("/api/runs")
async def list_runs(limit: int = 50):
    return {"runs": _get_recent_runs(limit)}


def _get_run_by_id(run_id: str) -> dict | None:
    import json

    db_path = _get_runs_db_path()
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            r.run_id,
            r.strategy,
            r.symbols,
            r.bar_period,
            r.mode,
            r.status,
            r.created_at,
            r.completed_at,
            COUNT(b.id) as bar_count,
            MIN(b.ts_event) as first_bar,
            MAX(b.ts_event) as last_bar
        FROM runs r
        LEFT JOIN bars b ON r.run_id = b.run_id
        WHERE r.run_id = ?
        GROUP BY r.run_id
        """,
        (run_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "run_id": row[0],
        "strategy": row[1],
        "symbols": json.loads(row[2]) if row[2] else [],
        "bar_period": _normalize_bar_period(row[3]),
        "mode": row[4],
        "status": row[5],
        "created_at": row[6],
        "completed_at": row[7],
        "bar_count": row[8],
        "first_bar": row[9],
        "last_bar": row[10],
    }


@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    run = _get_run_by_id(run_id)
    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    return run


@app.delete("/api/run/{run_id}")
async def delete_run(run_id: str):
    db_path = _get_runs_db_path()
    if not os.path.exists(db_path):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Run not found")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bars WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM order_requests WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM order_responses WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM fills WHERE run_id = ?", (run_id,))
    cursor.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    conn.commit()
    conn.close()
    return {"status": "deleted"}


def _normalize_side(side) -> str:
    if side in ("BUY", 1, "1"):
        return "BUY"
    return "SELL"


def _extract_positions(fills: list[dict]) -> list[dict]:
    if not fills:
        return []
    for f in fills:
        f["side"] = _normalize_side(f["side"])
    positions = []
    by_symbol: dict[str, list[dict]] = {}
    for f in fills:
        by_symbol.setdefault(f["symbol"], []).append(f)
    for symbol, symbol_fills in by_symbol.items():
        symbol_fills.sort(key=lambda x: x["ts_event"])
        position = 0.0
        position_fills: list[dict] = []
        position_id = 0
        for fill in symbol_fills:
            qty = fill["quantity"]
            signed_qty = qty if fill["side"] == "BUY" else -qty
            new_position = position + signed_qty
            position_fills.append(fill)
            if new_position == 0.0 and position != 0.0:
                position_id += 1
                pnl = 0.0
                total_commission = 0.0
                for pf in position_fills:
                    value = pf["price"] * pf["quantity"]
                    commission = pf.get("commission") or 0.0
                    total_commission += commission
                    if pf["side"] == "BUY":
                        pnl -= value
                    else:
                        pnl += value
                pnl -= total_commission
                entry_fill = position_fills[0]
                exit_fill = position_fills[-1]
                entry_side = entry_fill["side"]
                entry_qty = sum(
                    pf["quantity"] for pf in position_fills if pf["side"] == entry_side
                )
                entry_value = sum(
                    pf["quantity"] * pf["price"]
                    for pf in position_fills
                    if pf["side"] == entry_side
                )
                avg_entry = entry_value / entry_qty if entry_qty else 0
                exit_side = "SELL" if entry_side == "BUY" else "BUY"
                exit_qty = sum(
                    pf["quantity"] for pf in position_fills if pf["side"] == exit_side
                )
                exit_value = sum(
                    pf["quantity"] * pf["price"]
                    for pf in position_fills
                    if pf["side"] == exit_side
                )
                avg_exit = exit_value / exit_qty if exit_qty else 0
                positions.append(
                    {
                        "position_id": position_id,
                        "symbol": symbol,
                        "side": "LONG" if entry_side == "BUY" else "SHORT",
                        "quantity": entry_qty,
                        "entry_time": entry_fill["ts_event"],
                        "exit_time": exit_fill["ts_event"],
                        "avg_entry_price": avg_entry,
                        "avg_exit_price": avg_exit,
                        "pnl": pnl,
                        "commission": total_commission,
                        "num_fills": len(position_fills),
                    }
                )
                position_fills = []
            position = new_position
    positions.sort(key=lambda x: x["entry_time"])
    return positions


@app.get("/api/run/{run_id}/positions")
async def get_run_positions(run_id: str):
    db_path = _get_runs_db_path()
    if not os.path.exists(db_path):
        return {"positions": []}
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ts_event, symbol, side, quantity, price, commission
        FROM fills WHERE run_id = ? ORDER BY ts_event
        """,
        (run_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    fills = [
        {
            "ts_event": row[0],
            "symbol": row[1],
            "side": row[2],
            "quantity": row[3],
            "price": row[4],
            "commission": row[5],
        }
        for row in rows
    ]
    positions = _extract_positions(fills)
    total_pnl = sum(p["pnl"] for p in positions)
    winners = sum(1 for p in positions if p["pnl"] > 0)
    losers = sum(1 for p in positions if p["pnl"] < 0)
    return {
        "positions": positions,
        "summary": {
            "total_positions": len(positions),
            "total_pnl": total_pnl,
            "winners": winners,
            "losers": losers,
            "win_rate": winners / len(positions) if positions else 0,
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/strategies")
async def list_strategies():
    strategies = []
    for class_name, cls in registry.get_strategies().items():
        display_name = getattr(cls, "name", "") or class_name
        strategies.append({"class_name": class_name, "display_name": display_name})
    return {"strategies": strategies}


@app.get("/api/brokers")
async def list_brokers():
    return {"brokers": list(registry.get_brokers().keys())}


@app.get("/api/datafeeds")
async def list_datafeeds():
    return {"datafeeds": list(registry.get_datafeeds().keys())}


@app.get("/api/strategies/{name}")
async def get_strategy(name: str):
    schema = registry.get_strategy_schema(name)
    if schema is None:
        return {"error": "Strategy not found"}
    return schema


@app.get("/api/brokers/{name}")
async def get_broker(name: str):
    schema = registry.get_broker_schema(name)
    if schema is None:
        return {"error": "Broker not found"}
    return schema


@app.get("/api/datafeeds/{name}")
async def get_datafeed(name: str):
    schema = registry.get_datafeed_schema(name)
    if schema is None:
        return {"error": "Datafeed not found"}
    return schema


@app.get("/api/secmaster/symbols")
async def get_symbols(bar_period: str | None = None):
    return {"symbols": _get_available_symbols(bar_period)}


@app.get("/api/secmaster/symbols_coverage")
async def get_symbols_coverage(bar_period: str):
    return {"symbols": _get_symbols_with_coverage(bar_period)}


@app.get("/api/secmaster/bar_periods")
async def get_bar_periods():
    return {"bar_periods": _get_available_bar_periods()}


@app.get("/api/presets")
async def list_presets():
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
    import json

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
    name: str
    symbols: list[str]


@app.post("/api/presets")
async def create_preset(request: PresetRequest):
    import json

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
    import json

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
    db_path = _get_secmaster_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM symbol_presets WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return {"status": "deleted", "name": name}


class BacktestRequest(BaseModel):
    strategy: str
    strategy_params: dict
    symbols: list[str]
    start_date: str | None = None
    end_date: str | None = None


def _run_backtest(request: BacktestRequest, run_id: str) -> None:
    import pandas as pd

    try:
        _running_jobs[run_id] = "running"

        strategy_cls = registry.get_strategies().get(request.strategy)
        if not strategy_cls:
            _running_jobs[run_id] = "error: invalid strategy"
            return

        strategy_params = _deserialize_params(
            request.strategy_params, getattr(strategy_cls, "parameters", {})
        )

        updated_parameters = {}
        for name, spec in strategy_cls.parameters.items():
            if name in strategy_params:
                updated_parameters[name] = type(spec)(
                    default=strategy_params[name],
                    **{k: v for k, v in spec.__dict__.items() if k != "default"},
                )
            else:
                updated_parameters[name] = spec

        configured_strategy = type(
            f"Configured{request.strategy}",
            (strategy_cls,),
            {"symbols": request.symbols, "parameters": updated_parameters},
        )

        datafeed_attrs = {}
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
            "ConfiguredSimulatedDatafeed",
            (SimulatedDatafeed,),
            datafeed_attrs,
        )

        configured_orchestrator = type(
            "ConfiguredOrchestrator",
            (Orchestrator,),
            {"mode": "backtest"},
        )

        orchestrator = configured_orchestrator(
            strategies=[configured_strategy],
            broker=SimulatedBroker,
            datafeed=configured_datafeed,
        )

        orchestrator.run()
        _running_jobs[run_id] = "completed"
    except Exception as e:
        _running_jobs[run_id] = f"error: {e}"


def _deserialize_params(params: dict, param_specs: dict) -> dict:
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


@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    import uuid

    run_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_backtest, request, run_id)
    return {"run_id": run_id, "status": "started"}


@app.get("/api/backtest/status/{run_id}")
async def backtest_status(run_id: str):
    status = _running_jobs.get(run_id, "not found")
    return {"run_id": run_id, "status": status}


BACKTEST_FORM_STYLE = """
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; color: #8b949e; }
.form-group select, .form-group input {
    width: 100%; padding: 8px 12px; background: #0d1117; border: 1px solid #30363d;
    border-radius: 6px; color: #e6edf3; font-size: 14px;
}
.form-group select:focus, .form-group input:focus { outline: none; border-color: #58a6ff; }
.params-container { margin-top: 12px; padding: 12px; background: #0d1117; border-radius: 6px; }
.param-row { display: flex; gap: 12px; margin-bottom: 8px; align-items: center; }
.param-row label { min-width: 120px; font-size: 13px; }
.param-row input, .param-row select { flex: 1; }
.btn { padding: 10px 20px; background: #238636; border: none; border-radius: 6px;
    color: #fff; font-size: 14px; cursor: pointer; }
.btn:hover { background: #2ea043; }
.btn:disabled { background: #30363d; cursor: not-allowed; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-secondary { background: #30363d; }
.btn-secondary:hover { background: #484f58; }
.btn-danger { background: #da3633; }
.btn-danger:hover { background: #f85149; }
#status { margin-top: 16px; padding: 12px; border-radius: 6px; display: none; }
.status-running { background: #9e6a03; }
.status-completed { background: #238636; }
.status-error { background: #da3633; }
.date-row { display: flex; gap: 12px; }
.date-row .form-group { flex: 1; margin-bottom: 0; }
.symbol-section { background: #0d1117; border-radius: 6px; padding: 12px; }
.preset-row { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
.preset-row select { flex: 1; }
.preset-row input { flex: 1; }
.search-row { display: flex; gap: 8px; margin-bottom: 8px; }
.search-row input { flex: 1; }
.search-results { max-height: 150px; overflow-y: auto; border: 1px solid #30363d; border-radius: 4px; margin-bottom: 12px; }
.search-results:empty { display: none; }
.search-result { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-bottom: 1px solid #21262d; }
.search-result:last-child { border-bottom: none; }
.search-result:hover { background: #161b22; }
.search-result .symbol { font-family: monospace; }
.selected-symbols { display: flex; flex-wrap: wrap; gap: 6px; min-height: 32px; max-height: 150px; overflow-y: auto; }
.selected-tag { display: inline-flex; align-items: center; gap: 4px; background: #238636; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-family: monospace; }
.selected-tag .remove { cursor: pointer; opacity: 0.7; }
.selected-tag .remove:hover { opacity: 1; }
.selected-label { font-size: 13px; color: #8b949e; margin-bottom: 6px; }
.section-header { font-size: 14px; color: #8b949e; margin-bottom: 6px; margin-top: 8px; }
"""

BACKTEST_FORM_SCRIPT = """
let strategyParams = [];
let symbolCoverage = {};
let allSymbols = [];
let selectedSymbols = [];
let presets = [];
let barPeriods = [];
let currentBarPeriod = '';
let globalMinTs = null;
let globalMaxTs = null;
let globalMinDate = null;
let globalMaxDate = null;

async function loadStrategies() {
    const res = await fetch('/api/strategies');
    const data = await res.json();
    const sel = document.getElementById('strategy');
    data.strategies.forEach(s => sel.innerHTML += `<option value="${s.class_name}">${s.display_name}</option>`);
    if (data.strategies.length > 0) { sel.value = data.strategies[0].class_name; loadStrategyParams(); }
}

async function loadBarPeriods() {
    const res = await fetch('/api/secmaster/bar_periods');
    const data = await res.json();
    barPeriods = data.bar_periods || [];
    const sel = document.getElementById('bar-period');
    sel.innerHTML = '';
    barPeriods.forEach(p => sel.innerHTML += `<option value="${p}">${p}</option>`);
    if (barPeriods.length > 0) {
        currentBarPeriod = barPeriods[0];
        sel.value = currentBarPeriod;
        await loadSymbolsForPeriod();
    }
}

async function onBarPeriodChange() {
    currentBarPeriod = document.getElementById('bar-period').value;
    selectedSymbols = [];
    renderSelectedSymbols();
    await loadSymbolsForPeriod();
    updateDateRange();
}

async function loadSymbolsForPeriod() {
    const res = await fetch(`/api/secmaster/symbols_coverage?bar_period=${currentBarPeriod}`);
    const data = await res.json();
    symbolCoverage = {};
    allSymbols = [];
    (data.symbols || []).forEach(s => {
        symbolCoverage[s.symbol] = {min_ts: s.min_ts, max_ts: s.max_ts};
        allSymbols.push(s.symbol);
    });
}

async function loadPresets() {
    const res = await fetch('/api/presets');
    const data = await res.json();
    presets = data.presets || [];
    renderPresetSelect();
}

function renderPresetSelect() {
    const sel = document.getElementById('preset-select');
    sel.innerHTML = '<option value="">-- Select Preset --</option>';
    presets.forEach(p => sel.innerHTML += `<option value="${p}">${p}</option>`);
}

async function loadPreset() {
    const name = document.getElementById('preset-select').value;
    if (!name) return;
    const res = await fetch(`/api/presets/${encodeURIComponent(name)}`);
    const data = await res.json();
    if (data.symbols) {
        selectedSymbols = data.symbols.filter(s => allSymbols.includes(s));
        renderSelectedSymbols();
        updateDateRange();
    }
}

async function savePreset() {
    const nameInput = document.getElementById('preset-name');
    const name = nameInput.value.trim();
    if (!name) { alert('Enter a preset name'); return; }
    if (selectedSymbols.length === 0) { alert('Select at least one symbol'); return; }
    const exists = presets.includes(name);
    const method = exists ? 'PUT' : 'POST';
    const url = exists ? `/api/presets/${encodeURIComponent(name)}` : '/api/presets';
    await fetch(url, {
        method, headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, symbols: selectedSymbols})
    });
    nameInput.value = '';
    await loadPresets();
    document.getElementById('preset-select').value = name;
}

async function deletePreset() {
    const name = document.getElementById('preset-select').value;
    if (!name) { alert('Select a preset to delete'); return; }
    if (!confirm(`Delete preset "${name}"?`)) return;
    await fetch(`/api/presets/${encodeURIComponent(name)}`, {method: 'DELETE'});
    await loadPresets();
    selectedSymbols = [];
    renderSelectedSymbols();
    updateDateRange();
}

function searchSymbols() {
    const query = document.getElementById('symbol-search').value.toUpperCase();
    const container = document.getElementById('search-results');
    if (query.length < 1) { container.innerHTML = ''; return; }
    const matches = allSymbols.filter(s => s.toUpperCase().includes(query) && !selectedSymbols.includes(s)).slice(0, 20);
    container.innerHTML = matches.map(s => `<div class="search-result"><span class="symbol">${s}</span><button class="btn btn-sm" onclick="addSymbol('${s}')">+</button></div>`).join('');
}

function addSymbol(symbol) {
    if (!selectedSymbols.includes(symbol)) {
        selectedSymbols.push(symbol);
        selectedSymbols.sort();
        renderSelectedSymbols();
        searchSymbols();
        updateDateRange();
    }
}

function removeSymbol(symbol) {
    selectedSymbols = selectedSymbols.filter(s => s !== symbol);
    renderSelectedSymbols();
    searchSymbols();
    updateDateRange();
}

function renderSelectedSymbols() {
    const container = document.getElementById('selected-symbols');
    const label = document.getElementById('selected-label');
    label.textContent = `Selected (${selectedSymbols.length}):`;
    container.innerHTML = selectedSymbols.map(s => `<span class="selected-tag">${s}<span class="remove" onclick="removeSymbol('${s}')">&times;</span></span>`).join('');
}

function updateDateRange() {
    if (selectedSymbols.length === 0) {
        globalMinTs = null;
        globalMaxTs = null;
        document.getElementById('start-date').value = '';
        document.getElementById('end-date').value = '';
        document.getElementById('range-slider-container').style.display = 'none';
        return;
    }
    let minTs = Infinity, maxTs = -Infinity;
    selectedSymbols.forEach(s => {
        const cov = symbolCoverage[s];
        if (cov) {
            if (cov.min_ts < minTs) minTs = cov.min_ts;
            if (cov.max_ts > maxTs) maxTs = cov.max_ts;
        }
    });
    if (minTs === Infinity) return;
    globalMinTs = minTs;
    globalMaxTs = maxTs;
    globalMinDate = tsToDate(minTs);
    globalMaxDate = tsToDate(maxTs);
    const startInput = document.getElementById('start-date');
    const endInput = document.getElementById('end-date');
    startInput.min = globalMinDate;
    startInput.max = globalMaxDate;
    startInput.value = globalMinDate;
    endInput.min = globalMinDate;
    endInput.max = globalMaxDate;
    endInput.value = globalMaxDate;
}

function tsToDate(ts) {
    return new Date(ts / 1000000).toISOString().split('T')[0];
}

function clampDate(inputId) {
    if (!globalMinDate || !globalMaxDate) return;
    const input = document.getElementById(inputId);
    if (input.value < globalMinDate) input.value = globalMinDate;
    if (input.value > globalMaxDate) input.value = globalMaxDate;
}

async function loadStrategyParams() {
    const name = document.getElementById('strategy').value;
    const res = await fetch(`/api/strategies/${name}`);
    const data = await res.json();
    strategyParams = (data.parameters || []).filter(p => p.name !== 'bar_period');
    renderParams('strategy-params', strategyParams, 'sp_');
}

function formatParamName(name) {
    return name.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function renderParams(containerId, params, prefix) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    params.forEach(p => {
        const row = document.createElement('div');
        row.className = 'param-row';
        let input;
        if (p.choices) {
            input = `<select id="${prefix}${p.name}">` +
                p.choices.map(c => `<option value="${c}" ${c===p.default?'selected':''}>${c}</option>`).join('') +
                '</select>';
        } else if (p.type === 'bool') {
            input = `<select id="${prefix}${p.name}"><option value="true" ${p.default?'selected':''}>true</option><option value="false" ${!p.default?'selected':''}>false</option></select>`;
        } else {
            const attrs = [];
            if (p.min !== undefined) attrs.push(`min="${p.min}"`);
            if (p.max !== undefined) attrs.push(`max="${p.max}"`);
            if (p.step !== undefined) attrs.push(`step="${p.step}"`);
            input = `<input type="${p.type==='int'||p.type==='float'?'number':'text'}" id="${prefix}${p.name}" value="${p.default}" ${attrs.join(' ')}>`;
        }
        row.innerHTML = `<label>${formatParamName(p.name)}</label>${input}`;
        container.appendChild(row);
    });
}

function collectParams(params, prefix) {
    const result = {};
    params.forEach(p => {
        const el = document.getElementById(prefix + p.name);
        let val = el.value;
        if (p.type === 'int') val = parseInt(val);
        else if (p.type === 'float') val = parseFloat(val);
        else if (p.type === 'bool') val = val === 'true';
        result[p.name] = val;
    });
    return result;
}

async function runBacktest() {
    const btn = document.getElementById('run-btn');
    const status = document.getElementById('status');
    if (selectedSymbols.length === 0) {
        alert('Please select at least one symbol');
        return;
    }
    btn.disabled = true;
    status.style.display = 'block';
    status.className = 'status-running';
    status.textContent = 'Starting backtest...';

    const params = collectParams(strategyParams, 'sp_');
    params.bar_period = currentBarPeriod;
    const payload = {
        strategy: document.getElementById('strategy').value,
        strategy_params: params,
        symbols: selectedSymbols,
        start_date: document.getElementById('start-date').value || null,
        end_date: document.getElementById('end-date').value || null
    };

    const res = await fetch('/api/backtest/run', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    const data = await res.json();
    const runId = data.run_id;
    status.textContent = `Backtest ${runId} running...`;

    const poll = setInterval(async () => {
        const r = await fetch(`/api/backtest/status/${runId}`);
        const d = await r.json();
        if (d.status === 'completed') {
            clearInterval(poll);
            status.className = 'status-completed';
            status.textContent = `Backtest ${runId} completed!`;
            btn.disabled = false;
        } else if (d.status.startsWith('error')) {
            clearInterval(poll);
            status.className = 'status-error';
            status.textContent = `Backtest ${runId}: ${d.status}`;
            btn.disabled = false;
        }
    }, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
    loadStrategies();
    loadBarPeriods();
    loadPresets();
});
"""


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_form():
    sidebar = SIDEBAR_HTML.format(
        runs_active="", backtest_active="active", secmaster_active=""
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Backtest - OneSecondTrader</title>
        <style>{BASE_STYLE}{BACKTEST_FORM_STYLE}</style>
    </head>
    <body>
        {sidebar}
        <main class="main-content">
            <div class="container">
                <div class="card">
                    <h2>Run Backtest</h2>
                    <div class="form-group">
                        <label>Strategy</label>
                        <select id="strategy" onchange="loadStrategyParams()"></select>
                        <div class="section-header">Parameters</div>
                        <div id="strategy-params" class="params-container"></div>
                    </div>
                    <div class="form-group">
                        <label>Bar Period</label>
                        <select id="bar-period" onchange="onBarPeriodChange()"></select>
                    </div>
                    <div class="form-group">
                        <label>Symbols</label>
                        <div class="symbol-section">
                            <div class="preset-row">
                                <select id="preset-select" onchange="loadPreset()"></select>
                                <input type="text" id="preset-name" placeholder="New preset name...">
                                <button class="btn btn-sm btn-secondary" onclick="savePreset()">Save</button>
                                <button class="btn btn-sm btn-danger" onclick="deletePreset()">Delete</button>
                            </div>
                            <div class="search-row">
                                <input type="text" id="symbol-search" placeholder="Search symbols..." oninput="searchSymbols()">
                            </div>
                            <div id="search-results" class="search-results"></div>
                            <div id="selected-label" class="selected-label">Selected (0):</div>
                            <div id="selected-symbols" class="selected-symbols"></div>
                        </div>
                    </div>
                    <div class="date-row">
                        <div class="form-group">
                            <label>Start Date</label>
                            <input type="date" id="start-date" onchange="clampDate('start-date')">
                        </div>
                        <div class="form-group">
                            <label>End Date</label>
                            <input type="date" id="end-date" onchange="clampDate('end-date')">
                        </div>
                    </div>
                    <div class="form-group" style="margin-top: 16px;">
                        <button id="run-btn" class="btn" onclick="runBacktest()">Run Backtest</button>
                    </div>
                    <div id="status"></div>
                </div>
            </div>
        </main>
        <script>{BACKTEST_FORM_SCRIPT}</script>
    </body>
    </html>
    """


def _get_secmaster_summary() -> dict:
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return {"exists": False}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT key, value FROM meta")
    meta = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    if not meta:
        return {"exists": True, "db_path": db_path, "needs_reindex": True}

    rtypes_str = meta.get("ohlcv_schemas", "")
    rtypes = [RTYPE_TO_BAR_PERIOD.get(int(r), r) for r in rtypes_str.split(",") if r]

    db_size_bytes = os.path.getsize(db_path)

    return {
        "exists": True,
        "db_path": db_path,
        "db_size_mb": round(db_size_bytes / (1024 * 1024), 1),
        "symbol_count": int(meta.get("symbol_count", 0)),
        "ohlcv_record_count": int(meta.get("ohlcv_record_count", 0)),
        "min_ts": int(meta.get("ohlcv_min_ts", 0)),
        "max_ts": int(meta.get("ohlcv_max_ts", 0)),
        "schemas": rtypes,
    }


def _search_symbol(query: str) -> list[dict]:
    db_path = _get_secmaster_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT symbol, rtype, min_ts, max_ts, record_count
        FROM symbol_coverage
        WHERE symbol LIKE ?
        ORDER BY symbol
        LIMIT 100
    """,
        (f"%{query}%",),
    )

    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "symbol": row[0],
                "min_ts": row[2],
                "max_ts": row[3],
                "record_count": row[4],
                "schema": (
                    RTYPE_TO_BAR_PERIOD.get(row[1], str(row[1])) if row[1] else None
                ),
            }
        )

    conn.close()
    return results


@app.get("/api/secmaster/summary")
async def get_secmaster_summary():
    return _get_secmaster_summary()


@app.get("/api/secmaster/search")
async def search_secmaster(q: str = ""):
    if len(q) < 1:
        return {"results": []}
    return {"results": _search_symbol(q)}


SECMASTER_STYLE = """
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #0d1117; border-radius: 8px; padding: 20px; }
.stat-card .label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-card .value { font-size: 28px; font-weight: 600; margin-top: 4px; }
.stat-card .sub { font-size: 12px; color: #8b949e; margin-top: 4px; }
.asset-table { width: 100%; border-collapse: collapse; }
.asset-table th, .asset-table td { padding: 12px; text-align: left; border-bottom: 1px solid #30363d; }
.asset-table th { font-size: 12px; color: #8b949e; text-transform: uppercase; font-weight: 500; }
.asset-table tr:hover { background: #21262d; }
.search-box { width: 100%; padding: 12px 16px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; font-size: 14px; margin-bottom: 16px; }
.search-box:focus { outline: none; border-color: #58a6ff; }
.search-results { max-height: 400px; overflow-y: auto; }
.no-db { text-align: center; padding: 48px; color: #8b949e; }
.no-db code { background: #21262d; padding: 2px 6px; border-radius: 4px; }
.loading { display: flex; align-items: center; gap: 12px; color: #8b949e; padding: 24px; }
.spinner { width: 20px; height: 20px; border: 2px solid #30363d; border-top-color: #58a6ff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
"""

SECMASTER_SCRIPT = """
function showLoading(elementId, message) {
    document.getElementById(elementId).innerHTML = `<div class="loading"><div class="spinner"></div><span>${message}</span></div>`;
}

async function loadSummary() {
    showLoading('content', 'Loading database summary...');
    const res = await fetch('/api/secmaster/summary');
    const data = await res.json();

    if (!data.exists) {
        document.getElementById('content').innerHTML = `
            <div class="no-db">
                <p>No securities master database found.</p>
                <p style="margin-top: 8px;">Set <code>SECMASTER_DB_PATH</code> environment variable or place <code>secmaster.db</code> in the working directory.</p>
            </div>
        `;
        return;
    }

    if (data.needs_reindex) {
        document.getElementById('content').innerHTML = `
            <div class="no-db">
                <p>Database metadata not found.</p>
                <p style="margin-top: 8px;">Run <code>from onesecondtrader.secmaster.utils import update_meta; update_meta(path)</code> to rebuild stats.</p>
            </div>
        `;
        return;
    }

    const minDate = new Date(data.min_ts / 1000000).toISOString().split('T')[0];
    const maxDate = new Date(data.max_ts / 1000000).toISOString().split('T')[0];

    document.getElementById('content').innerHTML = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Symbols</div>
                <div class="value">${data.symbol_count.toLocaleString()}</div>
            </div>
            <div class="stat-card">
                <div class="label">OHLCV Records</div>
                <div class="value">${data.ohlcv_record_count.toLocaleString()}</div>
            </div>
            <div class="stat-card">
                <div class="label">Date Range</div>
                <div class="value" style="font-size: 18px;">${minDate}</div>
                <div class="sub">to ${maxDate}</div>
            </div>
            <div class="stat-card">
                <div class="label">Schemas</div>
                <div class="value" style="font-size: 18px;">${data.schemas.join(', ')}</div>
            </div>
            <div class="stat-card">
                <div class="label">Database Size</div>
                <div class="value">${data.db_size_mb} MB</div>
                <div class="sub">${data.db_path}</div>
            </div>
        </div>
        <div class="card">
            <h2>Symbol Search</h2>
            <input type="text" class="search-box" id="search-input" placeholder="Search symbols..." oninput="searchSymbols()">
            <div id="search-results" class="search-results"></div>
        </div>
    `;
}

let searchTimeout;
async function searchSymbols() {
    const q = document.getElementById('search-input').value;
    clearTimeout(searchTimeout);
    if (q.length < 1) {
        document.getElementById('search-results').innerHTML = '';
        return;
    }
    showLoading('search-results', 'Searching...');
    searchTimeout = setTimeout(async () => {
        const res = await fetch('/api/secmaster/search?q=' + encodeURIComponent(q));
        const data = await res.json();
        if (data.results.length === 0) {
            document.getElementById('search-results').innerHTML = '<p style="color: #8b949e;">No results found.</p>';
            return;
        }
        let rows = data.results.map(r => {
            const minDate = r.min_ts ? new Date(r.min_ts / 1000000).toISOString().split('T')[0] : '-';
            const maxDate = r.max_ts ? new Date(r.max_ts / 1000000).toISOString().split('T')[0] : '-';
            return `<tr>
                <td>${r.symbol}</td>
                <td>${r.schema || '-'}</td>
                <td>${minDate} → ${maxDate}</td>
                <td>${r.record_count ? r.record_count.toLocaleString() : '-'}</td>
            </tr>`;
        }).join('');
        document.getElementById('search-results').innerHTML = `
            <table class="asset-table">
                <thead><tr><th>Symbol</th><th>Schema</th><th>Date Range</th><th>Records</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }, 300);
}

document.addEventListener('DOMContentLoaded', loadSummary);
"""


@app.get("/secmaster", response_class=HTMLResponse)
async def secmaster_page():
    sidebar = SIDEBAR_HTML.format(
        runs_active="", backtest_active="", secmaster_active="active"
    )
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Securities Master - OneSecondTrader</title>
        <style>{BASE_STYLE}{SECMASTER_STYLE}</style>
    </head>
    <body>
        {sidebar}
        <main class="main-content">
            <div class="container" id="content">
                <p style="color: #8b949e;">Loading...</p>
            </div>
        </main>
        <script>{SECMASTER_SCRIPT}</script>
    </body>
    </html>
    """
