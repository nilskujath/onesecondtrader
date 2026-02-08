"""
Page-specific HTML content generators.

Each function generates the HTML content for a specific dashboard page, which is then
wrapped in the standard layout by `render_page`.
"""

from .layout import render_page


def explorer_page() -> str:
    """
    Generate the new data explorer page.

    Returns:
        HTML string for the explorer page content.
    """
    content = """
    <link rel="stylesheet" href="/static/css/explorer.css">
    <div class="card">
        <h2>Data Source</h2>
        <div class="form-group">
            <label>Preset</label>
            <div class="preset-row">
                <select id="ds-preset-select" onchange="loadDsPreset()"></select>
                <input type="text" id="ds-preset-name" placeholder="New preset name..." oninput="updateButtonStates()">
                <button id="ds-preset-save-btn" class="btn btn-sm btn-secondary" onclick="saveDsPreset()">Save</button>
                <button id="ds-preset-delete-btn" class="btn btn-sm btn-danger" onclick="deleteDsPreset()">Delete</button>
            </div>
        </div>
        <div class="form-group">
            <label>Bar Period</label>
            <select id="bar-period" onchange="onBarPeriodChange()">
                <option value="">-- Select bar period --</option>
            </select>
        </div>
        <div class="form-group" id="symbols-section" style="display: none;">
            <label>Symbols</label>
            <div class="symbol-section">
                <div class="publisher-row">
                    <select id="publisher-name" onchange="onPublisherChange()">
                        <option value="">-- Select Publisher --</option>
                    </select>
                    <select id="publisher-dataset" onchange="onDatasetChange()">
                        <option value="">-- Select Dataset --</option>
                    </select>
                </div>
                <div id="symbol-selection" style="display: none;">
                    <div id="contract-type-section" style="display: none; margin-bottom: 8px;">
                        <label style="font-size: 13px; color: #8b949e;">Contract Type</label>
                        <div style="display: flex; gap: 12px; margin-top: 4px;">
                            <label style="font-size: 13px;"><input type="radio" name="contract-type" value="outrights" checked onchange="onContractTypeChange()"> Outrights</label>
                            <label style="font-size: 13px;"><input type="radio" name="contract-type" value="spreads" onchange="onContractTypeChange()"> Spreads</label>
                            <label style="font-size: 13px;"><input type="radio" name="contract-type" value="continuous" onchange="onContractTypeChange()"> Continuous</label>
                        </div>
                    </div>
                    <div class="search-row">
                        <input type="text" id="symbol-search" placeholder="Search symbols..." oninput="searchSymbols()">
                    </div>
                    <div id="search-results" class="search-results"></div>
                    <div id="selected-label" class="selected-label">Selected (0):</div>
                    <div id="selected-symbols" class="selected-symbols"></div>
                </div>
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
    </div>
    <div class="card">
        <h2>Indicators</h2>
        <div class="form-group">
            <label>Preset</label>
            <div class="preset-row">
                <select id="ind-preset-select" onchange="loadIndPreset()"></select>
                <input type="text" id="ind-preset-name" placeholder="New preset name..." oninput="updateButtonStates()">
                <button id="ind-preset-save-btn" class="btn btn-sm btn-secondary" onclick="saveIndPreset()">Save</button>
                <button id="ind-preset-delete-btn" class="btn btn-sm btn-danger" onclick="deleteIndPreset()">Delete</button>
            </div>
        </div>
        <div class="indicator-builder">
            <div class="indicator-add-row">
                <select id="indicator-class" onchange="onIndicatorClassChange()">
                    <option value="">-- Select Indicator --</option>
                </select>
                <button class="btn-add" onclick="addIndicator()">+ Add</button>
            </div>
            <div id="indicator-params" class="indicator-params"></div>
        </div>
        <div id="indicator-list"></div>
        <div class="form-group" style="margin-top: 16px;">
            <button id="calculate-btn" class="btn" onclick="onCalculate()" disabled>Calculate Indicators</button>
            <div id="explore-progress" class="progress-bar">
                <div id="explore-progress-fill" class="progress-fill" style="width: 0%"></div>
            </div>
        </div>
    </div>
    <div class="card" id="chart-settings-card" style="display:none;">
        <h2>Chart Settings</h2>
        <div id="indicator-chart-table"></div>
    </div>
    <div class="card" id="chart-display-card" style="display:none;">
        <h2>Chart Display</h2>
        <div class="chart-mode-tabs">
            <button class="mode-tab active" onclick="setChartMode('bars')">By Bars</button>
            <button class="mode-tab" onclick="setChartMode('time')">By Time</button>
            <button class="mode-tab" onclick="setChartMode('condition')">By Condition</button>
        </div>
        <div class="form-group" id="cond-preset-row" style="display:none;">
            <label>Preset</label>
            <div class="preset-row">
                <select id="cond-preset-select" onchange="loadCondPreset()"></select>
                <input type="text" id="cond-preset-name" placeholder="New preset name..." oninput="updateButtonStates()">
                <button id="cond-preset-save-btn" class="btn btn-sm btn-secondary" onclick="saveCondPreset()">Save</button>
                <button id="cond-preset-delete-btn" class="btn btn-sm btn-danger" onclick="deleteCondPreset()">Delete</button>
            </div>
        </div>
        <div id="chart-mode-controls"></div>
        <div id="charts-content">
            <div class="empty-content"><p>Configure chart display settings above</p></div>
        </div>
    </div>
    <script src="/static/js/explorer.js"></script>
    """
    return render_page("Explorer", content, "explorer")


