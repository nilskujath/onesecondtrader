# Styles

::: onesecondtrader.dashboard.styles
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

???+ quote "Source code in `styles.py`"

    ```python linenums="1"
    """
    CSS stylesheets and JavaScript for the dashboard UI.
    
    This module contains embedded CSS and JavaScript as Python string constants. The styles
    implement a dark-themed interface with a fixed sidebar navigation and responsive content
    areas.
    
    Constants:
        BASE_CSS: Global styles for layout, sidebar, cards, forms, and common elements.
        BACKTEST_CSS: Styles specific to the backtest configuration page.
        BACKTEST_JS: JavaScript for backtest page interactivity including:
            - Strategy and parameter loading
            - Publisher/dataset/symbol cascading selection
            - Symbol preset management
            - Date range validation
            - Backtest execution and run history display
    """
    
    BASE_CSS = """
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
    .empty-state p {
        margin-top: 8px;
        font-size: 14px;
    }
    """
    
    BACKTEST_CSS = """
    .container { max-width: none; height: 100vh; padding: 24px; display: flex; flex-direction: column; box-sizing: border-box; }
    .backtest-layout { display: flex; gap: 24px; flex: 1; min-height: 0; }
    .backtest-left { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .backtest-right { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .backtest-left .card, .backtest-right .card { flex: 1; display: flex; flex-direction: column; margin-bottom: 0; overflow: hidden; }
    .backtest-right .runs-list { flex: 1; overflow-y: auto; }
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
        color: #fff; font-size: 14px; cursor: pointer; width: 100%; }
    .btn:hover { background: #2ea043; }
    .btn:disabled { background: #30363d; cursor: not-allowed; }
    .date-row { display: flex; gap: 12px; }
    .date-row .form-group { flex: 1; margin-bottom: 0; }
    .symbol-section { background: #0d1117; border-radius: 6px; padding: 12px; }
    .publisher-row { display: flex; gap: 8px; margin-bottom: 12px; }
    .publisher-row select { flex: 1; }
    .preset-row { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
    .preset-row select { flex: 1; }
    .preset-row input { flex: 1; }
    .preset-row .btn-sm { padding: 6px 12px; font-size: 12px; width: auto; cursor: not-allowed; }
    .preset-row .btn-secondary { background: #30363d; }
    .preset-row .btn-secondary.active { background: #238636; cursor: pointer; }
    .preset-row .btn-secondary.active:hover { background: #2ea043; }
    .preset-row .btn-danger { background: #30363d; }
    .preset-row .btn-danger.active { background: #da3633; cursor: pointer; }
    .preset-row .btn-danger.active:hover { background: #f85149; }
    .search-row { display: flex; gap: 8px; margin-bottom: 8px; }
    .search-row input { flex: 1; }
    .search-results { max-height: 150px; overflow-y: auto; border: 1px solid #30363d; border-radius: 4px; margin-bottom: 12px; }
    .search-results:empty { display: none; }
    .search-result { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; border-bottom: 1px solid #21262d; cursor: pointer; }
    .search-result:last-child { border-bottom: none; }
    .search-result:hover { background: #161b22; }
    .search-result .symbol { font-family: monospace; }
    .selected-symbols { display: flex; flex-wrap: wrap; gap: 6px; min-height: 32px; max-height: 150px; overflow-y: auto; }
    .selected-tag { display: inline-flex; align-items: center; gap: 4px; background: #238636; color: #fff; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-family: monospace; }
    .selected-tag .remove { cursor: pointer; opacity: 0.7; }
    .selected-tag .remove:hover { opacity: 1; }
    .selected-label { font-size: 13px; color: #8b949e; margin-bottom: 6px; }
    .section-header { font-size: 14px; color: #8b949e; margin-bottom: 6px; margin-top: 8px; }
    .runs-list { display: flex; flex-direction: column; gap: 12px; }
    .run-item { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; display: flex; gap: 12px; align-items: flex-start; }
    .run-item.selected { border-color: #58a6ff; }
    .run-checkbox { flex-shrink: 0; margin-top: 2px; width: 16px; height: 16px; accent-color: #58a6ff; cursor: pointer; }
    .run-content { flex: 1; min-width: 0; }
    .run-content.clickable { cursor: pointer; }
    .run-content.clickable:hover { opacity: 0.8; }
    .run-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .run-name { font-family: monospace; font-size: 13px; color: #e6edf3; }
    .run-id { color: #8b949e; font-size: 11px; margin-left: 6px; }
    .run-status { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 10px; }
    .run-status.running { background: #9e6a03; color: #fff; }
    .run-status.completed { background: #238636; color: #fff; }
    .run-status.failed { background: #da3633; color: #fff; }
    .run-status.cancelled { background: #30363d; color: #8b949e; }
    .run-status.error { background: #da3633; color: #fff; }
    .run-meta { font-size: 12px; color: #8b949e; }
    .run-meta.with-progress { margin-bottom: 8px; }
    .progress-bar { height: 6px; background: #30363d; border-radius: 3px; overflow: hidden; }
    .progress-fill { height: 100%; background: #58a6ff; transition: width 0.3s ease; }
    .progress-fill.completed { background: #238636; }
    .progress-fill.error { background: #da3633; }
    .empty-runs { text-align: center; padding: 48px 24px; color: #8b949e; }
    .empty-runs p { font-size: 14px; }
    .runs-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #30363d; }
    .runs-toolbar .select-all-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #8b949e; cursor: pointer; }
    .runs-toolbar .select-all-label input { width: 16px; height: 16px; accent-color: #58a6ff; cursor: pointer; }
    .btn-delete { padding: 6px 12px; background: #da3633; border: none; border-radius: 6px; color: #fff; font-size: 13px; cursor: pointer; }
    .btn-delete:hover { background: #f85149; }
    .btn-delete:disabled { background: #30363d; cursor: not-allowed; color: #8b949e; }
    """
    
    BACKTEST_JS = """
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
            await loadPresets();
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
        await filterAndRenderPresets();
    }
    
    async function filterAndRenderPresets() {
        const sel = document.getElementById('preset-select');
        sel.innerHTML = '<option value="">-- Select Preset --</option>';
        const rtype = getSelectedRtype();
        const availableSymbols = symbolsForRtype[rtype] || [];
        for (const p of presets) {
            const res = await fetch(`/api/presets/${encodeURIComponent(p)}`);
            const data = await res.json();
            const hasAvailable = (data.symbols || []).some(s => availableSymbols.includes(s));
            if (hasAvailable) {
                sel.innerHTML += `<option value="${p}">${p}</option>`;
            }
        }
        updateButtonStates();
    }
    
    async function loadPreset() {
        const name = document.getElementById('preset-select').value;
        updateButtonStates();
        if (!name) {
            selectedSymbols = [];
            renderSelectedSymbols();
            updateDateRange();
            return;
        }
        const rtype = getSelectedRtype();
        const symbols = symbolsForRtype[rtype] || [];
        const res = await fetch(`/api/presets/${encodeURIComponent(name)}`);
        const data = await res.json();
        if (data.symbols) {
            selectedSymbols = data.symbols.filter(s => symbols.includes(s));
            renderSelectedSymbolsKeepPreset();
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
        const canSave = hasPresetName && selectedSymbols.length > 0;
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
            alert('Failed to delete runs');
        }
    }
    
    function renderRuns() {
        const container = document.getElementById('runs-list');
        const activeRunIds = Object.keys(activeRuns).filter(id => activeRuns[id].status === 'running');
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
            html += `<div class="run-item">
                <div class="run-content">
                    <div class="run-header">
                        <span class="run-name">${run.strategy}</span>
                        <span class="run-status running">running</span>
                    </div>
                    <div class="run-meta with-progress">${run.symbols.length} symbol${run.symbols.length !== 1 ? 's' : ''} · ${run.startDate || 'all'} to ${run.endDate || 'all'}</div>
                    <div class="progress-bar"><div class="progress-fill" style="width: ${progress}%"></div></div>
                </div>
            </div>`;
        });
    
        dbRuns.forEach(r => {
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
                status: 'running',
                progress: 10
            };
            renderRuns();
            btn.disabled = false;
    
            let progress = 10;
            const poll = setInterval(async () => {
                const r = await fetch(`/api/backtest/status/${runId}`);
                const d = await r.json();
                if (d.status === 'completed') {
                    clearInterval(poll);
                    delete activeRuns[runId];
                    await loadDbRuns();
                } else if (d.status.startsWith('error')) {
                    clearInterval(poll);
                    delete activeRuns[runId];
                    await loadDbRuns();
                } else {
                    progress = Math.min(progress + 5, 90);
                    activeRuns[runId].progress = progress;
                    renderRuns();
                }
            }, 1000);
        } catch (e) {
            alert(`Error: ${e.message}`);
            btn.disabled = false;
        }
    }
    
    function goToPerformance(runId) {
        window.location.href = `/performance?run_id=${runId}`;
    }
    
    document.addEventListener('DOMContentLoaded', () => {
        loadStrategies();
        loadCoverage();
        loadDbRuns();
    });
    """
    
    PERFORMANCE_CSS = """
    .container { max-width: none; height: 100vh; padding: 24px; display: flex; flex-direction: column; box-sizing: border-box; }
    .performance-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; gap: 16px; }
    .settings-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
    .settings-row { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
    .settings-group { display: flex; align-items: center; gap: 8px; }
    .settings-group label { font-size: 13px; color: #8b949e; font-weight: 500; }
    .settings-group select { padding: 8px 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; font-size: 13px; cursor: pointer; min-width: 250px; }
    .settings-group select:focus { outline: none; border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15); }
    .settings-group input { padding: 8px 12px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #e6edf3; font-size: 13px; min-width: 200px; }
    .settings-group input:focus { outline: none; border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15); }
    .settings-group input::placeholder { color: #484f58; }
    .symbol-suggestions { position: absolute; top: 100%; left: 0; right: 0; background: #161b22; border: 1px solid #30363d; border-radius: 6px; max-height: 200px; overflow-y: auto; z-index: 100; display: none; margin-top: 4px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .symbol-suggestions.show { display: block; }
    .symbol-suggestion { padding: 8px 12px; cursor: pointer; font-size: 13px; color: #e6edf3; }
    .symbol-suggestion:hover { background: #21262d; }
    .symbol-suggestion.selected { background: #388bfd33; color: #58a6ff; }
    .symbol-input-wrapper { position: relative; }
    .charts-row { display: flex; gap: 16px; flex: 1; min-height: 0; }
    .chart-card { flex: 1; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; min-width: 0; }
    .chart-card h3 { margin: 0 0 12px 0; font-size: 14px; font-weight: 500; color: #8b949e; }
    .chart-card .chart-content { flex: 1; display: flex; align-items: center; justify-content: center; min-height: 300px; }
    .chart-card img { max-width: 100%; max-height: 100%; height: auto; border-radius: 4px; background: #fff; }
    .chart-loading { color: #484f58; font-size: 13px; }
    .empty-message { text-align: center; padding: 48px 24px; color: #484f58; font-size: 14px; }
    @media (max-width: 900px) { .charts-row { flex-direction: column; } }
    """
    
    PERFORMANCE_JS = """
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
    """
    
    CHART_CSS = """
    .container { max-width: none; height: 100vh; padding: 24px; display: flex; flex-direction: column; box-sizing: border-box; }
    .chart-layout { display: flex; flex-direction: column; flex: 1; min-height: 0; }
    .chart-layout > .card { flex: 1; display: flex; flex-direction: column; margin-bottom: 0; min-height: 0; overflow-y: auto; }
    .empty-content { text-align: center; padding: 48px 24px; color: #8b949e; }
    .empty-content p { font-size: 14px; }
    .settings-panel { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 16px; margin-bottom: 16px; }
    .settings-row { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
    .settings-group { display: flex; align-items: center; gap: 8px; }
    .settings-group label { font-size: 13px; color: #8b949e; }
    .settings-group input[type="radio"] { margin: 0; cursor: pointer; }
    .settings-group input[type="number"] { width: 80px; padding: 6px 10px; background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #e6edf3; font-size: 13px; }
    .settings-group input[type="number"]:focus { outline: none; border-color: #58a6ff; }
    .settings-group select { padding: 6px 10px; background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #e6edf3; font-size: 13px; cursor: pointer; }
    .settings-group select:focus { outline: none; border-color: #58a6ff; }
    .settings-group select#run-select { min-width: 250px; }
    .settings-group input#symbol-filter { width: 180px; padding: 6px 10px; background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #e6edf3; font-size: 13px; }
    .settings-group input#symbol-filter:focus { outline: none; border-color: #58a6ff; }
    .settings-group input#symbol-filter::placeholder { color: #8b949e; }
    .settings-divider { width: 1px; height: 24px; background: #30363d; }
    .segments-table-container { }
    .segments-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .segments-table th { position: sticky; top: 0; background: #161b22; padding: 10px 12px; text-align: left; color: #8b949e; font-weight: 500; border-bottom: 1px solid #30363d; cursor: pointer; user-select: none; white-space: nowrap; }
    .segments-table th:hover { color: #e6edf3; }
    .segments-table th .sort-icon { margin-left: 4px; opacity: 0.5; }
    .segments-table th.sorted .sort-icon { opacity: 1; }
    .segments-table td { padding: 10px 12px; border-bottom: 1px solid #21262d; color: #e6edf3; white-space: nowrap; }
    .segments-table tr:hover td { background: #21262d; }
    .segments-table .symbol { font-family: monospace; }
    .segments-table .number { font-family: monospace; text-align: right; }
    .empty-table { text-align: center; padding: 48px 24px; color: #8b949e; }
    .segments-table tr.data-row { cursor: pointer; }
    .segments-table tr.chart-row { display: none; }
    .segments-table tr.chart-row.expanded { display: table-row; }
    .segments-table tr.chart-row td { padding: 16px; background: #0d1117; }
    .chart-container { position: relative; text-align: center; }
    .chart-container img { max-width: 100%; height: auto; border-radius: 4px; }
    .chart-loading { color: #8b949e; padding: 48px; }
    .trades-table-container { }
    .trades-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .trades-table th { position: sticky; top: 0; background: #161b22; padding: 10px 12px; text-align: left; color: #8b949e; font-weight: 500; border-bottom: 1px solid #30363d; cursor: pointer; user-select: none; white-space: nowrap; }
    .trades-table th:hover { color: #e6edf3; }
    .trades-table th .sort-icon { margin-left: 4px; opacity: 0.5; }
    .trades-table th.sorted .sort-icon { opacity: 1; }
    .trades-table td { padding: 10px 12px; border-bottom: 1px solid #21262d; color: #e6edf3; white-space: nowrap; }
    .trades-table tr:hover td { background: #21262d; }
    .trades-table .symbol { font-family: monospace; }
    .trades-table .number { font-family: monospace; text-align: right; }
    .trades-table .direction { font-weight: 500; }
    .trades-table .direction.long { color: #3fb950; }
    .trades-table .direction.short { color: #f85149; }
    .trades-table .pnl { font-weight: 500; font-family: monospace; }
    .trades-table .pnl.positive { color: #3fb950; }
    .trades-table .pnl.negative { color: #f85149; }
    .trades-table tr.data-row { cursor: pointer; }
    .trades-table tr.chart-row { display: none; }
    .trades-table tr.chart-row.expanded { display: table-row; }
    .trades-table tr.chart-row td { padding: 16px; background: #0d1117; }
    """
    
    CHART_JS = """
    let runs = [];
    let selectedRunId = null;
    let segments = [];
    let filteredSegments = [];
    let roundtrips = [];
    let filteredRoundtrips = [];
    let sortColumn = 'symbol';
    let sortAsc = true;
    let barPeriod = null;
    
    let settings = {
        mode: 'bars',
        barsPerChart: 500,
        overlap: 100,
        timePeriod: 'day'
    };
    
    const TIME_PERIOD_OPTIONS = {
        DAY: [{value: 'year', label: 'Year'}, {value: 'quarter', label: 'Quarter'}, {value: 'month', label: 'Month'}],
        HOUR: [{value: 'month', label: 'Month'}, {value: 'week', label: 'Week'}, {value: 'day', label: 'Day'}],
        MINUTE: [{value: 'day', label: 'Day'}, {value: '4hour', label: '4 Hours'}, {value: 'hour', label: 'Hour'}],
        SECOND: [{value: '15min', label: '15 Minutes'}, {value: '5min', label: '5 Minutes'}, {value: '1min', label: '1 Minute'}]
    };
    
    function loadSettings() {
        const saved = localStorage.getItem('chartSettings');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                settings = {...settings, ...parsed};
            } catch (e) {}
        }
    }
    
    function saveSettings() {
        localStorage.setItem('chartSettings', JSON.stringify(settings));
    }
    
    function getUrlRunId() {
        const params = new URLSearchParams(window.location.search);
        return params.get('run_id');
    }
    
    async function loadRuns() {
        loadSettings();
        const res = await fetch('/api/runs');
        const data = await res.json();
        runs = (data.runs || []).filter(r => r.status === 'completed');
        renderSettings();
        const urlRunId = getUrlRunId();
        if (urlRunId && runs.some(r => r.run_id === urlRunId)) {
            selectRun(urlRunId);
        }
    }
    
    function onRunChange() {
        const runId = document.getElementById('run-select').value;
        if (runId) {
            selectRun(runId);
        } else {
            selectedRunId = null;
            document.getElementById('charts-content').innerHTML = '<div class="empty-content"><p>Select a run to view charts</p></div>';
        }
    }
    
    function selectRun(runId) {
        selectedRunId = runId;
        const url = new URL(window.location);
        url.searchParams.set('run_id', runId);
        window.history.replaceState({}, '', url);
        const select = document.getElementById('run-select');
        if (select && select.value !== runId) {
            select.value = runId;
        }
        loadData(runId);
    }
    
    function renderSettings() {
        const container = document.getElementById('settings-panel');
        if (!container) return;
        const timePeriodOpts = TIME_PERIOD_OPTIONS[barPeriod] || TIME_PERIOD_OPTIONS['DAY'];
        if (settings.mode === 'time' && !timePeriodOpts.some(o => o.value === settings.timePeriod)) {
            settings.timePeriod = timePeriodOpts[0].value;
        }
        const barsChecked = settings.mode === 'bars' ? 'checked' : '';
        const timeChecked = settings.mode === 'time' ? 'checked' : '';
        const tradesChecked = settings.mode === 'trades' ? 'checked' : '';
        const barsDisabled = settings.mode !== 'bars' ? 'disabled' : '';
        const timeDisabled = settings.mode !== 'time' ? 'disabled' : '';
        const overlapDisabled = settings.mode === 'trades' ? 'disabled' : '';
        const periodOptions = timePeriodOpts.map(o =>
            `<option value="${o.value}" ${settings.timePeriod === o.value ? 'selected' : ''}>${o.label}</option>`
        ).join('');
        const runOptions = runs.length === 0
            ? '<option value="">No completed runs</option>'
            : '<option value="">Select a run...</option>' + runs.map(r => {
                const config = r.config || {};
                const strategies = config.strategies ? config.strategies.join(', ') : r.name;
                const timePart = r.run_id.slice(11, 19).replace(/-/g, ':');
                const selected = r.run_id === selectedRunId ? 'selected' : '';
                return `<option value="${r.run_id}" ${selected}>${strategies} (${timePart})</option>`;
            }).join('');
        const symbolFilterValue = settings.symbolFilter || '';
        container.innerHTML = `
            <div class="settings-row">
                <div class="settings-group">
                    <label>Run:</label>
                    <select id="run-select" onchange="onRunChange()">${runOptions}</select>
                </div>
                <div class="settings-group">
                    <label>Symbol:</label>
                    <input type="text" id="symbol-filter" placeholder="Filter symbols..." value="${symbolFilterValue}" oninput="filterData()">
                </div>
                <div class="settings-divider"></div>
                <div class="settings-group">
                    <input type="radio" id="mode-bars" name="split-mode" value="bars" ${barsChecked} onchange="onModeChange('bars')">
                    <label for="mode-bars">By Bars</label>
                </div>
                <div class="settings-group">
                    <label>Bars per chart:</label>
                    <input type="number" id="bars-per-chart" value="${settings.barsPerChart}" min="10" max="5000" ${barsDisabled} onchange="onBarsPerChartChange(this.value)">
                </div>
                <div class="settings-divider"></div>
                <div class="settings-group">
                    <input type="radio" id="mode-time" name="split-mode" value="time" ${timeChecked} onchange="onModeChange('time')">
                    <label for="mode-time">By Time</label>
                </div>
                <div class="settings-group">
                    <label>Period:</label>
                    <select id="time-period" ${timeDisabled} onchange="onTimePeriodChange(this.value)">${periodOptions}</select>
                </div>
                <div class="settings-divider"></div>
                <div class="settings-group">
                    <input type="radio" id="mode-trades" name="split-mode" value="trades" ${tradesChecked} onchange="onModeChange('trades')">
                    <label for="mode-trades">By Trades</label>
                </div>
                <div class="settings-divider"></div>
                <div class="settings-group">
                    <label>Overlap:</label>
                    <input type="number" id="overlap" value="${settings.overlap}" min="0" max="1000" ${overlapDisabled} onchange="onOverlapChange(this.value)">
                </div>
            </div>
        `;
    }
    
    function onModeChange(mode) {
        settings.mode = mode;
        saveSettings();
        renderSettings();
        if (selectedRunId) loadData(selectedRunId);
    }
    
    function onBarsPerChartChange(value) {
        settings.barsPerChart = parseInt(value) || 500;
        saveSettings();
        if (selectedRunId) loadData(selectedRunId);
    }
    
    function onTimePeriodChange(value) {
        settings.timePeriod = value;
        saveSettings();
        if (selectedRunId) loadData(selectedRunId);
    }
    
    function onOverlapChange(value) {
        settings.overlap = parseInt(value) || 0;
        saveSettings();
        if (selectedRunId) loadData(selectedRunId);
    }
    
    async function loadData(runId) {
        const container = document.getElementById('charts-content');
        container.innerHTML = '<div class="empty-content"><p>Loading...</p></div>';
        if (settings.mode === 'trades') {
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
            renderSettings();
            filterData();
        } else {
            const params = new URLSearchParams({
                mode: settings.mode,
                bars_per_chart: settings.barsPerChart,
                overlap: settings.overlap,
                time_period: settings.timePeriod
            });
            const res = await fetch(`/api/runs/${runId}/chart-segments?${params}`);
            const data = await res.json();
            segments = data.segments || [];
            barPeriod = data.bar_period;
            sortColumn = 'symbol';
            sortAsc = true;
            renderSettings();
            filterData();
        }
    }
    
    function filterData() {
        const query = document.getElementById('symbol-filter').value.toLowerCase().trim();
        settings.symbolFilter = query;
        if (settings.mode === 'trades') {
            if (!query) {
                filteredRoundtrips = [...roundtrips];
            } else {
                const terms = query.split(/[,\\s]+/).filter(t => t.length > 0);
                filteredRoundtrips = roundtrips.filter(rt =>
                    terms.some(term => rt.symbol.toLowerCase().includes(term))
                );
            }
        } else {
            if (!query) {
                filteredSegments = [...segments];
            } else {
                const terms = query.split(/[,\\s]+/).filter(t => t.length > 0);
                filteredSegments = segments.filter(seg =>
                    terms.some(term => seg.symbol.toLowerCase().includes(term))
                );
            }
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
        if (settings.mode === 'trades') {
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
        } else {
            filteredSegments.sort((a, b) => {
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
            renderSegmentsTable();
        }
    }
    
    function formatTimestamp(ns) {
        const ms = BigInt(ns) / BigInt(1000000);
        const date = new Date(Number(ms));
        return date.toISOString().slice(0, 16).replace('T', ' ');
    }
    
    function renderSegmentsTable() {
        const container = document.getElementById('charts-content');
        if (segments.length === 0) {
            container.innerHTML = '<div class="empty-table"><p>No chart segments found</p></div>';
            return;
        }
        const columns = [
            {key: 'symbol', label: 'Symbol'},
            {key: 'segment_num', label: 'Segment'},
            {key: 'start_ts', label: 'Start'},
            {key: 'end_ts', label: 'End'},
            {key: 'bar_count', label: 'Bars'},
        ];
        const headerHtml = columns.map(c => {
            const isSorted = sortColumn === c.key;
            const arrow = isSorted ? (sortAsc ? '▲' : '▼') : '▲';
            return `<th class="${isSorted ? 'sorted' : ''}" onclick="sortBy('${c.key}')">${c.label}<span class="sort-icon">${arrow}</span></th>`;
        }).join('');
        const rowsHtml = filteredSegments.map((seg, idx) => {
            const displayStart = seg.period_start_ns || seg.start_ts;
            const displayEnd = seg.period_end_ns || seg.end_ts;
            return `<tr class="data-row" onclick="toggleChart(${idx})">
                <td class="symbol">${seg.symbol}</td>
                <td class="number">${seg.segment_num}</td>
                <td>${formatTimestamp(displayStart)}</td>
                <td>${formatTimestamp(displayEnd)}</td>
                <td class="number">${seg.bar_count}</td>
            </tr>
            <tr class="chart-row" id="chart-row-${idx}">
                <td colspan="5">
                    <div class="chart-container" id="chart-container-${idx}">
                        <div class="chart-loading">Loading chart...</div>
                    </div>
                </td>
            </tr>`;
        }).join('');
        container.innerHTML = `
            <div class="segments-table-container">
                <table class="segments-table">
                    <thead><tr>${headerHtml}</tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            </div>
        `;
    }
    
    function renderTradesTable() {
        const container = document.getElementById('charts-content');
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
    
    const chartCache = {};
    
    function toggleChart(idx) {
        const chartRow = document.getElementById(`chart-row-${idx}`);
        if (chartRow.classList.contains('expanded')) {
            chartRow.classList.remove('expanded');
            return;
        }
        chartRow.classList.add('expanded');
        const container = document.getElementById(`chart-container-${idx}`);
        let url, cacheKey;
        if (settings.mode === 'trades') {
            const rt = filteredRoundtrips[idx];
            cacheKey = `${selectedRunId}_trade_${rt.symbol}_${rt.entry_ts}_${rt.exit_ts}`;
            if (chartCache[cacheKey]) {
                container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
                return;
            }
            container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
            url = `/api/runs/${selectedRunId}/chart.png?symbol=${encodeURIComponent(rt.symbol)}&start_ns=${rt.entry_ts}&end_ns=${rt.exit_ts}&direction=${rt.direction}&pnl=${rt.pnl_after_commission}`;
        } else {
            const seg = filteredSegments[idx];
            cacheKey = `${selectedRunId}_${seg.symbol}_${seg.start_ts}_${seg.end_ts}`;
            if (chartCache[cacheKey]) {
                container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
                return;
            }
            container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
            url = `/api/runs/${selectedRunId}/segment-chart.png?symbol=${encodeURIComponent(seg.symbol)}&start_ns=${seg.start_ts}&end_ns=${seg.end_ts}`;
            if (seg.period_start_ns && seg.period_end_ns) {
                url += `&period_start_ns=${seg.period_start_ns}&period_end_ns=${seg.period_end_ns}`;
            }
        }
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
    
    document.addEventListener('DOMContentLoaded', () => {
        loadRuns();
    });
    """
    
    ```
