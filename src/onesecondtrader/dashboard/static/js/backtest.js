/* ════════════════════════════════════════════════════════════════════
   Box 1 — Backtest Config  (original backtest.js, unchanged except
           goToPerformance → selectAnalysisRun)
   ════════════════════════════════════════════════════════════════════ */

let strategyParams = [];
let coverageData = [];
let availableRtypes = [];
let symbolsForRtype = {};
let symbolCoverageForRtype = {};
let selectedSymbols = [];
let presets = [];
let globalMinDate = null;
let globalMaxDate = null;
let dbRuns = [];
let activeRuns = {};
let selectedRunIds = new Set();
let publishers = [];
let datasets = [];
let selectedPublisherId = null;
let isLoadingPreset = false;

const RTYPE_LABELS = {32: 'Second', 33: 'Minute', 34: 'Hour', 35: 'Day'};

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

async function loadPublishers() {
    const rtype = getSelectedRtype();
    const url = rtype ? `/api/secmaster/publishers?rtype=${rtype}` : '/api/secmaster/publishers';
    const res = await fetch(url);
    const data = await res.json();
    publishers = data.publishers || [];
    const sel = document.getElementById('publisher-name');
    sel.innerHTML = '<option value="">-- Select Publisher --</option>';
    publishers.forEach(p => sel.innerHTML += `<option value="${p}">${capitalize(p)}</option>`);
}

async function onPublisherChange() {
    if (isLoadingPreset) return;
    document.getElementById('preset-select').value = '';
    const name = document.getElementById('publisher-name').value;
    const rtype = getSelectedRtype();
    const datasetSel = document.getElementById('publisher-dataset');
    datasetSel.innerHTML = '<option value="">-- Select Dataset --</option>';
    datasets = [];
    selectedPublisherId = null;
    document.getElementById('symbol-selection').style.display = 'none';
    selectedSymbols = [];
    renderSelectedSymbols();
    updateDateRange();
    if (!name) return;
    const url = rtype
        ? `/api/secmaster/publishers/${encodeURIComponent(name)}/datasets?rtype=${rtype}`
        : `/api/secmaster/publishers/${encodeURIComponent(name)}/datasets`;
    const res = await fetch(url);
    const data = await res.json();
    datasets = data.datasets || [];
    datasets.forEach(d => datasetSel.innerHTML += `<option value="${d.publisher_id}">${d.dataset}</option>`);
}

async function onDatasetChange() {
    if (isLoadingPreset) return;
    document.getElementById('preset-select').value = '';
    const pubId = document.getElementById('publisher-dataset').value;
    selectedPublisherId = pubId ? parseInt(pubId) : null;
    selectedSymbols = [];
    renderSelectedSymbols();
    updateDateRange();
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
    if (selectedPublisherId) {
        await loadCoverageForPublisher(selectedPublisherId);
        document.getElementById('symbol-selection').style.display = 'block';
    } else {
        document.getElementById('symbol-selection').style.display = 'none';
    }
}

async function loadCoverageForPublisher(publisherId) {
    const rtype = getSelectedRtype();
    const url = `/api/secmaster/symbols_coverage?publisher_id=${publisherId}&rtype=${rtype}`;
    const res = await fetch(url);
    const data = await res.json();
    coverageData = data.symbols || [];
    symbolsForRtype = {};
    symbolCoverageForRtype = {};
    coverageData.forEach(row => {
        if (!symbolsForRtype[row.rtype]) {
            symbolsForRtype[row.rtype] = [];
            symbolCoverageForRtype[row.rtype] = {};
        }
        symbolsForRtype[row.rtype].push(row.symbol);
        symbolCoverageForRtype[row.rtype][row.symbol] = {min_ts: row.min_ts, max_ts: row.max_ts};
    });
}

async function loadPresets() {
    const res = await fetch('/api/presets');
    const data = await res.json();
    presets = data.presets || [];
    renderPresetDropdown();
}

function renderPresetDropdown() {
    const sel = document.getElementById('preset-select');
    sel.innerHTML = '<option value="">-- Select Preset --</option>';
    presets.forEach(p => {
        sel.innerHTML += `<option value="${p.name}">${p.name}</option>`;
    });
    updateButtonStates();
}

async function loadPreset() {
    const name = document.getElementById('preset-select').value;
    updateButtonStates();
    if (!name) return;
    const preset = presets.find(p => p.name === name);
    if (!preset) return;
    await applyPreset(preset);
}

async function applyPreset(preset) {
    isLoadingPreset = true;
    try {
        const barPeriodEl = document.getElementById('bar-period');
        barPeriodEl.value = String(preset.rtype);
        const section = document.getElementById('symbols-section');
        section.style.display = 'block';
        await loadPublishers();
        const pubNameEl = document.getElementById('publisher-name');
        pubNameEl.value = preset.publisher_name;
        const rtype = preset.rtype;
        const url = `/api/secmaster/publishers/${encodeURIComponent(preset.publisher_name)}/datasets?rtype=${rtype}`;
        const res = await fetch(url);
        const data = await res.json();
        datasets = data.datasets || [];
        const datasetSel = document.getElementById('publisher-dataset');
        datasetSel.innerHTML = '<option value="">-- Select Dataset --</option>';
        datasets.forEach(d => datasetSel.innerHTML += `<option value="${d.publisher_id}">${d.dataset}</option>`);
        datasetSel.value = String(preset.publisher_id);
        selectedPublisherId = preset.publisher_id;
        await loadCoverageForPublisher(selectedPublisherId);
        document.getElementById('symbol-selection').style.display = 'block';
        document.getElementById('symbol-search').value = '';
        document.getElementById('search-results').innerHTML = '';
        const availableSymbols = symbolsForRtype[rtype] || [];
        selectedSymbols = preset.symbols.filter(s => availableSymbols.includes(s));
        renderSelectedSymbolsKeepPreset();
        updateDateRange();
    } finally {
        isLoadingPreset = false;
    }
}

