/* New Explorer tab — uses Orchestrator-backed /api/explorer endpoints */

let coverageData = [];
let symbolsForRtype = {};
let symbolCoverageForRtype = {};
let selectedSymbols = [];
let globalMinDate = null;
let globalMaxDate = null;
let publishers = [];
let datasets = [];
let selectedPublisherId = null;
let selectedContractType = 'outrights';
let hasContinuousSymbols = false;
let allCoverageData = [];

let availableIndicators = [];
let selectedIndicators = [];
let dsPresets = [];
let indPresets = [];
let fillBetween = [];

let chartMode = 'bars';  // 'bars', 'time', 'condition'
let barsPerChart = 500;
let timePeriod = 'day';

let conditionalSegments = [];
let filteredConditionalSegments = [];
let sortColumn = 'symbol';
let sortAsc = true;

let chartType = 'c_bars';
let chartOverlap = 100;
let indicatorsCalculated = false;

let selectedConditions = [];
let conditionBuilder = { leftField: '', operator: '<=', rightField: '', rightValue: 0 };
let contextBars = 50;
let gapTolerance = 0;
let condPresets = [];

let activeExploreRunId = null;
let indicatorNames = [];
let chartSettingsData = {};
let _settingsVersion = 0;
let indicatorDefaultsData = {};

const RTYPE_LABELS = {32: 'Second', 33: 'Minute', 34: 'Hour', 35: 'Day'};
const CONDITION_BAR_FIELDS = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME'];
const CONDITION_OPERATORS = ['<=', '>=', '<', '>', '==', '!='];
const VALID_STYLES = ['line', 'histogram', 'dots', 'dash1', 'dash2', 'dash3', 'background1', 'background2'];
const VALID_COLORS = ['black', 'red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'teal'];
const VALID_WIDTHS = ['thin', 'normal', 'thick', 'extra_thick'];
const CHART_TYPE_OPTIONS = [
    {value: 'candlestick', label: 'Candlestick'},
    {value: 'oc_bars', label: 'OC Bars'},
    {value: 'c_bars', label: 'C Bars'},
    {value: 'bars', label: 'Bars'}
];
const TIME_PERIODS = ['1min', '5min', '10min', '15min', '20min', 'hour', '4hour', 'day', 'week', 'month', 'quarter', 'year'];
const TIME_PERIOD_LABELS = {
    '1min': '1 Min', '5min': '5 Min', '10min': '10 Min', '15min': '15 Min',
    '20min': '20 Min', 'hour': 'Hour', '4hour': '4 Hour', 'day': 'Day',
    'week': 'Week', 'month': 'Month', 'quarter': 'Quarter', 'year': 'Year'
};
const TIME_PERIODS_BY_RTYPE = {
    35: ['year', 'quarter'],
    34: ['quarter', 'month', 'week'],
    33: ['day', 'hour'],
    32: ['hour', '20min', '10min', '5min'],
};

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function humanizeClassName(name) {
    return name
        .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
        .replace(/([a-z])([A-Z])/g, '$1 $2');
}

function humanizeParam(name) {
    return name.split('_').map(function(w) {
        return w.charAt(0).toUpperCase() + w.slice(1);
    }).join(' ');
}

// ── Data Source Selection ──

async function loadBarPeriods() {
    const res = await fetch('/api/secmaster/symbols_coverage');
    const data = await res.json();
    coverageData = data.symbols || [];
    const rtypeSet = new Set();
    coverageData.forEach(row => rtypeSet.add(row.rtype));
    const rtypes = Array.from(rtypeSet).sort((a, b) => a - b);
    const sel = document.getElementById('bar-period');
    sel.innerHTML = '<option value="">-- Select bar period --</option>';
    rtypes.forEach(rt => {
        const label = RTYPE_LABELS[rt] || 'rtype ' + rt;
        sel.innerHTML += '<option value="' + rt + '">' + label + '</option>';
    });
}

function getSelectedRtype() {
    return parseInt(document.getElementById('bar-period').value) || null;
}

async function onBarPeriodChange() {
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
    updateButtonStates();
}

async function loadPublishers() {
    const rtype = getSelectedRtype();
    const url = rtype ? '/api/secmaster/publishers?rtype=' + rtype : '/api/secmaster/publishers';
    const res = await fetch(url);
    const data = await res.json();
    publishers = data.publishers || [];
    const sel = document.getElementById('publisher-name');
    sel.innerHTML = '<option value="">-- Select Publisher --</option>';
    publishers.forEach(function(p) { sel.innerHTML += '<option value="' + p + '">' + capitalize(p) + '</option>'; });
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
    updateButtonStates();
    if (!name) return;
    const url = rtype
        ? '/api/secmaster/publishers/' + encodeURIComponent(name) + '/datasets?rtype=' + rtype
        : '/api/secmaster/publishers/' + encodeURIComponent(name) + '/datasets';
    const res = await fetch(url);
    const data = await res.json();
    datasets = data.datasets || [];
    datasets.forEach(function(d) { datasetSel.innerHTML += '<option value="' + d.publisher_id + '">' + d.dataset + '</option>'; });
}

async function onDatasetChange() {
    const pubId = document.getElementById('publisher-dataset').value;
    selectedPublisherId = pubId ? parseInt(pubId) : null;
    selectedSymbols = [];
    renderSelectedSymbols();
    updateDateRange();
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
    updateButtonStates();
    if (selectedPublisherId) {
        await loadCoverageForPublisher(selectedPublisherId);
        document.getElementById('symbol-selection').style.display = 'block';
    } else {
        document.getElementById('symbol-selection').style.display = 'none';
    }
}

async function loadCoverageForPublisher(publisherId) {
    const rtype = getSelectedRtype();
    const url = '/api/secmaster/symbols_coverage?publisher_id=' + publisherId + '&rtype=' + rtype;
    const res = await fetch(url);
    const data = await res.json();
    allCoverageData = data.symbols || [];

    // Detect if continuous symbols exist
    hasContinuousSymbols = allCoverageData.some(function(row) { return row.symbol_type === 'continuous'; });
    var section = document.getElementById('contract-type-section');
    if (section) {
        section.style.display = hasContinuousSymbols ? '' : 'none';
        if (!hasContinuousSymbols) {
            selectedContractType = 'outrights';
            var radio = document.querySelector('input[name="contract-type"][value="outrights"]');
            if (radio) radio.checked = true;
        }
    }

    applyCoverageFilter();
}

function applyCoverageFilter() {
    coverageData = allCoverageData.filter(function(row) {
        if (!hasContinuousSymbols) return true;
        if (selectedContractType === 'continuous') return row.symbol_type === 'continuous';
        if (selectedContractType === 'spreads') return row.symbol_type === 'raw_symbol' && row.symbol.includes('-');
        // outrights
        return row.symbol_type === 'raw_symbol' && !row.symbol.includes('-');
    });
    symbolsForRtype = {};
    symbolCoverageForRtype = {};
    coverageData.forEach(function(row) {
        if (!symbolsForRtype[row.rtype]) {
            symbolsForRtype[row.rtype] = [];
            symbolCoverageForRtype[row.rtype] = {};
        }
        symbolsForRtype[row.rtype].push(row.symbol);
        symbolCoverageForRtype[row.rtype][row.symbol] = {min_ts: row.min_ts, max_ts: row.max_ts};
    });
}

function onContractTypeChange() {
    var radio = document.querySelector('input[name="contract-type"]:checked');
    selectedContractType = radio ? radio.value : 'outrights';
    applyCoverageFilter();
    selectedSymbols = [];
    renderSelectedSymbols();
    updateDateRange();
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
    updateButtonStates();
}

function searchSymbols() {
    const query = document.getElementById('symbol-search').value.toLowerCase();
    const container = document.getElementById('search-results');
    const rtype = getSelectedRtype();
    if (!query || !rtype) { container.innerHTML = ''; return; }
    const symbols = symbolsForRtype[rtype] || [];
    const matches = symbols.filter(function(s) { return s.toLowerCase().includes(query) && !selectedSymbols.includes(s); }).slice(0, 100);
    container.innerHTML = matches.map(function(s) {
        return '<div class="search-result" onclick="addSymbol(\'' + s + '\')"><span class="symbol">' + s + '</span></div>';
    }).join('');
}

function addSymbol(symbol) {
    if (!selectedSymbols.includes(symbol)) {
        selectedSymbols.push(symbol);
        renderSelectedSymbols();
        updateDateRange();
    }
    document.getElementById('symbol-search').value = '';
    document.getElementById('search-results').innerHTML = '';
    updateButtonStates();
}

function removeSymbol(symbol) {
    selectedSymbols = selectedSymbols.filter(function(s) { return s !== symbol; });
    renderSelectedSymbols();
    updateDateRange();
    updateButtonStates();
}

function renderSelectedSymbols() {
    const container = document.getElementById('selected-symbols');
    document.getElementById('selected-label').textContent = 'Selected (' + selectedSymbols.length + '):';
    container.innerHTML = selectedSymbols.map(function(s) {
        return '<span class="selected-tag">' + s + '<span class="remove" onclick="removeSymbol(\'' + s + '\')">&times;</span></span>';
    }).join('');
}

function tsToDate(ts) {
    const ms = Math.floor(ts / 1000000);
    const d = new Date(ms);
    return d.toISOString().split('T')[0];
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
    selectedSymbols.forEach(function(s) {
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

// ── Data Source Presets ──

async function loadDsPresets() {
    const res = await fetch('/api/presets');
    const data = await res.json();
    dsPresets = data.presets || [];
    const sel = document.getElementById('ds-preset-select');
    sel.innerHTML = '<option value="">-- Select Preset --</option>';
    dsPresets.forEach(function(p) {
        sel.innerHTML += '<option value="' + p.name + '">' + p.name + '</option>';
    });
    updateButtonStates();
}

async function loadDsPreset() {
    const name = document.getElementById('ds-preset-select').value;
    updateButtonStates();
    if (!name) return;
    const preset = dsPresets.find(function(p) { return p.name === name; });
    if (!preset) return;
    await applyDsPreset(preset);
}

async function applyDsPreset(preset) {
    try {
        const barPeriodEl = document.getElementById('bar-period');
        barPeriodEl.value = String(preset.rtype);
        const section = document.getElementById('symbols-section');
        section.style.display = 'block';
        await loadPublishers();
        const pubNameEl = document.getElementById('publisher-name');
        pubNameEl.value = preset.publisher_name;
        const rtype = preset.rtype;
        const url = '/api/secmaster/publishers/' + encodeURIComponent(preset.publisher_name) + '/datasets?rtype=' + rtype;
        const res = await fetch(url);
        const data = await res.json();
        datasets = data.datasets || [];
        const datasetSel = document.getElementById('publisher-dataset');
        datasetSel.innerHTML = '<option value="">-- Select Dataset --</option>';
        datasets.forEach(function(d) { datasetSel.innerHTML += '<option value="' + d.publisher_id + '">' + d.dataset + '</option>'; });
        datasetSel.value = String(preset.publisher_id);
        selectedPublisherId = preset.publisher_id;
        await loadCoverageForPublisher(selectedPublisherId);
        // Restore contract type from preset
        if (preset.symbol_type === 'continuous' && hasContinuousSymbols) {
            selectedContractType = 'continuous';
            var ctRadio = document.querySelector('input[name="contract-type"][value="continuous"]');
            if (ctRadio) ctRadio.checked = true;
        } else {
            selectedContractType = 'outrights';
            var ctRadio2 = document.querySelector('input[name="contract-type"][value="outrights"]');
            if (ctRadio2) ctRadio2.checked = true;
        }
        applyCoverageFilter();
        document.getElementById('symbol-selection').style.display = 'block';
        document.getElementById('symbol-search').value = '';
        document.getElementById('search-results').innerHTML = '';
        const availableSymbols = symbolsForRtype[rtype] || [];
        selectedSymbols = (preset.symbols || []).filter(function(s) { return availableSymbols.includes(s); });
        renderSelectedSymbols();
        updateDateRange();
    } catch (e) {
        console.error('Failed to apply data source preset', e);
    }
    updateButtonStates();
}

async function saveDsPreset() {
    const nameInput = document.getElementById('ds-preset-name');
    const name = nameInput.value.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const rtype = getSelectedRtype();
    if (!rtype) { alert('Select a bar period first'); return; }
    if (!selectedPublisherId) { alert('Select a publisher and dataset first'); return; }
    const publisherName = document.getElementById('publisher-name').value;
    const exists = dsPresets.some(function(p) { return p.name === name; });
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? '/api/presets/' + encodeURIComponent(name) : '/api/presets';
    var symbolType = (hasContinuousSymbols && selectedContractType === 'continuous') ? 'continuous' : 'raw_symbol';
    await fetch(apiUrl, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: name,
            rtype: rtype,
            publisher_name: publisherName,
            publisher_id: selectedPublisherId,
            symbols: selectedSymbols,
            symbol_type: symbolType
        })
    });
    nameInput.value = '';
    await loadDsPresets();
    document.getElementById('ds-preset-select').value = name;
    updateButtonStates();
}

async function deleteDsPreset() {
    const name = document.getElementById('ds-preset-select').value;
    if (!name) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + name + '"?')) return;
    await fetch('/api/presets/' + encodeURIComponent(name), {method: 'DELETE'});
    await loadDsPresets();
}