def backtest_page() -> str:
    """
    Generate the backtest page with 4 vertically stacked boxes.

    Box 1: Backtest config (strategy/dataset selection + runs list)
    Box 2: Run selection dropdown + performance metrics placeholder
    Box 3: Per-symbol PnL Summary + Trade Journey charts
    Box 4: Trades table + chart rendering + chart settings

    Returns:
        HTML string for the backtest page content.
    """
    content = """
    <link rel="stylesheet" href="/static/css/backtest.css">

    <!-- Box 1: Backtest Config -->
    <div id="box-config" class="box">
        <div class="backtest-layout">
            <div class="backtest-left">
                <div class="card">
                    <h2>Settings</h2>
                    <div class="form-group">
                        <label>Strategy</label>
                        <select id="strategy" onchange="loadStrategyParams()"></select>
                        <div class="section-header">Parameters</div>
                        <div id="strategy-params" class="params-container"></div>
                    </div>
                    <div class="form-group">
                        <label>Preset</label>
                        <div class="preset-row">
                            <select id="preset-select" onchange="loadPreset()"></select>
                            <input type="text" id="preset-name" placeholder="New preset name..." oninput="updateButtonStates()">
                            <button id="preset-save-btn" class="btn btn-sm btn-secondary" onclick="savePreset()">Save</button>
                            <button id="preset-delete-btn" class="btn btn-sm btn-danger" onclick="deletePreset()">Delete</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Bar Period</label>
                        <select id="bar-period" onchange="onBarPeriodChange()">
                            <option value="">-- Select bar period --</option>
                        </select>
                    </div>
                    <div class="form-group" id="symbols-section" style="display: none;">
                        <label>Symbols</label>
                        <div class="symbol-section">
                            <div class="publisher-row">
                                <select id="publisher-name" onchange="onPublisherChange()">
                                    <option value="">-- Select Publisher --</option>
                                </select>
                                <select id="publisher-dataset" onchange="onDatasetChange()">
                                    <option value="">-- Select Dataset --</option>
                                </select>
                            </div>
                            <div id="symbol-selection" style="display: none;">
                                <div id="contract-type-section" style="display: none; margin-bottom: 8px;">
                                    <label style="font-size: 13px; color: #8b949e;">Contract Type</label>
                                    <div style="display: flex; gap: 12px; margin-top: 4px;">
                                        <label style="font-size: 13px;"><input type="radio" name="contract-type" value="outrights" checked onchange="onContractTypeChange()"> Outrights</label>
                                        <label style="font-size: 13px;"><input type="radio" name="contract-type" value="spreads" onchange="onContractTypeChange()"> Spreads</label>
                                        <label style="font-size: 13px;"><input type="radio" name="contract-type" value="continuous" onchange="onContractTypeChange()"> Continuous</label>
                                    </div>
                                </div>
                                <div class="search-row">
                                    <input type="text" id="symbol-search" placeholder="Search symbols..." oninput="searchSymbols()">
                                </div>
                                <div id="search-results" class="search-results"></div>
                                <div id="selected-label" class="selected-label">Selected (0):</div>
                                <div id="selected-symbols" class="selected-symbols"></div>
                            </div>
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
                        <button id="run-btn" class="btn" onclick="runBacktest()" disabled>Run Backtest</button>
                    </div>
                </div>
            </div>
            <div class="backtest-right">
                <div class="card">
                    <h2>Runs</h2>
                    <div id="runs-list" class="runs-list"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Box 2: Run Selection + Metrics Placeholder -->
    <div id="box-run-metrics" class="box">
        <div class="card">
            <h2>Analysis</h2>
            <div class="settings-row">
                <div class="settings-group">
                    <label>Run:</label>
                    <select id="run-select" onchange="onRunSelect()">
                        <option value="">Select a completed run...</option>
                    </select>
                </div>
            </div>
            <div id="metrics-placeholder"></div>
        </div>
    </div>

    <!-- Box 3: Per-symbol Performance Charts -->
    <div id="box-symbol-perf" class="box">
        <div class="card">
            <h2>Symbol Performance</h2>
            <div class="settings-row">
                <div class="settings-group">
                    <label>Symbol:</label>
                    <div class="symbol-input-wrapper">
                        <input type="text" id="perf-symbol-input" placeholder="Select a run first..." disabled oninput="onPerfSymbolInput()" onkeydown="onPerfSymbolKeydown(event)" onfocus="onPerfSymbolInput()" autocomplete="off">
                        <div id="perf-symbol-suggestions" class="symbol-suggestions"></div>
                    </div>
                </div>
            </div>
            <div class="charts-row" id="perf-charts-row">
                <div class="chart-card"><h3>PnL Summary</h3><div class="chart-content" id="pnl-container"><div class="empty-message">Select a run and symbol</div></div></div>
                <div class="chart-card"><h3>Trade Journey</h3><div class="chart-content" id="journey-container"><div class="empty-message">Select a run and symbol</div></div></div>
            </div>
        </div>
    </div>

    <!-- Box 4: Trades Table + Chart Settings -->
    <div id="box-trades" class="box">
        <div class="card">
            <h2>Trades</h2>
            <div id="trades-settings-panel"></div>
            <div id="trades-ind-settings-container"></div>
            <div id="trades-content">
                <div class="empty-content"><p>Select a run to view trades</p></div>
            </div>
        </div>
    </div>

    <script src="/static/js/backtest.js"></script>
    """
    return render_page("Backtest", content, "backtest")