async function savePreset() {
    const nameInput = document.getElementById('preset-name');
    const name = nameInput.value.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const rtype = getSelectedRtype();
    if (!rtype) { alert('Select a bar period first'); return; }
    if (!selectedPublisherId) { alert('Select a publisher and dataset first'); return; }
    if (selectedSymbols.length === 0) { alert('Select at least one symbol'); return; }
    const publisherName = document.getElementById('publisher-name').value;
    const exists = presets.some(p => p.name === name);
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? `/api/presets/${encodeURIComponent(name)}` : '/api/presets';
    await fetch(apiUrl, {
        method, headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name,
            rtype,
            publisher_name: publisherName,
            publisher_id: selectedPublisherId,
            symbols: selectedSymbols
        })
    });
    nameInput.value = '';
    await loadPresets();
    document.getElementById('preset-select').value = name;
    updateButtonStates();
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

function updateButtonStates() {
    const runBtn = document.getElementById('run-btn');
    const saveBtn = document.getElementById('preset-save-btn');
    const deleteBtn = document.getElementById('preset-delete-btn');
    const presetSelect = document.getElementById('preset-select');
    const presetNameInput = document.getElementById('preset-name');
    const strategyEl = document.getElementById('strategy');
    const barPeriodEl = document.getElementById('bar-period');
    if (!runBtn) return;
    const rtype = barPeriodEl ? parseInt(barPeriodEl.value) || null : null;
    const strategy = strategyEl ? strategyEl.value : '';
    const canRun = strategy && rtype && selectedPublisherId && selectedSymbols.length > 0;
    runBtn.disabled = !canRun;
    const hasPresetSelected = !!(presetSelect && presetSelect.value);
    const hasPresetName = !!(presetNameInput && presetNameInput.value.trim().length > 0);
    const canSave = hasPresetName && rtype && selectedPublisherId && selectedSymbols.length > 0;
    if (saveBtn) {
        saveBtn.classList.toggle('active', canSave);
    }
    if (deleteBtn) {
        deleteBtn.classList.toggle('active', hasPresetSelected);
    }
}

async function loadStrategies() {
    const res = await fetch('/api/strategies');
    const data = await res.json();
    const sel = document.getElementById('strategy');
    sel.innerHTML = '';
    data.strategies.forEach(s => sel.innerHTML += `<option value="${s.id}">${s.name}</option>`);
    if (data.strategies.length > 0) {
        sel.value = data.strategies[0].id;
        loadStrategyParams();
    }
}

async function loadStrategyParams() {
    const name = document.getElementById('strategy').value;
    if (!name) return;
    const res = await fetch(`/api/strategies/${name}`);
    const data = await res.json();
    strategyParams = data.parameters || [];
    renderParams();
}

function formatParamName(name) {
    let result = name.replace(/_/g, ' ');
    result = result.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
    result = result.replace(/([a-z])([A-Z])/g, '$1 $2');
    return result.split(' ').map(word => {
        if (word === word.toUpperCase() && word.length > 1) return word;
        return word.charAt(0).toUpperCase() + word.slice(1);
    }).join(' ');
}

function renderParams() {
    const container = document.getElementById('strategy-params');
    const filtered = strategyParams.filter(p => p.name !== 'bar_period');
    if (filtered.length === 0) {
        container.innerHTML = '<div style="color: #8b949e; font-size: 13px;">No parameters</div>';
        return;
    }
    container.innerHTML = filtered.map(p => {
        const label = formatParamName(p.name);
        if (p.choices && p.choices.length > 0) {
            const opts = p.choices.map(c => `<option value="${c}" ${c === p.default ? 'selected' : ''}>${c}</option>`).join('');
            return `<div class="param-row"><label>${label}</label><select id="sp_${p.name}">${opts}</select></div>`;
        }
        const inputType = p.type === 'bool' ? 'checkbox' : (p.type === 'float' || p.type === 'int' ? 'number' : 'text');
        const step = p.step || (p.type === 'float' ? '0.01' : '1');
        const checked = p.type === 'bool' && p.default ? 'checked' : '';
        return `<div class="param-row"><label>${label}</label><input type="${inputType}" id="sp_${p.name}" value="${p.default}" step="${step}" ${p.min !== undefined ? `min="${p.min}"` : ''} ${p.max !== undefined ? `max="${p.max}"` : ''} ${checked}></div>`;
    }).join('');
}

function tsToDate(ts) {
    const ms = Math.floor(ts / 1000000);
    const d = new Date(ms);
    return d.toISOString().split('T')[0];
}

async function loadCoverage() {
    const res = await fetch('/api/secmaster/symbols_coverage');
    const data = await res.json();
    coverageData = data.symbols || [];
    const rtypeSet = new Set();
    coverageData.forEach(row => rtypeSet.add(row.rtype));
    availableRtypes = Array.from(rtypeSet).sort((a, b) => a - b);
    populateBarPeriodDropdown();
}

function populateBarPeriodDropdown() {
    const sel = document.getElementById('bar-period');
    sel.innerHTML = '<option value="">-- Select bar period --</option>';
    availableRtypes.forEach(rt => {
        const label = RTYPE_LABELS[rt] || `rtype ${rt}`;
        sel.innerHTML += `<option value="${rt}">${label}</option>`;
    });
}

function onBarPeriodChange() {
    if (isLoadingPreset) return;
    document.getElementById('preset-select').value = '';
    selectedSymbols = [];
    selectedPublisherId = null;
    symbolsForRtype = {};
    symbolCoverageForRtype = {};
    renderSelectedSymbols();
    updateDateRange();
    const rtype = document.getElementById('bar-period').value;
    const section = document.getElementById('symbols-section');
    const symbolSelection = document.getElementById('symbol-selection');
    document.getElementById('publisher-name').value = '';
    document.getElementById('publisher-dataset').innerHTML = '<option value="">-- Select Dataset --</option>';
    if (rtype) {
        section.style.display = 'block';
        loadPublishers();
    } else {
        section.style.display = 'none';
    }
    symbolSelection.style.display = 'none';
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
}

function getSelectedRtype() {
    return parseInt(document.getElementById('bar-period').value) || null;
}

function searchSymbols() {
    const query = document.getElementById('symbol-search').value.toLowerCase();
    const container = document.getElementById('search-results');
    const rtype = getSelectedRtype();
    if (!query || !rtype) {
        container.innerHTML = '';
        return;
    }
    const symbols = symbolsForRtype[rtype] || [];
    const matches = symbols.filter(s => s.toLowerCase().includes(query) && !selectedSymbols.includes(s)).slice(0, 20);
    container.innerHTML = matches.map(s =>
        `<div class="search-result" onclick="addSymbol('${s}')"><span class="symbol">${s}</span></div>`
    ).join('');
}