// ── Indicator & Chart Settings Presets ──

async function loadIndPresets() {
    const res = await fetch('/api/explore/presets');
    const data = await res.json();
    indPresets = data.presets || [];
    const sel = document.getElementById('ind-preset-select');
    sel.innerHTML = '<option value="">-- Select Preset --</option>';
    indPresets.forEach(function(p) {
        sel.innerHTML += '<option value="' + p.name + '">' + p.name + '</option>';
    });
    updateButtonStates();
}

async function loadIndPreset() {
    const name = document.getElementById('ind-preset-select').value;
    updateButtonStates();
    if (!name) return;
    const preset = indPresets.find(function(p) { return p.name === name; });
    if (!preset || !preset.config) return;
    var config = preset.config;
    selectedIndicators = (config.indicators || []).map(function(ind) {
        return {
            class_name: ind.class_name,
            params: ind.params || {},
            chart: ind.chart || {panel: 0, below_price: true, style: 'line', color: 'black', width: 'normal', visible: true}
        };
    });
    fillBetween = config.fill_between || [];
    chartType = config.chart_type || 'c_bars';
    chartOverlap = config.overlap != null ? config.overlap : 100;
    indicatorsCalculated = false;
    renderIndicatorList();
    updateButtonStates();
}

async function saveIndPreset() {
    const nameInput = document.getElementById('ind-preset-name');
    const name = nameInput.value.trim();
    if (!name) { alert('Enter a preset name'); return; }
    const config = {
        indicators: selectedIndicators,
        fill_between: fillBetween,
        chart_type: chartType,
        overlap: chartOverlap
    };
    const exists = indPresets.some(function(p) { return p.name === name; });
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? '/api/explore/presets/' + encodeURIComponent(name) : '/api/explore/presets';
    await fetch(apiUrl, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, config: config})
    });
    nameInput.value = '';
    await loadIndPresets();
    document.getElementById('ind-preset-select').value = name;
    updateButtonStates();
}

