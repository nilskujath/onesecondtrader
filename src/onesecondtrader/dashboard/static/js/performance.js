let runs = [];
let selectedRunId = null;
let selectedSymbol = null;
let symbols = [];
let suggestionIndex = -1;

function getUrlRunId() {
    const params = new URLSearchParams(window.location.search);
    return params.get('run_id');
}

async function loadRuns() {
    const res = await fetch('/api/runs');
    const data = await res.json();
    runs = (data.runs || []).filter(r => r.status === 'completed');
    renderSettings();
    renderCharts();
    const urlRunId = getUrlRunId();
    if (urlRunId && runs.some(r => r.run_id === urlRunId)) {
        selectRun(urlRunId);
    }
}

function onRunChange() {
    const select = document.getElementById('run-select');
    const runId = select.value;
    if (runId) {
        selectRun(runId);
    }
}

function selectRun(runId) {
    selectedRunId = runId;
    selectedSymbol = null;
    const url = new URL(window.location);
    url.searchParams.set('run_id', runId);
    window.history.replaceState({}, '', url);
    const select = document.getElementById('run-select');
    if (select && select.value !== runId) {
        select.value = runId;
    }
    loadSymbols(runId);
}

async function loadSymbols(runId) {
    renderCharts();
    const res = await fetch(`/api/runs/${runId}/roundtrips`);
    const data = await res.json();
    const roundtrips = data.roundtrips || [];
    symbols = [...new Set(roundtrips.map(rt => rt.symbol))].sort();
    renderSettings();
    renderCharts();
}

function onSymbolInput() {
    const input = document.getElementById('symbol-input');
    const query = input.value.trim().toUpperCase();
    const suggestions = document.getElementById('symbol-suggestions');
    suggestionIndex = -1;
    if (!query) {
        suggestions.classList.remove('show');
        selectedSymbol = null;
        renderCharts();
        return;
    }
    const matches = symbols.filter(s => s.toUpperCase().includes(query));
    if (matches.length === 0) {
        suggestions.classList.remove('show');
        return;
    }
    suggestions.innerHTML = matches.map((s, i) => `<div class="symbol-suggestion" data-symbol="${s}" onclick="selectSymbol('${s}')">${s}</div>`).join('');
    suggestions.classList.add('show');
}

function onSymbolKeydown(e) {
    const suggestions = document.getElementById('symbol-suggestions');
    const items = suggestions.querySelectorAll('.symbol-suggestion');
    if (!suggestions.classList.contains('show') || items.length === 0) return;
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        suggestionIndex = Math.min(suggestionIndex + 1, items.length - 1);
        updateSuggestionHighlight(items);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        suggestionIndex = Math.max(suggestionIndex - 1, 0);
        updateSuggestionHighlight(items);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (suggestionIndex >= 0 && suggestionIndex < items.length) {
            selectSymbol(items[suggestionIndex].dataset.symbol);
        }
    } else if (e.key === 'Escape') {
        suggestions.classList.remove('show');
    }
}

function updateSuggestionHighlight(items) {
    items.forEach((item, i) => {
        item.classList.toggle('selected', i === suggestionIndex);
    });
}

function selectSymbol(symbol) {
    selectedSymbol = symbol;
    const input = document.getElementById('symbol-input');
    if (input) input.value = symbol;
    const suggestions = document.getElementById('symbol-suggestions');
    if (suggestions) suggestions.classList.remove('show');
    renderCharts();
}

function renderSettings() {
    const container = document.getElementById('settings-panel');
    if (!container) return;
    const runOptions = runs.length === 0
        ? '<option value="">No completed runs</option>'
        : '<option value="">Select a run...</option>' + runs.map(r => {
            const config = r.config || {};
            const strategies = config.strategies ? config.strategies.join(', ') : r.name;
            const timePart = r.run_id.slice(11, 19).replace(/-/g, ':');
            const selected = r.run_id === selectedRunId ? 'selected' : '';
            return `<option value="${r.run_id}" ${selected}>${strategies} (${timePart})</option>`;
        }).join('');
    const symbolValue = selectedSymbol || '';
    const symbolDisabled = symbols.length === 0 ? 'disabled' : '';
    const symbolPlaceholder = symbols.length === 0 ? 'Select a run first...' : 'Search symbol...';
    container.innerHTML = `
        <div class="settings-row">
            <div class="settings-group">
                <label>Run:</label>
                <select id="run-select" onchange="onRunChange()">${runOptions}</select>
            </div>
            <div class="settings-group">
                <label>Symbol:</label>
                <div class="symbol-input-wrapper">
                    <input type="text" id="symbol-input" value="${symbolValue}" placeholder="${symbolPlaceholder}" ${symbolDisabled} oninput="onSymbolInput()" onkeydown="onSymbolKeydown(event)" onfocus="onSymbolInput()" autocomplete="off">
                    <div id="symbol-suggestions" class="symbol-suggestions"></div>
                </div>
            </div>
        </div>
    `;
}

function renderCharts() {
    const container = document.getElementById('charts-row');
    if (!container) return;
    const emptyPnl = !selectedRunId || !selectedSymbol ? '<div class="empty-message">Select a run and symbol</div>' : '<div class="chart-loading">Loading...</div>';
    const emptyJourney = !selectedRunId || !selectedSymbol ? '<div class="empty-message">Select a run and symbol</div>' : '<div class="chart-loading">Loading...</div>';
    container.innerHTML = `
        <div class="chart-card"><h3>PnL Summary</h3><div class="chart-content" id="pnl-container">${emptyPnl}</div></div>
        <div class="chart-card"><h3>Trade Journey</h3><div class="chart-content" id="journey-container">${emptyJourney}</div></div>
    `;
    if (selectedRunId && selectedSymbol) {
        loadChartImage('pnl-container', `/api/runs/${selectedRunId}/pnl-summary.png?symbol=${encodeURIComponent(selectedSymbol)}`);
        loadChartImage('journey-container', `/api/runs/${selectedRunId}/trade-journey.png?symbol=${encodeURIComponent(selectedSymbol)}`);
    }
}

function loadChartImage(containerId, url) {
    const container = document.getElementById(containerId);
    const img = new Image();
    img.onload = () => { container.innerHTML = ''; container.appendChild(img); };
    img.onerror = () => { container.innerHTML = '<div class="chart-loading">Failed to load chart</div>'; };
    img.src = url;
    img.alt = 'Chart';
}

document.addEventListener('click', (e) => {
    const suggestions = document.getElementById('symbol-suggestions');
    const input = document.getElementById('symbol-input');
    if (suggestions && input && !input.contains(e.target) && !suggestions.contains(e.target)) {
        suggestions.classList.remove('show');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    loadRuns();
});
