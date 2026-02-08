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
    timePeriod: 'day'
};

let chartType = 'c_bars';
let chartOverlap = 100;

let conditionalSettings = {
    leftField: '',
    operator: '<=',
    rightField: '',
    rightValue: 0,
    contextBars: 50,
    gapTolerance: 0
};
let conditionalSegments = [];
let filteredConditionalSegments = [];

let indicatorNames = [];
let chartSettingsData = {};
let _settingsVersion = 0;

const CONDITION_BAR_FIELDS = ['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME'];
const CONDITION_OPERATORS = ['<=', '>=', '<', '>', '==', '!='];

const VALID_STYLES = ['line', 'histogram', 'dots', 'dash1', 'dash2', 'dash3', 'background1', 'background2'];
const VALID_COLORS = ['black', 'red', 'blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'teal'];
const VALID_WIDTHS = ['thin', 'normal', 'thick', 'extra_thick'];
const DEFAULT_COLOR_CYCLE = ['blue', 'red', 'green', 'orange', 'purple', 'cyan', 'magenta', 'teal', 'black', 'yellow'];

const CHART_TYPE_OPTIONS = [
    {value: 'candlestick', label: 'Candlestick'},
    {value: 'oc_bars', label: 'OC Bars'},
    {value: 'c_bars', label: 'C Bars'},
    {value: 'bars', label: 'Bars'}
];

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
    const savedCond = localStorage.getItem('conditionalSettings');
    if (savedCond) {
        try {
            conditionalSettings = {...conditionalSettings, ...JSON.parse(savedCond)};
        } catch (e) {}
    }
}