async function deleteIndPreset() {
    const name = document.getElementById('ind-preset-select').value;
    if (!name) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + name + '"?')) return;
    await fetch('/api/explore/presets/' + encodeURIComponent(name), {method: 'DELETE'});
    await loadIndPresets();
}

function updateButtonStates() {
    const calcBtn = document.getElementById('calculate-btn');
    const rtype = getSelectedRtype();
    if (calcBtn) {
        calcBtn.disabled = indicatorsCalculated || !(rtype && selectedPublisherId && selectedSymbols.length > 0 && selectedIndicators.length > 0);
    }
    // Data source preset buttons
    const dsSaveBtn = document.getElementById('ds-preset-save-btn');
    const dsDeleteBtn = document.getElementById('ds-preset-delete-btn');
    const dsSelect = document.getElementById('ds-preset-select');
    const dsNameInput = document.getElementById('ds-preset-name');
    const hasDsName = !!(dsNameInput && dsNameInput.value.trim().length > 0);
    const canDsSave = hasDsName && rtype && selectedPublisherId;
    if (dsSaveBtn) dsSaveBtn.classList.toggle('active', !!canDsSave);
    const hasDsSelected = !!(dsSelect && dsSelect.value);
    if (dsDeleteBtn) dsDeleteBtn.classList.toggle('active', hasDsSelected);
    // Indicator preset buttons
    const indSaveBtn = document.getElementById('ind-preset-save-btn');
    const indDeleteBtn = document.getElementById('ind-preset-delete-btn');
    const indSelect = document.getElementById('ind-preset-select');
    const indNameInput = document.getElementById('ind-preset-name');
    const hasIndName = !!(indNameInput && indNameInput.value.trim().length > 0);
    if (indSaveBtn) indSaveBtn.classList.toggle('active', hasIndName);
    const hasIndSelected = !!(indSelect && indSelect.value);
    if (indDeleteBtn) indDeleteBtn.classList.toggle('active', hasIndSelected);
    // Condition preset buttons
    const condSaveBtn = document.getElementById('cond-preset-save-btn');
    const condDeleteBtn = document.getElementById('cond-preset-delete-btn');
    const condSelect = document.getElementById('cond-preset-select');
    const condNameInput = document.getElementById('cond-preset-name');
    const hasCondName = !!(condNameInput && condNameInput.value.trim().length > 0);
    if (condSaveBtn) condSaveBtn.classList.toggle('active', hasCondName);
    const hasCondSelected = !!(condSelect && condSelect.value);
    if (condDeleteBtn) condDeleteBtn.classList.toggle('active', hasCondSelected);
}

// ── Indicator Management ──

async function loadAvailableIndicators() {
    const res = await fetch('/api/indicators');
    const data = await res.json();
    availableIndicators = data.indicators || [];
    renderIndicatorSelector();
}

function renderIndicatorSelector() {
    const sel = document.getElementById('indicator-class');
    sel.innerHTML = '<option value="">-- Select Indicator --</option>';
    const groups = {};
    availableIndicators.forEach(function(ind) {
        const pkg = ind.package || 'Other';
        if (!groups[pkg]) groups[pkg] = [];
        groups[pkg].push(ind);
    });
    Object.keys(groups).sort().forEach(function(pkg) {
        const optgroup = document.createElement('optgroup');
        optgroup.label = pkg;
        groups[pkg].forEach(function(ind) {
            const option = document.createElement('option');
            option.value = ind.class_name;
            option.textContent = humanizeClassName(ind.class_name);
            optgroup.appendChild(option);
        });
        sel.appendChild(optgroup);
    });
}

function onIndicatorClassChange() {
    const className = document.getElementById('indicator-class').value;
    const container = document.getElementById('indicator-params');
    if (!className) { container.innerHTML = ''; return; }
    const ind = availableIndicators.find(function(i) { return i.class_name === className; });
    if (!ind) { container.innerHTML = ''; return; }
    var indicatorClassParams = [];
    container.innerHTML = ind.params.map(function(p) {
        if (p.type === 'indicator_class') {
            indicatorClassParams.push(p.name);
            const opts = p.choices.map(function(c) {
                return '<option value="' + c + '"' + (c === p.default ? ' selected' : '') + '>' + c + '</option>';
            }).join('');
            return '<div class="param-input"><label>' + humanizeParam(p.name) + ':</label><select id="ip_' + p.name + '" onchange="onSourceIndicatorChange(\'' + p.name + '\')">' + opts + '</select></div>' +
                '<div id="source-subparams-' + p.name + '"></div>';
        }
        if (p.type === 'enum') {
            const opts = p.choices.map(function(c) {
                return '<option value="' + c + '"' + (c === p.default ? ' selected' : '') + '>' + c + '</option>';
            }).join('');
            return '<div class="param-input"><label>' + humanizeParam(p.name) + ':</label><select id="ip_' + p.name + '">' + opts + '</select></div>';
        }
        var inputType = p.type === 'float' ? 'number' : (p.type === 'int' ? 'number' : 'text');
        var step = p.type === 'float' ? '0.01' : '1';
        var val = p.default !== null && p.default !== undefined ? p.default : '';
        return '<div class="param-input"><label>' + humanizeParam(p.name) + ':</label><input type="' + inputType + '" id="ip_' + p.name + '" value="' + val + '" step="' + step + '"></div>';
    }).join('');
    indicatorClassParams.forEach(function(pName) { onSourceIndicatorChange(pName); });
    var addBtn = document.querySelector('.indicator-add-row .btn-add');
    if (className) addBtn.classList.add('active');
    else addBtn.classList.remove('active');
}

function onSourceIndicatorChange(paramName) {
    var className = document.getElementById('indicator-class').value;
    var ind = availableIndicators.find(function(i) { return i.class_name === className; });
    if (!ind) return;
    var pSpec = ind.params.find(function(p) { return p.name === paramName && p.type === 'indicator_class'; });
    if (!pSpec || !pSpec.source_params) return;
    var selEl = document.getElementById('ip_' + paramName);
    if (!selEl) return;
    var selectedSource = selEl.value;
    var subParams = pSpec.source_params[selectedSource] || [];
    var container = document.getElementById('source-subparams-' + paramName);
    if (!container) return;
    if (subParams.length === 0) { container.innerHTML = ''; return; }
    container.innerHTML = subParams.map(function(sp) {
        if (sp.type === 'enum') {
            var opts = sp.choices.map(function(c) {
                return '<option value="' + c + '"' + (c === sp.default ? ' selected' : '') + '>' + c + '</option>';
            }).join('');
            return '<div class="param-input"><label>' + humanizeParam(sp.name) + ':</label><select id="sp_' + paramName + '_' + sp.name + '">' + opts + '</select></div>';
        }
        var inputType = sp.type === 'float' ? 'number' : (sp.type === 'int' ? 'number' : 'text');
        var step = sp.type === 'float' ? '0.01' : '1';
        var val = sp.default !== null && sp.default !== undefined ? sp.default : '';
        return '<div class="param-input"><label>' + humanizeParam(sp.name) + ':</label><input type="' + inputType + '" id="sp_' + paramName + '_' + sp.name + '" value="' + val + '" step="' + step + '"></div>';
    }).join('');
}

