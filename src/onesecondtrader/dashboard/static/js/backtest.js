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
        // 1. Set bar period and show symbols section
        const barPeriodEl = document.getElementById('bar-period');
        barPeriodEl.value = String(preset.rtype);
        const section = document.getElementById('symbols-section');
        section.style.display = 'block';

        // Load publishers for this rtype
        await loadPublishers();

        // 2. Set publisher and load datasets
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

        // 3. Set dataset
        datasetSel.value = String(preset.publisher_id);
        selectedPublisherId = preset.publisher_id;

        // 4. Load coverage and show symbol selection
        await loadCoverageForPublisher(selectedPublisherId);
        document.getElementById('symbol-selection').style.display = 'block';
        document.getElementById('symbol-search').value = '';
        document.getElementById('search-results').innerHTML = '';

        // 5. Set symbols (filtered to available)
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
        const clickable = r.status === 'completed' ? `onclick="goToPerformance('${r.run_id}')"` : '';
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
            // Keep refreshing DB a few times to ensure status is reflected
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

function goToPerformance(runId) {
    window.location.href = `/performance?run_id=${runId}`;
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

document.addEventListener('DOMContentLoaded', () => {
    loadStrategies();
    loadCoverage();
    loadPresets();
    loadDbRuns();
    restoreActiveRuns();
});