function addSymbol(symbol) {
    if (!selectedSymbols.includes(symbol)) {
        selectedSymbols.push(symbol);
        document.getElementById('preset-select').value = '';
        renderSelectedSymbols();
        updateDateRange();
    }
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
}

function removeSymbol(symbol) {
    selectedSymbols = selectedSymbols.filter(s => s !== symbol);
    document.getElementById('preset-select').value = '';
    renderSelectedSymbols();
    updateDateRange();
}

function renderSelectedSymbols() {
    const container = document.getElementById('selected-symbols');
    document.getElementById('selected-label').textContent = `Selected (${selectedSymbols.length}):`;
    container.innerHTML = selectedSymbols.map(s =>
        `<span class="selected-tag">${s}<span class="remove" onclick="removeSymbol('${s}')">&times;</span></span>`
    ).join('');
    updateButtonStates();
}

function renderSelectedSymbolsKeepPreset() {
    const container = document.getElementById('selected-symbols');
    document.getElementById('selected-label').textContent = `Selected (${selectedSymbols.length}):`;
    container.innerHTML = selectedSymbols.map(s =>
        `<span class="selected-tag">${s}<span class="remove" onclick="removeSymbol('${s}')">&times;</span></span>`
    ).join('');
    updateButtonStates();
}

function updateDateRange() {
    const startInput = document.getElementById('start-date');
    const endInput = document.getElementById('end-date');
    const rtype = getSelectedRtype();
    if (selectedSymbols.length === 0 || !rtype) {
        globalMinDate = null;
        globalMaxDate = null;
        startInput.value = '';
        endInput.value = '';
        startInput.removeAttribute('min');
        startInput.removeAttribute('max');
        endInput.removeAttribute('min');
        endInput.removeAttribute('max');
        return;
    }
    const coverage = symbolCoverageForRtype[rtype] || {};
    let minTs = null, maxTs = null;
    selectedSymbols.forEach(s => {
        const cov = coverage[s];
        if (cov) {
            if (minTs === null || cov.min_ts < minTs) minTs = cov.min_ts;
            if (maxTs === null || cov.max_ts > maxTs) maxTs = cov.max_ts;
        }
    });
    if (minTs === null) return;
    globalMinDate = tsToDate(minTs);
    globalMaxDate = tsToDate(maxTs);
    startInput.min = globalMinDate;
    startInput.max = globalMaxDate;
    startInput.value = globalMinDate;
    endInput.min = globalMinDate;
    endInput.max = globalMaxDate;
    endInput.value = globalMaxDate;
}

function clampDate(inputId) {
    if (!globalMinDate || !globalMaxDate) return;
    const input = document.getElementById(inputId);
    if (input.value < globalMinDate) input.value = globalMinDate;
    if (input.value > globalMaxDate) input.value = globalMaxDate;
}

function collectParams() {
    const result = {};
    strategyParams.forEach(p => {
        const el = document.getElementById(`sp_${p.name}`);
        if (!el) return;
        if (p.type === 'bool') result[p.name] = el.checked;
        else if (p.type === 'int') result[p.name] = parseInt(el.value);
        else if (p.type === 'float') result[p.name] = parseFloat(el.value);
        else result[p.name] = el.value;
    });
    return result;
}

async function loadDbRuns() {
    const res = await fetch('/api/runs');
    const data = await res.json();
    dbRuns = data.runs || [];
    renderRuns();
    // Also refresh the Box 2 completed-runs dropdown
    loadCompletedRuns();
}

function toggleRunSelection(runId) {
    if (selectedRunIds.has(runId)) {
        selectedRunIds.delete(runId);
    } else {
        selectedRunIds.add(runId);
    }
    renderRuns();
}

function toggleSelectAll() {
    const allDbRunIds = dbRuns.map(r => r.run_id);
    if (selectedRunIds.size === allDbRunIds.length && allDbRunIds.length > 0) {
        selectedRunIds.clear();
    } else {
        allDbRunIds.forEach(id => selectedRunIds.add(id));
    }
    renderRuns();
}

async function deleteSelectedRuns() {
    if (selectedRunIds.size === 0) return;
    if (!confirm(`Delete ${selectedRunIds.size} run(s)? This cannot be undone.`)) return;
    const res = await fetch('/api/runs', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({run_ids: Array.from(selectedRunIds)})
    });
    if (res.ok) {
        selectedRunIds.clear();
        await loadDbRuns();
    } else {
        try {
            const data = await res.json();
            alert(data.detail || 'Failed to delete runs');
        } catch {
            alert('Failed to delete runs');
        }
    }
}

function renderRuns() {
    const container = document.getElementById('runs-list');
    const activeRunIds = Object.keys(activeRuns).filter(id => activeRuns[id].status === 'running' || activeRuns[id].status === 'queued').reverse();
    const allDbRunIds = dbRuns.map(r => r.run_id);
    const allSelected = allDbRunIds.length > 0 && selectedRunIds.size === allDbRunIds.length;

    let html = '';
    if (dbRuns.length > 0 || activeRunIds.length > 0) {
        html += `<div class="runs-toolbar">
            <label class="select-all-label">
                <input type="checkbox" ${allSelected ? 'checked' : ''} onchange="toggleSelectAll()">
                Select all
            </label>
            <button class="btn-delete" ${selectedRunIds.size === 0 ? 'disabled' : ''} onclick="deleteSelectedRuns()">
                Delete (${selectedRunIds.size})
            </button>
        </div>`;
    }

    activeRunIds.forEach(id => {
        const run = activeRuns[id];
        const progress = run.progress;
        const isQueued = run.status === 'queued';
        html += `<div class="run-item">
            <div class="run-content">
                <div class="run-header">
                    <span class="run-name">${run.strategy}</span>
                    <span class="run-status ${isQueued ? 'queued' : 'running'}">${isQueued ? 'queued' : 'running'}</span>
                </div>
                <div class="run-meta ${isQueued ? '' : 'with-progress'}">${run.symbols.length} symbol${run.symbols.length !== 1 ? 's' : ''} · ${run.startDate || 'all'} to ${run.endDate || 'all'}</div>
                ${isQueued ? '' : `<div class="progress-bar"><div class="progress-fill" style="width: ${progress}%"></div></div>`}
            </div>
        </div>`;
    });

    dbRuns.filter(r => r.status !== 'running').forEach(r => {
        const config = r.config || {};
        const strategies = config.strategies ? config.strategies.join(', ') : r.name;
        const symbols = config.symbols || [];
        const symbolCount = symbols.length;
        const startDate = config.start_date || '-';
        const endDate = config.end_date || '-';
        const timePart = r.run_id.slice(11, 19).replace(/-/g, ':');
        const isSelected = selectedRunIds.has(r.run_id);
        const statusClass = r.status;
        const clickable = r.status === 'completed' ? `onclick="selectAnalysisRun('${r.run_id}')"` : '';
        const clickableClass = r.status === 'completed' ? 'clickable' : '';
        html += `<div class="run-item ${isSelected ? 'selected' : ''}">
            <input type="checkbox" class="run-checkbox" ${isSelected ? 'checked' : ''} onchange="toggleRunSelection('${r.run_id}')">
            <div class="run-content ${clickableClass}" ${clickable}>
                <div class="run-header">
                    <span class="run-name">${strategies} <span class="run-id">${timePart}</span></span>
                    <span class="run-status ${statusClass}">${r.status}</span>
                </div>
                <div class="run-meta">${symbolCount} symbol${symbolCount !== 1 ? 's' : ''} · ${startDate} to ${endDate}</div>
            </div>
        </div>`;
    });

    if (html === '') {
        html = '<div class="empty-runs"><p>No runs yet</p><p>Configure settings and click Run Backtest</p></div>';
    }
    container.innerHTML = html;
}