function getDefaultPanelForClass(className) {
    const upper = className.toUpperCase();
    if (/MOVINGAVERAGE|BOLLINGER|PARABOLICSAR|PERIODHIGHLOW|PERIODEXTREME/.test(upper)) return 0;
    const assignedPanels = {};
    selectedIndicators.forEach(function(ind, idx) {
        if (ind.chart) assignedPanels[idx] = ind.chart.panel;
    });
    const maxPanel = Object.values(assignedPanels).length > 0 ? Math.max(0, ...Object.values(assignedPanels)) : 0;
    return maxPanel + 1;
}

function addIndicator() {
    const className = document.getElementById('indicator-class').value;
    if (!className) return;
    const ind = availableIndicators.find(function(i) { return i.class_name === className; });
    if (!ind) return;
    const params = {};
    ind.params.forEach(function(p) {
        const el = document.getElementById('ip_' + p.name);
        if (!el) return;
        if (p.type === 'int') params[p.name] = parseInt(el.value);
        else if (p.type === 'float') params[p.name] = parseFloat(el.value);
        else params[p.name] = el.value;
        if (p.type === 'indicator_class' && p.source_params) {
            var subParams = p.source_params[el.value] || [];
            if (subParams.length > 0) {
                var kwargsName = p.kwargs_name || 'source_kwargs';
                var kwargsDict = {};
                subParams.forEach(function(sp) {
                    var spEl = document.getElementById('sp_' + p.name + '_' + sp.name);
                    if (!spEl) return;
                    if (sp.type === 'int') kwargsDict[sp.name] = parseInt(spEl.value);
                    else if (sp.type === 'float') kwargsDict[sp.name] = parseFloat(spEl.value);
                    else kwargsDict[sp.name] = spEl.value;
                });
                params[kwargsName] = kwargsDict;
            }
        }
    });
    const defaultPanel = getDefaultPanelForClass(className);
    selectedIndicators.push({
        class_name: className,
        params: params,
        chart: {
            panel: defaultPanel,
            below_price: true,
            style: 'line',
            color: 'black',
            width: 'normal',
            visible: true
        }
    });
    indicatorsCalculated = false;
    renderIndicatorList();
    updateButtonStates();
    document.getElementById('indicator-class').value = '';
    document.getElementById('indicator-params').innerHTML = '';
    document.querySelector('.indicator-add-row .btn-add').classList.remove('active');
}

function removeIndicator(idx) {
    selectedIndicators.splice(idx, 1);
    indicatorsCalculated = false;
    renderIndicatorList();
    updateButtonStates();
}

function indicatorLabel(idx) {
    if (idx < 0 || idx >= selectedIndicators.length) return '';
    const ind = selectedIndicators[idx];
    var parts = [];
    Object.entries(ind.params).forEach(function(e) {
        if (typeof e[1] === 'object' && e[1] !== null) {
            Object.values(e[1]).forEach(function(v) { parts.push(v); });
        } else {
            parts.push(e[1]);
        }
    });
    return ind.class_name + '(' + parts.join(',') + ')';
}

function renderIndicatorList() {
    const container = document.getElementById('indicator-list');
    if (!container) return;
    if (selectedIndicators.length === 0) {
        container.innerHTML = '<div style="color:#8b949e;font-size:13px;padding:8px 0;">No indicators added</div>';
        return;
    }
    container.innerHTML = selectedIndicators.map(function(ind, idx) {
        return '<div class="indicator-list-item"><span>' + indicatorLabel(idx) + '</span>' +
            '<button class="btn-remove" onclick="removeIndicator(' + idx + ')">&times;</button></div>';
    }).join('');
}

// ── Calculation ──

async function onCalculate() {
    const btn = document.getElementById('calculate-btn');
    const progressBar = document.getElementById('explore-progress');
    const progressFill = document.getElementById('explore-progress-fill');
    const rtype = getSelectedRtype();
    if (!rtype || !selectedPublisherId || selectedSymbols.length === 0 || selectedIndicators.length === 0) return;
    btn.disabled = true;
    progressBar.classList.add('visible');
    progressFill.style.width = '0%';
    progressFill.className = 'progress-fill';

    const indicatorsPayload = selectedIndicators.map(function(ind) {
        return {class_name: ind.class_name, params: ind.params};
    });

    const symbolType = (hasContinuousSymbols && selectedContractType === 'continuous') ? 'continuous' : 'raw_symbol';
    const payload = {
        symbols: selectedSymbols,
        rtype: rtype,
        publisher_id: selectedPublisherId,
        start_date: document.getElementById('start-date').value || null,
        end_date: document.getElementById('end-date').value || null,
        indicators: indicatorsPayload,
        symbol_type: symbolType
    };

    try {
        const res = await fetch('/api/explorer/run', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) { alert(data.error); btn.disabled = false; progressBar.classList.remove('visible'); return; }
        pollExplorerStatus(data.run_id);
    } catch (e) {
        alert('Error: ' + e.message);
        btn.disabled = false;
        progressBar.classList.remove('visible');
    }
}

function pollExplorerStatus(runId) {
    const progressFill = document.getElementById('explore-progress-fill');
    const progressBar = document.getElementById('explore-progress');
    const btn = document.getElementById('calculate-btn');
    fetch('/api/explorer/status/' + runId)
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.status === 'completed') {
                progressFill.style.width = '100%';
                progressFill.classList.add('completed');
                setTimeout(function() { progressBar.classList.remove('visible'); }, 1000);
                onExplorationComplete(runId);
                return;
            }
            if (d.status && d.status.startsWith('error')) {
                progressFill.style.width = '100%';
                progressFill.style.background = '#da3633';
                btn.disabled = false;
                setTimeout(function() { progressBar.classList.remove('visible'); }, 2000);
                alert('Exploration failed: ' + d.status);
                return;
            }
            progressFill.style.width = Math.round((d.progress || 0) * 100) + '%';
            setTimeout(function() { pollExplorerStatus(runId); }, 500);
        })
        .catch(function() {
            setTimeout(function() { pollExplorerStatus(runId); }, 1000);
        });
}

async function onExplorationComplete(runId) {
    activeExploreRunId = runId;
    indicatorsCalculated = true;
    updateButtonStates();
    try {
        // Get actual indicator names from the run
        const indRes = await fetch('/api/runs/' + runId + '/indicators');
        const indData = await indRes.json();
        indicatorNames = indData.indicators || [];

        // Map selectedIndicators chart settings to actual indicator names by index
        chartSettingsData = {indicators: {}, fill_between: [], chart_type: chartType, overlap: chartOverlap};
        const assignedPanels = {};
        indicatorNames.forEach(function(name, idx) {
            if (indicatorDefaultsData.indicators && indicatorDefaultsData.indicators[name]) {
                var saved = indicatorDefaultsData.indicators[name];
                var panel = saved.panel !== undefined ? saved.panel : getDefaultPanel(name, assignedPanels);
                chartSettingsData.indicators[name] = {panel: panel, below_price: saved.below_price !== undefined ? saved.below_price : true, style: saved.style || 'line', color: saved.color || 'black', width: saved.width || 'normal', visible: saved.visible !== undefined ? saved.visible : true};
            } else if (idx < selectedIndicators.length && selectedIndicators[idx].chart) {
                chartSettingsData.indicators[name] = {...selectedIndicators[idx].chart};
            } else {
                const panel = getDefaultPanel(name, assignedPanels);
                chartSettingsData.indicators[name] = {panel: panel, below_price: true, style: 'line', color: 'black', width: 'normal', visible: true};
            }
            assignedPanels[name] = chartSettingsData.indicators[name].panel;
        });

        // Map fill_between labels to actual indicator names
        chartSettingsData.fill_between = fillBetween.map(function(fb) {
            var upperName = fb.upper, lowerName = fb.lower;
            selectedIndicators.forEach(function(ind, idx) {
                if (indicatorLabel(idx) === fb.upper && idx < indicatorNames.length) upperName = indicatorNames[idx];
                if (indicatorLabel(idx) === fb.lower && idx < indicatorNames.length) lowerName = indicatorNames[idx];
            });
            return {upper: upperName, lower: lowerName, color: fb.color, alpha: fb.alpha};
        });

        // Save chart settings to the run
        await fetch('/api/runs/' + runId + '/chart-settings', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(chartSettingsData)
        });

        // Show chart settings and display cards
        document.getElementById('chart-settings-card').style.display = '';
        document.getElementById('chart-display-card').style.display = '';

        renderIndicatorChartTable();
        renderChartModeControls();
        loadChartData();
    } catch (e) {
        console.error('Failed to complete exploration setup', e);
    }
}