function saveSettings() {
    localStorage.setItem('chartSettings', JSON.stringify(settings));
    localStorage.setItem('conditionalSettings', JSON.stringify(conditionalSettings));
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

async function selectRun(runId) {
    selectedRunId = runId;
    const url = new URL(window.location);
    url.searchParams.set('run_id', runId);
    window.history.replaceState({}, '', url);
    const select = document.getElementById('run-select');
    if (select && select.value !== runId) {
        select.value = runId;
    }
    await loadIndicatorSettings(runId);
    renderConditionalSettings();
    loadData(runId);
}

function renderSettings() {
    const container = document.getElementById('settings-panel');
    if (!container) return;
    const timePeriodOpts = TIME_PERIOD_OPTIONS[barPeriod] || TIME_PERIOD_OPTIONS['DAY'];
    if (settings.mode === 'time' && !timePeriodOpts.some(o => o.value === settings.timePeriod)) {
        settings.timePeriod = timePeriodOpts[0].value;
    }
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
    let subControl = '';
    if (settings.mode === 'bars') {
        subControl = `<div class="settings-group">
            <label>Bars per chart:</label>
            <input type="number" id="bars-per-chart" value="${settings.barsPerChart}" min="10" max="5000" onchange="onBarsPerChartChange(this.value)">
        </div>`;
    } else if (settings.mode === 'time') {
        subControl = `<div class="settings-group">
            <label>Period:</label>
            <select id="time-period" onchange="onTimePeriodChange(this.value)">${periodOptions}</select>
        </div>`;
    }
    container.innerHTML = `
        <div class="settings-box">
            <div class="settings-row">
                <div class="settings-group">
                    <label>Run:</label>
                    <select id="run-select" onchange="onRunChange()">${runOptions}</select>
                </div>
                <div class="settings-group">
                    <label>Symbol:</label>
                    <input type="text" id="symbol-filter" placeholder="Filter symbols..." value="${symbolFilterValue}" oninput="filterData()">
                </div>
            </div>
        </div>
        <div class="settings-box">
            <div class="settings-row">
                <div class="settings-group">
                    <label>Split by:</label>
                    <select id="split-mode" onchange="onModeChange(this.value)">
                        <option value="bars" ${settings.mode === 'bars' ? 'selected' : ''}>By Bars</option>
                        <option value="time" ${settings.mode === 'time' ? 'selected' : ''}>By Time</option>
                        <option value="trades" ${settings.mode === 'trades' ? 'selected' : ''}>By Trades</option>
                        <option value="conditional" ${settings.mode === 'conditional' ? 'selected' : ''}>Conditional</option>
                    </select>
                </div>
                ${subControl}
            </div>
        </div>
    `;
}

function onModeChange(mode) {
    settings.mode = mode;
    saveSettings();
    renderSettings();
    renderConditionalSettings();
    renderIndicatorSettings();
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
    chartOverlap = parseInt(value) || 0;
    saveIndicatorSettings();
    if (selectedRunId) loadData(selectedRunId);
}

function onChartTypeChange(value) {
    chartType = value;
    saveIndicatorSettings();
    if (selectedRunId) loadData(selectedRunId);
}

async function loadData(runId) {
    const container = document.getElementById('charts-content');
    container.innerHTML = '<div class="empty-content"><p>Loading...</p></div>';
    if (settings.mode === 'conditional') {
        loadConditionalData();
        return;
    }
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
            overlap: chartOverlap,
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
    if (settings.mode === 'conditional') {
        if (!query) {
            filteredConditionalSegments = [...conditionalSegments];
        } else {
            const terms = query.split(/[,\\s]+/).filter(t => t.length > 0);
            filteredConditionalSegments = conditionalSegments.filter(seg =>
                terms.some(term => seg.symbol.toLowerCase().includes(term))
            );
        }
    } else if (settings.mode === 'trades') {
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
    if (settings.mode === 'conditional') {
        filteredConditionalSegments.sort((a, b) => {
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
        renderConditionalTable();
    } else if (settings.mode === 'trades') {
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
    if (settings.mode === 'conditional') {
        const seg = filteredConditionalSegments[idx];
        cacheKey = `${selectedRunId}_cond_${seg.symbol}_${seg.start_ts}_${seg.end_ts}_${seg.condition_start_ts}_${seg.condition_end_ts}_${chartType}_v${_settingsVersion}`;
        if (chartCache[cacheKey]) {
            container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
            return;
        }
        container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
        url = `/api/runs/${selectedRunId}/segment-chart.png?symbol=${encodeURIComponent(seg.symbol)}&start_ns=${seg.start_ts}&end_ns=${seg.end_ts}&highlight_start_ns=${seg.condition_start_ts}&highlight_end_ns=${seg.condition_end_ts}&chart_type=${chartType}`;
    } else if (settings.mode === 'trades') {
        const rt = filteredRoundtrips[idx];
        cacheKey = `${selectedRunId}_trade_${rt.symbol}_${rt.entry_ts}_${rt.exit_ts}_${chartType}_v${_settingsVersion}`;
        if (chartCache[cacheKey]) {
            container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
            return;
        }
        container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
        url = `/api/runs/${selectedRunId}/chart.png?symbol=${encodeURIComponent(rt.symbol)}&start_ns=${rt.entry_ts}&end_ns=${rt.exit_ts}&direction=${rt.direction}&pnl=${rt.pnl_after_commission}&chart_type=${chartType}`;
    } else {
        const seg = filteredSegments[idx];
        cacheKey = `${selectedRunId}_${seg.symbol}_${seg.start_ts}_${seg.end_ts}_${chartType}_v${_settingsVersion}`;
        if (chartCache[cacheKey]) {
            container.innerHTML = `<img src="${chartCache[cacheKey]}" alt="Chart">`;
            return;
        }
        container.innerHTML = '<div class="chart-loading">Loading chart...</div>';
        url = `/api/runs/${selectedRunId}/segment-chart.png?symbol=${encodeURIComponent(seg.symbol)}&start_ns=${seg.start_ts}&end_ns=${seg.end_ts}&chart_type=${chartType}`;
        if (seg.period_start_ns && seg.period_end_ns) {
            url += `&period_start_ns=${seg.period_start_ns}&period_end_ns=${seg.period_end_ns}`;
        }
    }
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

function getDefaultPanel(name, assignedPanels) {
    const upper = name.toUpperCase();
    // Overlay indicators (panel 0)
    if (/^SMA_/.test(upper) || /^BB_UPPER_/.test(upper) || /^BB_LOWER_/.test(upper) ||
        /^PSAR_/.test(upper) || /PERIOD HIGH/.test(upper) || /PERIOD LOW/.test(upper)) {
        return 0;
    }
    // Grouped: ADX, PLUS_DI, MINUS_DI share a panel
    const adxGroup = ['ADX_', 'PLUS_DI_', 'MINUS_DI_'];
    if (adxGroup.some(prefix => upper.startsWith(prefix))) {
        for (const [existingName, panel] of Object.entries(assignedPanels)) {
            if (adxGroup.some(prefix => existingName.toUpperCase().startsWith(prefix))) {
                return panel;
            }
        }
    }
    // Individual oscillators each get their own panel
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
        chartType = chartSettingsData.chart_type || 'c_bars';
        chartOverlap = chartSettingsData.overlap != null ? chartSettingsData.overlap : 100;
        const assignedPanels = {};
        indicatorNames.forEach((name, idx) => {
            if (!chartSettingsData.indicators[name]) {
                const panel = getDefaultPanel(name, assignedPanels);
                chartSettingsData.indicators[name] = {
                    panel: panel,
                    below_price: true,
                    style: 'line',
                    color: 'black',
                    width: 'normal',
                    visible: true
                };
                assignedPanels[name] = panel;
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
        renderConditionalSettings();
    } catch (e) {
        console.error('Failed to load indicator settings', e);
    }
}

async function saveIndicatorSettings() {
    if (!selectedRunId) return;
    try {
        await fetch(`/api/runs/${selectedRunId}/chart-settings`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({...chartSettingsData, chart_type: chartType, overlap: chartOverlap})
        });
        _settingsVersion++;
        Object.keys(chartCache).forEach(k => delete chartCache[k]);
        document.querySelectorAll('.chart-row.expanded').forEach(row => {
            const idx = parseInt(row.id.replace('chart-row-', ''));
            row.classList.remove('expanded');
            toggleChart(idx);
        });
    } catch (e) {
        console.error('Failed to save indicator settings', e);
    }
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
    saveIndicatorSettings();
    if (field === 'panel') renderIndicatorSettings();
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
    const container = document.getElementById('ind-settings-container');
    if (!container) return;
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
    const overlapDisabled = (settings.mode === 'trades' || settings.mode === 'conditional') ? 'disabled' : '';
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
                    <div class="settings-group">
                        <label>Overlap:</label>
                        <input type="number" value="${chartOverlap}" min="0" max="1000" ${overlapDisabled} onchange="onOverlapChange(this.value)">
                    </div>
                </div>
                ${indTable}
            </div>
        </div>
    `;
}

function renderConditionalSettings() {
    const container = document.getElementById('conditional-settings-container');
    if (!container) return;
    if (settings.mode !== 'conditional' || !selectedRunId) {
        container.innerHTML = '';
        return;
    }
    // Auto-default left field if empty
    if (!conditionalSettings.leftField) {
        if (indicatorNames.length > 0) {
            conditionalSettings.leftField = indicatorNames[0];
        } else if (CONDITION_BAR_FIELDS.length > 0) {
            conditionalSettings.leftField = CONDITION_BAR_FIELDS[0];
        }
    }
    const barFieldOpts = CONDITION_BAR_FIELDS.map(f =>
        `<option value="${f}" ${conditionalSettings.leftField === f ? 'selected' : ''}>${f}</option>`
    ).join('');
    const indOpts = indicatorNames.map(n =>
        `<option value="${n}" ${conditionalSettings.leftField === n ? 'selected' : ''}>${n}</option>`
    ).join('');
    const leftOptions = `<optgroup label="Bar Fields">${barFieldOpts}</optgroup><optgroup label="Indicators">${indOpts}</optgroup>`;

    const rightBarFieldOpts = CONDITION_BAR_FIELDS.map(f =>
        `<option value="${f}" ${conditionalSettings.rightField === f ? 'selected' : ''}>${f}</option>`
    ).join('');
    const rightIndOpts = indicatorNames.map(n =>
        `<option value="${n}" ${conditionalSettings.rightField === n ? 'selected' : ''}>${n}</option>`
    ).join('');
    const rightOptions = `<option value="" ${!conditionalSettings.rightField ? 'selected' : ''}>(Value)</option><optgroup label="Bar Fields">${rightBarFieldOpts}</optgroup><optgroup label="Indicators">${rightIndOpts}</optgroup>`;

    const opOptions = CONDITION_OPERATORS.map(op =>
        `<option value="${op}" ${conditionalSettings.operator === op ? 'selected' : ''}>${op}</option>`
    ).join('');

    const valueInputStyle = conditionalSettings.rightField ? 'display:none' : '';

    container.innerHTML = `
        <div class="conditional-settings-box">
            <div class="settings-row">
                <div class="settings-group">
                    <label>Left:</label>
                    <select onchange="onConditionalChange('leftField', this.value)">${leftOptions}</select>
                </div>
                <div class="settings-group">
                    <label>Operator:</label>
                    <select onchange="onConditionalChange('operator', this.value)">${opOptions}</select>
                </div>
                <div class="settings-group">
                    <label>Right:</label>
                    <select onchange="onConditionalChange('rightField', this.value)">${rightOptions}</select>
                </div>
                <div class="settings-group" id="cond-value-group" style="${valueInputStyle}">
                    <label>Value:</label>
                    <input type="number" step="any" value="${conditionalSettings.rightValue}" onchange="onConditionalChange('rightValue', parseFloat(this.value))">
                </div>
            </div>
            <div class="settings-row">
                <div class="settings-group">
                    <label>Context bars:</label>
                    <input type="number" value="${conditionalSettings.contextBars}" min="0" max="500" onchange="onConditionalChange('contextBars', parseInt(this.value))">
                </div>
                <div class="settings-group">
                    <label>Gap tolerance:</label>
                    <input type="number" value="${conditionalSettings.gapTolerance}" min="0" max="100" onchange="onConditionalChange('gapTolerance', parseInt(this.value))">
                </div>
            </div>
        </div>
    `;
}

function onConditionalChange(field, value) {
    conditionalSettings[field] = value;
    saveSettings();
    if (field === 'rightField') {
        renderConditionalSettings();
    }
    loadConditionalData();
}

async function loadConditionalData() {
    if (!selectedRunId) return;
    if (!conditionalSettings.leftField) return;
    if (!conditionalSettings.rightField && (conditionalSettings.rightValue === null || conditionalSettings.rightValue === undefined)) return;
    const container = document.getElementById('charts-content');
    container.innerHTML = '<div class="empty-content"><p>Loading...</p></div>';
    const params = new URLSearchParams({
        left_field: conditionalSettings.leftField,
        operator: conditionalSettings.operator,
        context_bars: String(conditionalSettings.contextBars),
        gap_tolerance: String(conditionalSettings.gapTolerance)
    });
    if (conditionalSettings.rightField) {
        params.set('right_field', conditionalSettings.rightField);
    } else {
        params.set('right_value', String(conditionalSettings.rightValue));
    }
    try {
        const res = await fetch(`/api/runs/${selectedRunId}/conditional-segments?${params}`);
        const data = await res.json();
        conditionalSegments = data.segments || [];
        sortColumn = 'symbol';
        sortAsc = true;
        filterData();
    } catch (e) {
        container.innerHTML = '<div class="empty-content"><p>Error loading conditional segments</p></div>';
    }
}

function renderConditionalTable() {
    const container = document.getElementById('charts-content');
    if (conditionalSegments.length === 0) {
        container.innerHTML = '<div class="empty-table"><p>No conditional segments found</p></div>';
        return;
    }
    const columns = [
        {key: 'symbol', label: 'Symbol'},
        {key: 'segment_num', label: 'Region #'},
        {key: 'condition_start_ts', label: 'Condition Start'},
        {key: 'condition_end_ts', label: 'Condition End'},
        {key: 'condition_bar_count', label: 'Condition Bars'},
        {key: 'bar_count', label: 'Total Bars'},
    ];
    const headerHtml = columns.map(c => {
        const isSorted = sortColumn === c.key;
        const arrow = isSorted ? (sortAsc ? '▲' : '▼') : '▲';
        return `<th class="${isSorted ? 'sorted' : ''}" onclick="sortBy('${c.key}')">${c.label}<span class="sort-icon">${arrow}</span></th>`;
    }).join('');
    const rowsHtml = filteredConditionalSegments.map((seg, idx) => {
        return `<tr class="data-row" onclick="toggleChart(${idx})">
            <td class="symbol">${seg.symbol}</td>
            <td class="number">${seg.segment_num}</td>
            <td>${formatTimestamp(seg.condition_start_ts)}</td>
            <td>${formatTimestamp(seg.condition_end_ts)}</td>
            <td class="number">${seg.condition_bar_count}</td>
            <td class="number">${seg.bar_count}</td>
        </tr>
        <tr class="chart-row" id="chart-row-${idx}">
            <td colspan="6">
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

document.addEventListener('DOMContentLoaded', () => {
    loadRuns();
});