async function pollBacktestStatus(runId, refreshCount) {
    if (refreshCount === undefined) refreshCount = 0;
    try {
        const r = await fetch(`/api/backtest/status/${runId}`);
        const d = await r.json();
        if (d.status === 'completed' || d.status.startsWith('error')) {
            delete activeRuns[runId];
            renderRuns();
            await loadDbRuns();
            if (refreshCount < 5) {
                setTimeout(() => pollBacktestStatus(runId, refreshCount + 1), 500);
            }
            return;
        }
        if (activeRuns[runId]) {
            activeRuns[runId].status = d.status === 'queued' ? 'queued' : 'running';
            activeRuns[runId].progress = d.progress || 0;
            renderRuns();
        }
    } catch (e) {
        // fetch failed, will retry on next poll
    }
    setTimeout(() => pollBacktestStatus(runId), 1000);
}

async function runBacktest() {
    const btn = document.getElementById('run-btn');
    const rtype = getSelectedRtype();
    if (!rtype) {
        alert('Please select a bar period');
        return;
    }
    if (!selectedPublisherId) {
        alert('Please select a publisher and dataset');
        return;
    }
    if (selectedSymbols.length === 0) {
        alert('Please select at least one symbol');
        return;
    }
    btn.disabled = true;

    const strategy = document.getElementById('strategy').value;
    const startDate = document.getElementById('start-date').value || null;
    const endDate = document.getElementById('end-date').value || null;
    const barPeriod = RTYPE_LABELS[rtype] || 'Unknown';

    const payload = {
        strategy: strategy,
        strategy_params: collectParams(),
        symbols: selectedSymbols,
        rtype: rtype,
        publisher_id: selectedPublisherId,
        start_date: startDate,
        end_date: endDate
    };

    try {
        const res = await fetch('/api/backtest/run', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to start backtest');
        const runId = data.run_id;

        activeRuns[runId] = {
            strategy: strategy,
            symbols: [...selectedSymbols],
            barPeriod: barPeriod,
            startDate: startDate,
            endDate: endDate,
            status: 'queued',
            progress: 0
        };
        renderRuns();
        btn.disabled = false;

        pollBacktestStatus(runId);
    } catch (e) {
        alert(`Error: ${e.message}`);
        btn.disabled = false;
    }
}

async function restoreActiveRuns() {
    const res = await fetch('/api/backtest/running');
    const data = await res.json();
    (data.running || []).forEach(r => {
        activeRuns[r.run_id] = {
            strategy: r.strategy || 'Unknown',
            symbols: r.symbols || [],
            startDate: r.start_date || null,
            endDate: r.end_date || null,
            status: r.status || 'running',
            progress: r.progress || 0
        };
        pollBacktestStatus(r.run_id);
    });
    renderRuns();
}


/* ════════════════════════════════════════════════════════════════════
   Box 2 — Run Selection (Analysis)
   ════════════════════════════════════════════════════════════════════ */

let analysisRunId = null;
let completedRuns = [];

// Box 3 state
let perfSymbols = [];
let perfSelectedSymbol = null;
let perfSuggestionIndex = -1;

// Box 4 state
let roundtrips = [];
let filteredRoundtrips = [];
let sortColumn = 'symbol';
let sortAsc = true;
let chartType = 'c_bars';
let chartContext = 100;
let indicatorNames = [];
let chartSettingsData = {};
let _settingsVersion = 0;
let indicatorDefaultsData = {};
const chartCache = {};

const VALID_STYLES = ['line', 'histogram', 'dots', 'dash1', 'dash2', 'dash3', 'background1', 'background2'];
const VALID_COLORS = ['black', 'red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'teal'];
const VALID_WIDTHS = ['thin', 'normal', 'thick', 'extra_thick'];
const CHART_TYPE_OPTIONS = [
    {value: 'candlestick', label: 'Candlestick'},
    {value: 'oc_bars', label: 'OC Bars'},
    {value: 'c_bars', label: 'C Bars'},
    {value: 'bars', label: 'Bars'}
];

async function loadCompletedRuns() {
    try {
        const res = await fetch('/api/runs');
        const data = await res.json();
        completedRuns = (data.runs || []).filter(r => r.status === 'completed');
    } catch (e) {
        completedRuns = [];
    }
    renderRunSelect();
}

function renderRunSelect() {
    const select = document.getElementById('run-select');
    if (!select) return;
    const currentVal = select.value;
    let html = '<option value="">Select a completed run...</option>';
    completedRuns.forEach(r => {
        const config = r.config || {};
        const strategies = config.strategies ? config.strategies.join(', ') : r.name;
        const timePart = r.run_id.slice(11, 19).replace(/-/g, ':');
        const selected = r.run_id === analysisRunId ? 'selected' : '';
        html += `<option value="${r.run_id}" ${selected}>${strategies} (${timePart})</option>`;
    });
    select.innerHTML = html;
    // Restore selection if still valid
    if (analysisRunId && completedRuns.some(r => r.run_id === analysisRunId)) {
        select.value = analysisRunId;
    }
}

function onRunSelect() {
    const select = document.getElementById('run-select');
    const runId = select.value;
    if (runId) {
        selectAnalysisRun(runId);
    } else {
        clearAnalysis();
    }
}

async function selectAnalysisRun(runId) {
    analysisRunId = runId;
    // Update Box 2 dropdown
    const select = document.getElementById('run-select');
    if (select && select.value !== runId) {
        select.value = runId;
    }
    // Load Box 3 + Box 4 data in parallel
    await Promise.all([
        loadPerfSymbols(runId),
        loadTradesData(runId),
        loadIndicatorSettings(runId)
    ]);
}

function clearAnalysis() {
    analysisRunId = null;
    perfSymbols = [];
    perfSelectedSymbol = null;
    roundtrips = [];
    filteredRoundtrips = [];
    indicatorNames = [];
    chartSettingsData = {};
    // Reset Box 3
    const perfInput = document.getElementById('perf-symbol-input');
    if (perfInput) {
        perfInput.value = '';
        perfInput.disabled = true;
        perfInput.placeholder = 'Select a run first...';
    }
    renderPerfCharts();
    // Reset Box 4
    const tradesContent = document.getElementById('trades-content');
    if (tradesContent) tradesContent.innerHTML = '<div class="empty-content"><p>Select a run to view trades</p></div>';
    const tradesSettings = document.getElementById('trades-settings-panel');
    if (tradesSettings) tradesSettings.innerHTML = '';
    const indSettings = document.getElementById('trades-ind-settings-container');
    if (indSettings) indSettings.innerHTML = '';
}


/* ════════════════════════════════════════════════════════════════════
   Box 3 — Symbol Performance  (ported from performance.js)
   ════════════════════════════════════════════════════════════════════ */

async function loadPerfSymbols(runId) {
    renderPerfCharts();
    const res = await fetch(`/api/runs/${runId}/roundtrips`);
    const data = await res.json();
    const rts = data.roundtrips || [];
    perfSymbols = [...new Set(rts.map(rt => rt.symbol))].sort();
    perfSelectedSymbol = null;
    const input = document.getElementById('perf-symbol-input');
    if (input) {
        input.value = '';
        input.disabled = perfSymbols.length === 0;
        input.placeholder = perfSymbols.length === 0 ? 'No symbols in run' : 'Search symbol...';
    }
    renderPerfCharts();
}

function onPerfSymbolInput() {
    const input = document.getElementById('perf-symbol-input');
    const query = input.value.trim().toUpperCase();
    const suggestions = document.getElementById('perf-symbol-suggestions');
    perfSuggestionIndex = -1;
    if (!query) {
        suggestions.classList.remove('show');
        perfSelectedSymbol = null;
        renderPerfCharts();
        return;
    }
    const matches = perfSymbols.filter(s => s.toUpperCase().includes(query));
    if (matches.length === 0) {
        suggestions.classList.remove('show');
        return;
    }
    suggestions.innerHTML = matches.map((s, i) => `<div class="symbol-suggestion" data-symbol="${s}" onclick="selectPerfSymbol('${s}')">${s}</div>`).join('');
    suggestions.classList.add('show');
}

function onPerfSymbolKeydown(e) {
    const suggestions = document.getElementById('perf-symbol-suggestions');
    const items = suggestions.querySelectorAll('.symbol-suggestion');
    if (!suggestions.classList.contains('show') || items.length === 0) return;
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        perfSuggestionIndex = Math.min(perfSuggestionIndex + 1, items.length - 1);
        items.forEach((item, i) => item.classList.toggle('selected', i === perfSuggestionIndex));
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        perfSuggestionIndex = Math.max(perfSuggestionIndex - 1, 0);
        items.forEach((item, i) => item.classList.toggle('selected', i === perfSuggestionIndex));
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (perfSuggestionIndex >= 0 && perfSuggestionIndex < items.length) {
            selectPerfSymbol(items[perfSuggestionIndex].dataset.symbol);
        }
    } else if (e.key === 'Escape') {
        suggestions.classList.remove('show');
    }
}

function selectPerfSymbol(symbol) {
    perfSelectedSymbol = symbol;
    const input = document.getElementById('perf-symbol-input');
    if (input) input.value = symbol;
    const suggestions = document.getElementById('perf-symbol-suggestions');
    if (suggestions) suggestions.classList.remove('show');
    renderPerfCharts();
}

function renderPerfCharts() {
    const pnlContainer = document.getElementById('pnl-container');
    const journeyContainer = document.getElementById('journey-container');
    if (!pnlContainer || !journeyContainer) return;
    if (!analysisRunId || !perfSelectedSymbol) {
        pnlContainer.innerHTML = '<div class="empty-message">Select a run and symbol</div>';
        journeyContainer.innerHTML = '<div class="empty-message">Select a run and symbol</div>';
        return;
    }
    pnlContainer.innerHTML = '<div class="chart-loading">Loading...</div>';
    journeyContainer.innerHTML = '<div class="chart-loading">Loading...</div>';
    loadChartImage('pnl-container', `/api/runs/${analysisRunId}/pnl-summary.png?symbol=${encodeURIComponent(perfSelectedSymbol)}`);
    loadChartImage('journey-container', `/api/runs/${analysisRunId}/trade-journey.png?symbol=${encodeURIComponent(perfSelectedSymbol)}`);
}

function loadChartImage(containerId, url) {
    const container = document.getElementById(containerId);
    const img = new Image();
    img.onload = () => { container.innerHTML = ''; container.appendChild(img); };
    img.onerror = () => { container.innerHTML = '<div class="chart-loading">Failed to load chart</div>'; };
    img.src = url;
    img.alt = 'Chart';
}

// Close perf suggestions on outside click
document.addEventListener('click', (e) => {
    const suggestions = document.getElementById('perf-symbol-suggestions');
    const input = document.getElementById('perf-symbol-input');
    if (suggestions && input && !input.contains(e.target) && !suggestions.contains(e.target)) {
        suggestions.classList.remove('show');
    }
});


/* ════════════════════════════════════════════════════════════════════
   Box 4 — Trades  (ported from chart.js, trades mode only)
   ════════════════════════════════════════════════════════════════════ */

async function loadTradesData(runId) {
    const container = document.getElementById('trades-content');
    container.innerHTML = '<div class="empty-content"><p>Loading...</p></div>';
    const res = await fetch(`/api/runs/${runId}/roundtrips`);
    const data = await res.json();
    roundtrips = data.roundtrips || [];
    const tradeNums = {};
    roundtrips.forEach(rt => {
        tradeNums[rt.symbol] = (tradeNums[rt.symbol] || 0) + 1;
        rt.trade_num = tradeNums[rt.symbol];
    });
    sortColumn = 'symbol';
    sortAsc = true;
    renderTradesSettingsPanel();
    filterTradesData();
}

function renderTradesSettingsPanel() {
    const container = document.getElementById('trades-settings-panel');
    if (!container) return;
    const symbolFilterValue = '';
    container.innerHTML = `
        <div class="settings-box">
            <div class="settings-row">
                <div class="settings-group">
                    <label>Symbol:</label>
                    <input type="text" id="trades-symbol-filter" placeholder="Filter symbols..." value="${symbolFilterValue}" oninput="filterTradesData()">
                </div>
                <div class="settings-group">
                    <label>Context:</label>
                    <input type="number" id="chart-context" value="${chartContext}" min="10" max="500" onchange="onContextChange(this.value)">
                </div>
            </div>
        </div>
    `;
}

function filterTradesData() {
    const filterEl = document.getElementById('trades-symbol-filter');
    const query = filterEl ? filterEl.value.toLowerCase().trim() : '';
    if (!query) {
        filteredRoundtrips = [...roundtrips];
    } else {
        const terms = query.split(/[,\s]+/).filter(t => t.length > 0);
        filteredRoundtrips = roundtrips.filter(rt =>
            terms.some(term => rt.symbol.toLowerCase().includes(term))
        );
    }
    sortAndRender();
}

function sortBy(column) {
    if (sortColumn === column) {
        sortAsc = !sortAsc;
    } else {
        sortColumn = column;
        sortAsc = true;
    }
    sortAndRender();
}

function sortAndRender() {
    filteredRoundtrips.sort((a, b) => {
        let valA = a[sortColumn];
        let valB = b[sortColumn];
        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
    });
    renderTradesTable();
}

function formatTimestamp(ns) {
    const ms = BigInt(ns) / BigInt(1000000);
    const date = new Date(Number(ms));
    return date.toISOString().slice(0, 16).replace('T', ' ');
}

function renderTradesTable() {
    const container = document.getElementById('trades-content');
    if (roundtrips.length === 0) {
        container.innerHTML = '<div class="empty-table"><p>No round-trip trades found</p></div>';
        return;
    }
    const columns = [
        {key: 'symbol', label: 'Symbol'},
        {key: 'trade_num', label: '#'},
        {key: 'direction', label: 'Direction'},
        {key: 'duration_bars', label: 'Bars'},
        {key: 'max_position', label: 'Max Position'},
        {key: 'high_watermark', label: 'High Watermark'},
        {key: 'low_watermark', label: 'Low Watermark'},
        {key: 'max_drawdown', label: 'Max Drawdown'},
        {key: 'pnl_before_commission', label: 'PnL (Gross)'},
        {key: 'pnl_after_commission', label: 'PnL (Net)'},
    ];
    const headerHtml = columns.map(c => {
        const isSorted = sortColumn === c.key;
        const arrow = isSorted ? (sortAsc ? '▲' : '▼') : '▲';
        return `<th class="${isSorted ? 'sorted' : ''}" onclick="sortBy('${c.key}')">${c.label}<span class="sort-icon">${arrow}</span></th>`;
    }).join('');
    const rowsHtml = filteredRoundtrips.map((rt, idx) => {
        const dirClass = rt.direction.toLowerCase();
        const pnlGrossClass = rt.pnl_before_commission >= 0 ? 'positive' : 'negative';
        const pnlNetClass = rt.pnl_after_commission >= 0 ? 'positive' : 'negative';
        const pnlGrossSign = rt.pnl_before_commission >= 0 ? '+' : '';
        const pnlNetSign = rt.pnl_after_commission >= 0 ? '+' : '';
        const hwmClass = rt.high_watermark >= 0 ? 'positive' : 'negative';
        const hwmSign = rt.high_watermark >= 0 ? '+' : '';
        const lwmClass = rt.low_watermark >= 0 ? 'positive' : 'negative';
        const lwmSign = rt.low_watermark >= 0 ? '+' : '';
        const mddClass = rt.max_drawdown > 0 ? 'negative' : '';
        return `<tr class="data-row" onclick="toggleChart(${idx})">
            <td class="symbol">${rt.symbol}</td>
            <td>${rt.trade_num}</td>
            <td class="direction ${dirClass}">${rt.direction}</td>
            <td>${rt.duration_bars}</td>
            <td>${rt.max_position}</td>
            <td class="pnl ${hwmClass}">${hwmSign}${rt.high_watermark.toFixed(2)}</td>
            <td class="pnl ${lwmClass}">${lwmSign}${rt.low_watermark.toFixed(2)}</td>
            <td class="pnl ${mddClass}">${rt.max_drawdown > 0 ? '-' : ''}${rt.max_drawdown.toFixed(2)}</td>
            <td class="pnl ${pnlGrossClass}">${pnlGrossSign}${rt.pnl_before_commission.toFixed(2)}</td>
            <td class="pnl ${pnlNetClass}">${pnlNetSign}${rt.pnl_after_commission.toFixed(2)}</td>
        </tr>
        <tr class="chart-row" id="chart-row-${idx}">
            <td colspan="10">
                <div class="chart-container" id="chart-container-${idx}">
                    <div class="chart-loading">Loading chart...</div>
                </div>
            </td>
        </tr>`;
    }).join('');
    container.innerHTML = `
        <div class="trades-table-container">
            <table class="trades-table">
                <thead><tr>${headerHtml}</tr></thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        </div>
    `;
}

function onContextChange(value) {
    chartContext = parseInt(value) || 100;
    // Clear chart cache so re-opened charts use new context
    Object.keys(chartCache).forEach(k => delete chartCache[k]);
    _settingsVersion++;
    // Collapse and re-open any expanded chart rows
    document.querySelectorAll('#trades-content .chart-row.expanded').forEach(row => {
        const idx = parseInt(row.id.replace('chart-row-', ''));
        row.classList.remove('expanded');
        toggleChart(idx);
    });
}

function toggleChart(idx) {
    const chartRow = document.getElementById(`chart-row-${idx}`);
    if (chartRow.classList.contains('expanded')) {
        chartRow.classList.remove('expanded');
        return;
    }
    chartRow.classList.add('expanded');
    const container = document.getElementById(`chart-container-${idx}`);
    const rt = filteredRoundtrips[idx];
    const cacheKey = `${analysisRunId}_trade_${rt.symbol}_${rt.entry_ts}_${rt.exit_ts}_${chartType}_ctx${chartContext}_v${_settingsVersion}`;
    if (chartCache[cacheKey]) {
        container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
        return;
    }
    container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
    let url = `/api/runs/${analysisRunId}/chart.png?symbol=${encodeURIComponent(rt.symbol)}&start_ns=${rt.entry_ts}&end_ns=${rt.exit_ts}&direction=${rt.direction}&pnl=${rt.pnl_after_commission}&chart_type=${chartType}&context=${chartContext}`;
    url += `&_v=${_settingsVersion}`;
    const img = new Image();
    img.onload = () => {
        chartCache[cacheKey] = url;
        container.innerHTML = '';
        container.appendChild(img);
    };
    img.onerror = () => {
        container.innerHTML = '<div class="chart-loading">Failed to load chart</div>';
    };
    img.src = url;
    img.alt = 'Chart';
}


/* ── Indicator settings (ported from chart.js) ── */

function getDefaultPanel(name, assignedPanels) {
    const upper = name.toUpperCase();
    if (/^SMA_/.test(upper) || /^BB_UPPER_/.test(upper) || /^BB_LOWER_/.test(upper) ||
        /^PSAR_/.test(upper) || /PERIOD HIGH/.test(upper) || /PERIOD LOW/.test(upper)) {
        return 0;
    }
    const adxGroup = ['ADX_', 'PLUS_DI_', 'MINUS_DI_'];
    if (adxGroup.some(prefix => upper.startsWith(prefix))) {
        for (const [existingName, panel] of Object.entries(assignedPanels)) {
            if (adxGroup.some(prefix => existingName.toUpperCase().startsWith(prefix))) {
                return panel;
            }
        }
    }
    const maxPanel = Math.max(0, ...Object.values(assignedPanels));
    return maxPanel + 1;
}

async function loadIndicatorSettings(runId) {
    try {
        const [indRes, settingsRes] = await Promise.all([
            fetch(`/api/runs/${runId}/indicators`),
            fetch(`/api/runs/${runId}/chart-settings`)
        ]);
        const indData = await indRes.json();
        const settingsJson = await settingsRes.json();
        indicatorNames = indData.indicators || [];
        chartSettingsData = settingsJson || {};
        if (!chartSettingsData.indicators) chartSettingsData.indicators = {};
        if (!chartSettingsData.fill_between) chartSettingsData.fill_between = [];
        chartType = chartSettingsData.chart_type || (indicatorDefaultsData.chart_type || 'c_bars');
        const assignedPanels = {};
        indicatorNames.forEach((name, idx) => {
            if (!chartSettingsData.indicators[name]) {
                if (indicatorDefaultsData.indicators && indicatorDefaultsData.indicators[name]) {
                    const saved = indicatorDefaultsData.indicators[name];
                    const panel = saved.panel !== undefined ? saved.panel : getDefaultPanel(name, assignedPanels);
                    chartSettingsData.indicators[name] = {
                        panel: panel,
                        below_price: saved.below_price !== undefined ? saved.below_price : true,
                        style: saved.style || 'line',
                        color: saved.color || 'black',
                        width: saved.width || 'normal',
                        visible: saved.visible !== undefined ? saved.visible : true
                    };
                } else {
                    const panel = getDefaultPanel(name, assignedPanels);
                    chartSettingsData.indicators[name] = {
                        panel: panel,
                        below_price: true,
                        style: 'line',
                        color: 'black',
                        width: 'normal',
                        visible: true
                    };
                }
                assignedPanels[name] = chartSettingsData.indicators[name].panel;
            } else {
                const cfg = chartSettingsData.indicators[name];
                if (cfg.panel < 0 && cfg.below_price === undefined) {
                    cfg.panel = Math.abs(cfg.panel);
                    cfg.below_price = false;
                }
                if (cfg.below_price === undefined) {
                    cfg.below_price = true;
                }
                assignedPanels[name] = cfg.panel;
            }
        });
        renderIndicatorSettings();
    } catch (e) {
        console.error('Failed to load indicator settings', e);
    }
}

async function saveIndicatorSettings() {
    if (!analysisRunId) return;
    try {
        await fetch(`/api/runs/${analysisRunId}/chart-settings`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({...chartSettingsData, chart_type: chartType})
        });
        _settingsVersion++;
        Object.keys(chartCache).forEach(k => delete chartCache[k]);
        document.querySelectorAll('#trades-content .chart-row.expanded').forEach(row => {
            const idx = parseInt(row.id.replace('chart-row-', ''));
            row.classList.remove('expanded');
            toggleChart(idx);
        });
    } catch (e) {
        console.error('Failed to save indicator settings', e);
    }
}