// ── Chart Settings Table ──

function getDefaultPanel(name, assignedPanels) {
    const upper = name.toUpperCase();
    if (/^SMA_/.test(upper) || /^BB_UPPER_/.test(upper) || /^BB_LOWER_/.test(upper) || /^PSAR_/.test(upper) || /PERIOD HIGH/.test(upper) || /PERIOD LOW/.test(upper)) return 0;
    const adxGroup = ['ADX_', 'PLUS_DI_', 'MINUS_DI_'];
    if (adxGroup.some(function(prefix) { return upper.startsWith(prefix); })) {
        for (const [existingName, panel] of Object.entries(assignedPanels)) {
            if (adxGroup.some(function(prefix) { return existingName.toUpperCase().startsWith(prefix); })) return panel;
        }
    }
    const maxPanel = Math.max(0, ...Object.values(assignedPanels));
    return maxPanel + 1;
}

function onIndicatorChartSettingChange(idx, field, value) {
    var name = indicatorNames[idx];
    if (!name || !chartSettingsData.indicators[name]) return;
    if (field === 'panel') { value = Math.max(0, parseInt(value) || 0); if (value === 0) chartSettingsData.indicators[name].below_price = true; }
    if (field === 'below_price') value = value === true || value === 'true';
    if (field === 'visible') value = value === true || value === 'true';
    chartSettingsData.indicators[name][field] = value;
    saveIndicatorDefault(name, chartSettingsData.indicators[name]);
    if (!indicatorDefaultsData.indicators) indicatorDefaultsData.indicators = {};
    indicatorDefaultsData.indicators[name] = {...chartSettingsData.indicators[name]};
    if (field === 'panel') renderIndicatorChartTable();
    saveChartSettings();
}

function onFillBetweenChange(idx, field, value) {
    if (field === 'alpha') value = parseFloat(value) || 0.15;
    chartSettingsData.fill_between[idx][field] = value;
    saveChartSettings();
}

function addFillBetween() {
    const names = indicatorNames.length >= 2 ? [indicatorNames[0], indicatorNames[1]] : ['', ''];
    chartSettingsData.fill_between.push({ upper: names[0], lower: names[1], color: 'blue', alpha: 0.15 });
    renderIndicatorChartTable();
    saveChartSettings();
}

function removeFillBetween(idx) {
    chartSettingsData.fill_between.splice(idx, 1);
    renderIndicatorChartTable();
    saveChartSettings();
}

function formatParamName(name) {
    var result = name.replace(/_/g, ' ');
    result = result.replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2');
    result = result.replace(/([a-z])([A-Z])/g, '$1 $2');
    result = result.replace(/([a-zA-Z])(\d)/g, '$1 $2');
    return result.split(' ').map(function(word) {
        if (word === word.toUpperCase() && word.length > 1) return word;
        return word.charAt(0).toUpperCase() + word.slice(1);
    }).join(' ');
}

function renderIndicatorChartTable() {
    const container = document.getElementById('indicator-chart-table');
    if (!container) return;
    const styleOptions = VALID_STYLES.map(function(s) { return '<option value="' + s + '">' + formatParamName(s) + '</option>'; }).join('');
    const colorOptions = VALID_COLORS.map(function(c) { return '<option value="' + c + '">' + formatParamName(c) + '</option>'; }).join('');
    const widthOptions = VALID_WIDTHS.map(function(w) { return '<option value="' + w + '">' + formatParamName(w) + '</option>'; }).join('');
    const chartTypeOptions = CHART_TYPE_OPTIONS.map(function(o) {
        return '<option value="' + o.value + '"' + (chartType === o.value ? ' selected' : '') + '>' + o.label + '</option>';
    }).join('');

    let html = '<div class="indicator-settings-panel"><div class="indicator-settings-body">' +
        '<div class="chart-settings-controls">' +
        '<div class="settings-group"><label>Chart Type:</label><select onchange="onChartTypeChange(this.value)">' + chartTypeOptions + '</select></div>' +
        '<div class="settings-group"><label>Overlap:</label><input type="number" value="' + chartOverlap + '" min="0" max="1000" onchange="onOverlapChange(this.value)"></div>' +
        '</div>';

    if (indicatorNames.length > 0) {
        const rows = indicatorNames.map(function(name, idx) {
            const cfg = chartSettingsData.indicators[name] || {panel: 0, below_price: true, style: 'line', color: 'black', width: 'normal', visible: true};
            const panelVal = cfg.panel || 0;
            const belowChecked = cfg.below_price !== false ? 'checked' : '';
            const belowDisabled = panelVal === 0 ? 'disabled' : '';
            const selStyle = styleOptions.replace('value="' + cfg.style + '"', 'value="' + cfg.style + '" selected');
            const selColor = colorOptions.replace('value="' + cfg.color + '"', 'value="' + cfg.color + '" selected');
            const selWidth = widthOptions.replace('value="' + cfg.width + '"', 'value="' + cfg.width + '" selected');
            const checked = cfg.visible !== false ? 'checked' : '';
            return '<tr>' +
                '<td class="ind-name" title="' + name + '">' + name + '</td>' +
                '<td><input type="number" min="0" value="' + panelVal + '" style="width:50px" onchange="onIndicatorChartSettingChange(' + idx + ',\'panel\',this.value)"></td>' +
                '<td><input type="checkbox" ' + belowChecked + ' ' + belowDisabled + ' onchange="onIndicatorChartSettingChange(' + idx + ',\'below_price\',this.checked)"></td>' +
                '<td><select onchange="onIndicatorChartSettingChange(' + idx + ',\'style\',this.value)">' + selStyle + '</select></td>' +
                '<td><select onchange="onIndicatorChartSettingChange(' + idx + ',\'color\',this.value)">' + selColor + '</select></td>' +
                '<td><select onchange="onIndicatorChartSettingChange(' + idx + ',\'width\',this.value)">' + selWidth + '</select></td>' +
                '<td><input type="checkbox" ' + checked + ' onchange="onIndicatorChartSettingChange(' + idx + ',\'visible\',this.checked)"></td>' +
                '</tr>';
        }).join('');
        html += '<table class="indicator-settings-table">' +
            '<thead><tr><th>Indicator</th><th>Panel</th><th>Below</th><th>Style</th><th>Color</th><th>Width</th><th>Visible</th></tr></thead>' +
            '<tbody>' + rows + '</tbody></table>';
    } else {
        html += '<div style="color:#8b949e;font-size:13px;padding:8px 0;">No indicators computed yet</div>';
    }

    // Fill Between
    const fbRows = (chartSettingsData.fill_between || []).map(function(fb, idx) {
        const upperOpts = indicatorNames.map(function(l) {
            return '<option value="' + l + '"' + (l === fb.upper ? ' selected' : '') + '>' + l + '</option>';
        }).join('');
        const lowerOpts = indicatorNames.map(function(l) {
            return '<option value="' + l + '"' + (l === fb.lower ? ' selected' : '') + '>' + l + '</option>';
        }).join('');
        const fbColorOpts = colorOptions.replace('value="' + fb.color + '"', 'value="' + fb.color + '" selected');
        return '<div class="fill-between-row">' +
            '<label>Upper:</label><select onchange="onFillBetweenChange(' + idx + ',\'upper\',this.value)">' + upperOpts + '</select>' +
            '<label>Lower:</label><select onchange="onFillBetweenChange(' + idx + ',\'lower\',this.value)">' + lowerOpts + '</select>' +
            '<label>Color:</label><select onchange="onFillBetweenChange(' + idx + ',\'color\',this.value)">' + fbColorOpts + '</select>' +
            '<label>Alpha:</label><input type="number" step="0.05" min="0" max="1" value="' + fb.alpha + '" onchange="onFillBetweenChange(' + idx + ',\'alpha\',this.value)">' +
            '<button class="btn-sm btn-danger" onclick="removeFillBetween(' + idx + ')">Remove</button>' +
            '</div>';
    }).join('');
    html += '<div class="fill-between-section"><label>Fill Between</label>' + fbRows +
        '<div style="margin-top:8px"><button class="btn-sm" onclick="addFillBetween()">+ Add Fill Between</button></div></div>';

    html += '</div></div>';
    container.innerHTML = html;
}