async function loadIndicatorDefaults() {
    try {
        const res = await fetch('/api/indicator-defaults');
        indicatorDefaultsData = await res.json();
    } catch (e) { indicatorDefaultsData = {}; }
}

function saveIndicatorDefault(name, settings) {
    fetch('/api/indicator-defaults/' + encodeURIComponent(name), {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings)
    }).catch(e => console.error('Failed to save indicator default', e));
}

function saveGlobalDefaults(data) {
    fetch('/api/indicator-defaults', {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).catch(e => console.error('Failed to save global defaults', e));
}

function onIndSettingChange(name, field, value) {
    if (!chartSettingsData.indicators) chartSettingsData.indicators = {};
    if (!chartSettingsData.indicators[name]) chartSettingsData.indicators[name] = {};
    if (field === 'panel') {
        value = Math.max(0, parseInt(value) || 0);
        if (value === 0) {
            chartSettingsData.indicators[name].below_price = true;
        }
    }
    if (field === 'below_price') value = value === true || value === 'true';
    if (field === 'visible') value = value === true || value === 'true';
    chartSettingsData.indicators[name][field] = value;
    saveIndicatorDefault(name, chartSettingsData.indicators[name]);
    saveIndicatorSettings();
    if (field === 'panel') renderIndicatorSettings();
}

function onChartTypeChange(value) {
    chartType = value;
    saveIndicatorSettings();
    saveGlobalDefaults({chart_type: chartType});
}

function onFillBetweenChange(idx, field, value) {
    if (!chartSettingsData.fill_between) return;
    if (field === 'alpha') value = parseFloat(value) || 0.15;
    chartSettingsData.fill_between[idx][field] = value;
    saveIndicatorSettings();
}

function addFillBetween() {
    if (!chartSettingsData.fill_between) chartSettingsData.fill_between = [];
    const names = indicatorNames.length >= 2 ? indicatorNames : ['', ''];
    chartSettingsData.fill_between.push({
        upper: names[0] || '',
        lower: names[1] || '',
        color: 'blue',
        alpha: 0.15
    });
    renderIndicatorSettings();
}

function removeFillBetween(idx) {
    if (!chartSettingsData.fill_between) return;
    chartSettingsData.fill_between.splice(idx, 1);
    saveIndicatorSettings();
    renderIndicatorSettings();
}

function renderIndicatorSettings() {
    const container = document.getElementById('trades-ind-settings-container');
    if (!container) return;
    if (!analysisRunId) {
        container.innerHTML = '';
        return;
    }
    const styleOptions = VALID_STYLES.map(s =>
        `<option value="${s}">${s}</option>`
    ).join('');
    const colorOptions = VALID_COLORS.map(c =>
        `<option value="${c}">${c}</option>`
    ).join('');
    const widthOptions = VALID_WIDTHS.map(w =>
        `<option value="${w}">${w.replace('_', ' ')}</option>`
    ).join('');
    const indCfg = chartSettingsData.indicators || {};
    const rows = indicatorNames.map(name => {
        const cfg = indCfg[name] || {panel: 0, below_price: true, style: 'line', color: 'black', width: 'normal', visible: true};
        const panelVal = cfg.panel || 0;
        const belowChecked = cfg.below_price !== false ? 'checked' : '';
        const belowDisabled = panelVal === 0 ? 'disabled' : '';
        const selStyle = styleOptions.replace(`value="${cfg.style}"`, `value="${cfg.style}" selected`);
        const selColor = colorOptions.replace(`value="${cfg.color}"`, `value="${cfg.color}" selected`);
        const selWidth = widthOptions.replace(`value="${cfg.width}"`, `value="${cfg.width}" selected`);
        const checked = cfg.visible !== false ? 'checked' : '';
        return `<tr>
            <td class="ind-name" title="${name}">${name}</td>
            <td><input type="number" min="0" value="${panelVal}" style="width:50px" onchange="onIndSettingChange('${name}','panel',this.value)"></td>
            <td><input type="checkbox" ${belowChecked} ${belowDisabled} onchange="onIndSettingChange('${name}','below_price',this.checked)"></td>
            <td><select onchange="onIndSettingChange('${name}','style',this.value)">${selStyle}</select></td>
            <td><select onchange="onIndSettingChange('${name}','color',this.value)">${selColor}</select></td>
            <td><select onchange="onIndSettingChange('${name}','width',this.value)">${selWidth}</select></td>
            <td><input type="checkbox" ${checked} onchange="onIndSettingChange('${name}','visible',this.checked)"></td>
        </tr>`;
    }).join('');
    const indNameOptions = indicatorNames.map(n => `<option value="${n}">${n}</option>`).join('');
    const fbRows = (chartSettingsData.fill_between || []).map((fb, idx) => {
        const upperOpts = indNameOptions.replace(`value="${fb.upper}"`, `value="${fb.upper}" selected`);
        const lowerOpts = indNameOptions.replace(`value="${fb.lower}"`, `value="${fb.lower}" selected`);
        const fbColorOpts = colorOptions.replace(`value="${fb.color}"`, `value="${fb.color}" selected`);
        return `<div class="fill-between-row">
            <label>Upper:</label><select onchange="onFillBetweenChange(${idx},'upper',this.value)">${upperOpts}</select>
            <label>Lower:</label><select onchange="onFillBetweenChange(${idx},'lower',this.value)">${lowerOpts}</select>
            <label>Color:</label><select onchange="onFillBetweenChange(${idx},'color',this.value)">${fbColorOpts}</select>
            <label>Alpha:</label><input type="number" step="0.05" min="0" max="1" value="${fb.alpha}" onchange="onFillBetweenChange(${idx},'alpha',this.value)">
            <button class="btn-sm btn-danger" onclick="removeFillBetween(${idx})">Remove</button>
        </div>`;
    }).join('');
    const chartTypeOptions = CHART_TYPE_OPTIONS.map(o =>
        `<option value="${o.value}" ${chartType === o.value ? 'selected' : ''}>${o.label}</option>`
    ).join('');
    const indTable = indicatorNames.length > 0 ? `
                <table class="indicator-settings-table">
                    <thead><tr><th>Indicator</th><th>Panel</th><th>Below</th><th>Style</th><th>Color</th><th>Width</th><th>Visible</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
                <div class="fill-between-section">
                    <label>Fill Between</label>
                    ${fbRows}
                    <div style="margin-top:8px"><button class="btn-sm" onclick="addFillBetween()">+ Add Fill Between</button></div>
                </div>` : '';
    container.innerHTML = `
        <div class="indicator-settings-panel">
            <div class="indicator-settings-header">
                Chart Settings
            </div>
            <div id="ind-settings-body" class="indicator-settings-body">
                <div class="chart-settings-controls">
                    <div class="settings-group">
                        <label>Chart Type:</label>
                        <select onchange="onChartTypeChange(this.value)">${chartTypeOptions}</select>
                    </div>
                </div>
                ${indTable}
            </div>
        </div>
    `;
}


/* ════════════════════════════════════════════════════════════════════
   Init
   ════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    loadStrategies();
    loadCoverage();
    loadPresets();
    loadDbRuns();
    restoreActiveRuns();
    loadCompletedRuns();
    loadIndicatorDefaults();
});