async function saveChartSettings() {
    if (!activeExploreRunId) return;
    try {
        await fetch('/api/runs/' + activeExploreRunId + '/chart-settings', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({...chartSettingsData, chart_type: chartType, overlap: chartOverlap})
        });
        _settingsVersion++;
        Object.keys(chartCache).forEach(function(k) { delete chartCache[k]; });
        document.querySelectorAll('.chart-row.expanded').forEach(function(row) {
            var idx = parseInt(row.id.replace('chart-row-', ''));
            var container = document.getElementById('chart-container-' + idx);
            var seg = filteredConditionalSegments[idx];
            if (!container || !seg) return;
            container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
            var cacheKey = activeExploreRunId + '_' + chartMode + '_' + seg.symbol + '_' + seg.start_ts + '_' + seg.end_ts + '_' + chartType + '_v' + _settingsVersion;
            var url = '/api/runs/' + activeExploreRunId + '/segment-chart.png?symbol=' + encodeURIComponent(seg.symbol) + '&start_ns=' + seg.start_ts + '&end_ns=' + seg.end_ts + '&chart_type=' + chartType;
            if (seg.condition_start_ts && seg.condition_end_ts) {
                url += '&highlight_start_ns=' + seg.condition_start_ts + '&highlight_end_ns=' + seg.condition_end_ts;
            }
            url += '&_v=' + _settingsVersion;
            var img = new Image();
            img.onload = function() { chartCache[cacheKey] = url; container.innerHTML = ''; container.appendChild(img); };
            img.onerror = function() { container.innerHTML = '<div class="chart-loading">Failed to load chart</div>'; };
            img.src = url;
            img.alt = 'Chart';
        });
    } catch (e) {
        console.error('Failed to save chart settings', e);
    }
}

async function loadIndicatorDefaults() {
    try {
        var res = await fetch('/api/indicator-defaults');
        indicatorDefaultsData = await res.json();
    } catch (e) { indicatorDefaultsData = {}; }
}

function saveIndicatorDefault(name, settings) {
    fetch('/api/indicator-defaults/' + encodeURIComponent(name), {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings)
    }).catch(function(e) { console.error('Failed to save indicator default', e); });
}

function saveGlobalDefaults(data) {
    fetch('/api/indicator-defaults', {
        method: 'PUT', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).catch(function(e) { console.error('Failed to save global defaults', e); });
}

function onOverlapChange(value) {
    chartOverlap = parseInt(value) || 0;
    saveChartSettings();
    saveGlobalDefaults({overlap: chartOverlap});
    if (activeExploreRunId) loadChartData();
}

function onChartTypeChange(value) {
    chartType = value;
    saveChartSettings();
    saveGlobalDefaults({chart_type: chartType});
    if (activeExploreRunId) loadChartData();
}

// ── Chart Mode Tabs ──

function setChartMode(mode) {
    chartMode = mode;
    document.querySelectorAll('.mode-tab').forEach(function(tab) {
        tab.classList.toggle('active', tab.textContent.toLowerCase().replace(/\s/g, '').includes(mode));
    });
    // Re-highlight tabs properly
    document.querySelectorAll('.mode-tab').forEach(function(tab) {
        tab.classList.remove('active');
    });
    var tabs = document.querySelectorAll('.mode-tab');
    if (mode === 'bars') tabs[0].classList.add('active');
    else if (mode === 'time') tabs[1].classList.add('active');
    else if (mode === 'condition') tabs[2].classList.add('active');

    var condPresetRow = document.getElementById('cond-preset-row');
    if (condPresetRow) condPresetRow.style.display = (mode === 'condition') ? '' : 'none';

    renderChartModeControls();
    loadChartData();
}

function renderChartModeControls() {
    const container = document.getElementById('chart-mode-controls');
    if (!container) return;
    let html = '';
    if (chartMode === 'bars') {
        html = '<div class="mode-controls-row">' +
            '<label>Bars per chart:</label><input type="number" value="' + barsPerChart + '" min="10" max="10000" onchange="barsPerChart=parseInt(this.value)||500;loadChartData()">' +
            '</div>';
    } else if (chartMode === 'time') {
        var rtype = getSelectedRtype();
        var periods = (rtype && TIME_PERIODS_BY_RTYPE[rtype]) ? TIME_PERIODS_BY_RTYPE[rtype] : TIME_PERIODS;
        if (periods.indexOf(timePeriod) === -1) timePeriod = periods[0];
        const periodOpts = periods.map(function(p) {
            return '<option value="' + p + '"' + (timePeriod === p ? ' selected' : '') + '>' + (TIME_PERIOD_LABELS[p] || p) + '</option>';
        }).join('');
        html = '<div class="mode-controls-row">' +
            '<label>Time period:</label><select onchange="timePeriod=this.value;loadChartData()">' + periodOpts + '</select>' +
            '</div>';
    } else if (chartMode === 'condition') {
        html = renderConditionControls();
    }
    container.innerHTML = html;
}

function renderConditionControls() {
    if (!conditionBuilder.leftField) {
        if (CONDITION_BAR_FIELDS.length > 0) conditionBuilder.leftField = CONDITION_BAR_FIELDS[0];
    }

    const barFieldOpts = CONDITION_BAR_FIELDS.map(function(f) { return '<option value="' + f + '"' + (conditionBuilder.leftField === f ? ' selected' : '') + '>' + f + '</option>'; }).join('');
    const indOpts = indicatorNames.map(function(n) { return '<option value="' + n + '"' + (conditionBuilder.leftField === n ? ' selected' : '') + '>' + n + '</option>'; }).join('');
    var leftOptions = '<optgroup label="Bar Fields">' + barFieldOpts + '</optgroup>';
    if (indicatorNames.length > 0) leftOptions += '<optgroup label="Indicators">' + indOpts + '</optgroup>';

    const rightBarFieldOpts = CONDITION_BAR_FIELDS.map(function(f) { return '<option value="' + f + '"' + (conditionBuilder.rightField === f ? ' selected' : '') + '>' + f + '</option>'; }).join('');
    const rightIndOpts = indicatorNames.map(function(n) { return '<option value="' + n + '"' + (conditionBuilder.rightField === n ? ' selected' : '') + '>' + n + '</option>'; }).join('');
    var rightOptions = '<option value=""' + (!conditionBuilder.rightField ? ' selected' : '') + '>(Value)</option><optgroup label="Bar Fields">' + rightBarFieldOpts + '</optgroup>';
    if (indicatorNames.length > 0) rightOptions += '<optgroup label="Indicators">' + rightIndOpts + '</optgroup>';

    const opOptions = CONDITION_OPERATORS.map(function(op) { return '<option value="' + op + '"' + (conditionBuilder.operator === op ? ' selected' : '') + '>' + op + '</option>'; }).join('');
    const valueInputStyle = conditionBuilder.rightField ? 'display:none' : '';

    var html = '<div class="conditional-settings-box"><div class="settings-row">' +
        '<div class="settings-group"><label>Left:</label><select onchange="onBuilderChange(\'leftField\', this.value)">' + leftOptions + '</select></div>' +
        '<div class="settings-group"><label>Operator:</label><select onchange="onBuilderChange(\'operator\', this.value)">' + opOptions + '</select></div>' +
        '<div class="settings-group"><label>Right:</label><select onchange="onBuilderChange(\'rightField\', this.value)">' + rightOptions + '</select></div>' +
        '<div class="settings-group" style="' + valueInputStyle + '"><label>Value:</label><input type="number" step="any" value="' + conditionBuilder.rightValue + '" onchange="onBuilderChange(\'rightValue\', parseFloat(this.value))"></div>' +
        '<div class="settings-group"><button class="btn-add active" onclick="addCondition()">+ Add</button></div>' +
        '</div>';

    if (selectedConditions.length > 0) {
        var rows = selectedConditions.map(function(c, idx) {
            return '<tr><td style="font-family:monospace;font-size:13px;">' + conditionToText(c) + '</td>' +
                '<td><button class="btn-remove" onclick="removeCondition(' + idx + ')">&times;</button></td></tr>';
        }).join('');
        html += '<table class="indicator-settings-table" style="margin-top:8px;">' +
            '<thead><tr><th>Condition</th><th></th></tr></thead>' +
            '<tbody>' + rows + '</tbody></table>';
    } else {
        html += '<div style="color:#8b949e;font-size:13px;padding:8px 0;">No conditions added (shows all data as one segment per symbol)</div>';
    }

    html += '<div class="settings-row" style="margin-top:8px;">' +
        '<div class="settings-group"><label>Context bars:</label><input type="number" value="' + contextBars + '" min="0" max="500" onchange="contextBars=parseInt(this.value);loadChartData()"></div>' +
        '<div class="settings-group"><label>Gap tolerance:</label><input type="number" value="' + gapTolerance + '" min="0" max="100" onchange="gapTolerance=parseInt(this.value);loadChartData()"></div>' +
        '</div></div>';

    return html;
}

function conditionToText(c) {
    if (c.rightField) return c.leftField + ' ' + c.operator + ' ' + c.rightField;
    return c.leftField + ' ' + c.operator + ' ' + c.rightValue;
}

function onBuilderChange(field, value) {
    conditionBuilder[field] = value;
    if (field === 'rightField') renderChartModeControls();
}

function addCondition() {
    if (!conditionBuilder.leftField) return;
    if (!conditionBuilder.rightField && (conditionBuilder.rightValue === null || conditionBuilder.rightValue === undefined || isNaN(conditionBuilder.rightValue))) return;
    var cond = {
        leftField: conditionBuilder.leftField,
        operator: conditionBuilder.operator,
        rightField: conditionBuilder.rightField || null,
        rightValue: conditionBuilder.rightField ? null : conditionBuilder.rightValue
    };
    selectedConditions.push(cond);
    renderChartModeControls();
    loadChartData();
}

function removeCondition(idx) {
    selectedConditions.splice(idx, 1);
    renderChartModeControls();
    loadChartData();
}

// ── Condition Presets ──

async function loadCondPresets() {
    const res = await fetch('/api/explore/condition-presets');
    const data = await res.json();
    condPresets = data.presets || [];
    const sel = document.getElementById('cond-preset-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">-- Select Preset --</option>';
    condPresets.forEach(function(p) {
        sel.innerHTML += '<option value="' + p.name + '">' + p.name + '</option>';
    });
    updateButtonStates();
}

async function loadCondPreset() {
    const sel = document.getElementById('cond-preset-select');
    const name = sel ? sel.value : '';
    updateButtonStates();
    if (!name) return;
    const preset = condPresets.find(function(p) { return p.name === name; });
    if (!preset || !preset.config) return;
    var config = preset.config;
    selectedConditions = (config.conditions || []).map(function(c) {
        return { leftField: c.leftField, operator: c.operator, rightField: c.rightField || null, rightValue: c.rightValue != null ? c.rightValue : null };
    });
    contextBars = config.contextBars != null ? config.contextBars : 50;
    gapTolerance = config.gapTolerance != null ? config.gapTolerance : 0;
    if (chartMode === 'condition') renderChartModeControls();
    loadChartData();
}

async function saveCondPreset() {
    const nameInput = document.getElementById('cond-preset-name');
    const name = nameInput ? nameInput.value.trim() : '';
    if (!name) { alert('Enter a preset name'); return; }
    const config = { conditions: selectedConditions, contextBars: contextBars, gapTolerance: gapTolerance };
    const exists = condPresets.some(function(p) { return p.name === name; });
    const method = exists ? 'PUT' : 'POST';
    const apiUrl = exists ? '/api/explore/condition-presets/' + encodeURIComponent(name) : '/api/explore/condition-presets';
    await fetch(apiUrl, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ name: name, config: config })
    });
    if (nameInput) nameInput.value = '';
    await loadCondPresets();
    const condSel = document.getElementById('cond-preset-select');
    if (condSel) condSel.value = name;
    updateButtonStates();
}

async function deleteCondPreset() {
    const sel = document.getElementById('cond-preset-select');
    const name = sel ? sel.value : '';
    if (!name) { alert('Select a preset to delete'); return; }
    if (!confirm('Delete preset "' + name + '"?')) return;
    await fetch('/api/explore/condition-presets/' + encodeURIComponent(name), { method: 'DELETE' });
    await loadCondPresets();
}

// ── Chart Data Loading ──

async function loadChartData() {
    if (!activeExploreRunId) return;
    const container = document.getElementById('charts-content');
    container.innerHTML = '<div class="empty-content"><p>Loading...</p></div>';

    try {
        if (chartMode === 'bars') {
            const res = await fetch('/api/runs/' + activeExploreRunId + '/chart-segments?mode=bars&bars_per_chart=' + barsPerChart + '&overlap=' + chartOverlap);
            const data = await res.json();
            conditionalSegments = data.segments || [];
        } else if (chartMode === 'time') {
            const res = await fetch('/api/runs/' + activeExploreRunId + '/chart-segments?mode=time&time_period=' + timePeriod + '&overlap=' + chartOverlap);
            const data = await res.json();
            conditionalSegments = data.segments || [];
        } else if (chartMode === 'condition') {
            if (selectedConditions.length === 0) {
                container.innerHTML = '<div class="empty-content"><p>Select one or more conditions to show filtered charts.</p></div>';
                return;
            }
            var conditions = selectedConditions.map(function(c) {
                var spec = { left_field: c.leftField, operator: c.operator };
                if (c.rightField) spec.right_field = c.rightField;
                else spec.right_value = c.rightValue;
                return spec;
            });
            const res = await fetch('/api/runs/' + activeExploreRunId + '/conditional-segments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ conditions: conditions, context_bars: contextBars, gap_tolerance: gapTolerance })
            });
            const data = await res.json();
            conditionalSegments = data.segments || [];
        }
        sortColumn = 'symbol';
        sortAsc = true;
        filteredConditionalSegments = [...conditionalSegments];
        sortAndRender();
    } catch (e) {
        container.innerHTML = '<div class="empty-content"><p>Error loading chart data</p></div>';
    }
}

// ── Chart Display ──

function sortBy(column) {
    if (sortColumn === column) { sortAsc = !sortAsc; } else { sortColumn = column; sortAsc = true; }
    sortAndRender();
}

function sortAndRender() {
    filteredConditionalSegments.sort(function(a, b) {
        var valA = a[sortColumn], valB = b[sortColumn];
        if (typeof valA === 'string') { valA = valA.toLowerCase(); valB = (valB || '').toLowerCase(); }
        if (valA < valB) return sortAsc ? -1 : 1;
        if (valA > valB) return sortAsc ? 1 : -1;
        return 0;
    });
    renderSegmentsTable();
}

function formatTimestamp(ns) {
    var ms = BigInt(ns) / BigInt(1000000);
    var date = new Date(Number(ms));
    return date.toISOString().slice(0, 16).replace('T', ' ');
}

var chartCache = {};

function toggleChart(idx) {
    const chartRow = document.getElementById('chart-row-' + idx);
    if (chartRow.classList.contains('expanded')) { chartRow.classList.remove('expanded'); return; }
    chartRow.classList.add('expanded');
    const container = document.getElementById('chart-container-' + idx);
    const seg = filteredConditionalSegments[idx];
    var cacheKey = activeExploreRunId + '_' + chartMode + '_' + seg.symbol + '_' + seg.start_ts + '_' + seg.end_ts + '_' + chartType + '_v' + _settingsVersion;
    if (chartCache[cacheKey]) { container.innerHTML = '<img src="' + chartCache[cacheKey] + '" alt="Chart">'; return; }
    container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
    var url = '/api/runs/' + activeExploreRunId + '/segment-chart.png?symbol=' + encodeURIComponent(seg.symbol) + '&start_ns=' + seg.start_ts + '&end_ns=' + seg.end_ts + '&chart_type=' + chartType;
    if (seg.condition_start_ts && seg.condition_end_ts) {
        url += '&highlight_start_ns=' + seg.condition_start_ts + '&highlight_end_ns=' + seg.condition_end_ts;
    }
    url += '&_v=' + _settingsVersion;
    var img = new Image();
    img.onload = function() { chartCache[cacheKey] = url; container.innerHTML = ''; container.appendChild(img); };
    img.onerror = function() { container.innerHTML = '<div class="chart-loading">Failed to load chart</div>'; };
    img.src = url;
    img.alt = 'Chart';
}

function renderSegmentsTable() {
    const container = document.getElementById('charts-content');
    if (filteredConditionalSegments.length === 0) {
        container.innerHTML = '<div class="empty-table"><p>No segments found</p></div>';
        return;
    }

    // Determine columns based on mode
    var columns;
    if (chartMode === 'condition') {
        columns = [
            {key: 'symbol', label: 'Symbol'},
            {key: 'segment_num', label: 'Region #'},
            {key: 'condition_start_ts', label: 'Condition Start'},
            {key: 'condition_end_ts', label: 'Condition End'},
            {key: 'condition_bar_count', label: 'Condition Bars'},
            {key: 'bar_count', label: 'Total Bars'},
        ];
    } else {
        columns = [
            {key: 'symbol', label: 'Symbol'},
            {key: 'segment_num', label: 'Segment #'},
            {key: 'start_ts', label: 'Start'},
            {key: 'end_ts', label: 'End'},
            {key: 'bar_count', label: 'Bars'},
        ];
    }

    const colCount = columns.length;
    const headerHtml = columns.map(function(c) {
        const isSorted = sortColumn === c.key;
        const arrow = isSorted ? (sortAsc ? '\u25B2' : '\u25BC') : '\u25B2';
        return '<th class="' + (isSorted ? 'sorted' : '') + '" onclick="sortBy(\'' + c.key + '\')">' + c.label + '<span class="sort-icon">' + arrow + '</span></th>';
    }).join('');

    const rowsHtml = filteredConditionalSegments.map(function(seg, idx) {
        var cells;
        if (chartMode === 'condition') {
            cells = '<td class="symbol">' + seg.symbol + '</td>' +
                '<td class="number">' + seg.segment_num + '</td>' +
                '<td>' + (seg.condition_start_ts ? formatTimestamp(seg.condition_start_ts) : '-') + '</td>' +
                '<td>' + (seg.condition_end_ts ? formatTimestamp(seg.condition_end_ts) : '-') + '</td>' +
                '<td class="number">' + (seg.condition_bar_count || 0) + '</td>' +
                '<td class="number">' + seg.bar_count + '</td>';
        } else if (chartMode === 'time') {
            cells = '<td class="symbol">' + seg.symbol + '</td>' +
                '<td class="number">' + seg.segment_num + '</td>' +
                '<td>' + formatTimestamp(seg.period_start_ns) + '</td>' +
                '<td>' + formatTimestamp(seg.period_end_ns) + '</td>' +
                '<td class="number">' + seg.bar_count + '</td>';
        } else {
            cells = '<td class="symbol">' + seg.symbol + '</td>' +
                '<td class="number">' + seg.segment_num + '</td>' +
                '<td>' + formatTimestamp(seg.start_ts) + '</td>' +
                '<td>' + formatTimestamp(seg.end_ts) + '</td>' +
                '<td class="number">' + seg.bar_count + '</td>';
        }
        return '<tr class="data-row" onclick="toggleChart(' + idx + ')">' + cells + '</tr>' +
            '<tr class="chart-row" id="chart-row-' + idx + '">' +
            '<td colspan="' + colCount + '"><div class="chart-container" id="chart-container-' + idx + '"><div class="chart-loading">Loading chart...</div></div></td>' +
            '</tr>';
    }).join('');

    container.innerHTML = '<div class="segments-table-container"><table class="segments-table"><thead><tr>' + headerHtml + '</tr></thead><tbody>' + rowsHtml + '</tbody></table></div>';
}

// ── Init ──

document.addEventListener('DOMContentLoaded', function() {
    loadBarPeriods();
    loadAvailableIndicators();
    loadDsPresets();
    loadIndPresets();
    loadCondPresets();
    renderIndicatorList();
    updateButtonStates();
    loadIndicatorDefaults().then(function() {
        if (indicatorDefaultsData.chart_type) {
            chartType = indicatorDefaultsData.chart_type;
            var sel = document.getElementById('chart-type-select');
            if (sel) sel.value = chartType;
        }
        if (indicatorDefaultsData.overlap !== undefined) {
            chartOverlap = indicatorDefaultsData.overlap;
            var inp = document.getElementById('overlap-input');
            if (inp) inp.value = chartOverlap;
        }
    });
});
