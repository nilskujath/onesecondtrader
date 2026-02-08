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
        <div id="chart-mode-controls"></div>
        <div class="form-group" id="cond-preset-row" style="display:none;">
            <label>Preset</label>
            <div class="preset-row">
                <select id="cond-preset-select" onchange="loadCondPreset()"></select>
                <input type="text" id="cond-preset-name" placeholder="New preset name..." oninput="updateButtonStates()">
                <button id="cond-preset-save-btn" class="btn btn-sm btn-secondary" onclick="saveCondPreset()">Save</button>
                <button id="cond-preset-delete-btn" class="btn btn-sm btn-danger" onclick="deleteCondPreset()">Delete</button>
            </div>
        </div>
        <div id="charts-content">
            <div class="empty-content"><p>Configure chart display settings above</p></div>
        </div>
    </div>
    <script src="/static/js/explorer.js"></script>
    """
    return render_page("Explorer", content, "explorer")


def backtest_page() -> str:
    """
    Generate the backtest configuration page.

    The page provides a form for configuring and running backtests with:

    - Strategy selection and parameter configuration
    - Bar period selection (Second, Minute, Hour, Day)
    - Publisher and dataset selection for data source filtering
    - Symbol search and selection with preset management
    - Date range selection constrained by available data
    - Run history display with selection and deletion

    Returns:
        HTML string for the backtest page content.
    """
    content = """
    <link rel="stylesheet" href="/static/css/backtest.css">
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
    <script src="/static/js/backtest.js"></script>
    """
    return render_page("Backtest", content, "backtest")


def performance_page() -> str:
    """
    Generate the performance analysis page.

    Returns:
        HTML string for the performance page content.
    """
    content = """
    <link rel="stylesheet" href="/static/css/performance.css">
    <div class="performance-layout">
        <div class="settings-card" id="settings-panel"></div>
        <div class="charts-row" id="charts-row"></div>
    </div>
    <script src="/static/js/performance.js"></script>
    """
    return render_page("Performance", content, "performance")


def chart_page() -> str:
    """
    Generate the chart viewing page.

    Returns:
        HTML string for the chart page content.
    """
    content = """
    <link rel="stylesheet" href="/static/css/chart.css">
    <div class="chart-layout">
        <div class="card">
            <h2>Charts</h2>
            <div id="settings-panel" class="settings-panel"></div>
            <div id="conditional-settings-container"></div>
            <div id="ind-settings-container"></div>
            <div id="charts-content">
                <div class="empty-content"><p>Select a run to view charts</p></div>
            </div>
        </div>
    </div>
    <script src="/static/js/chart.js"></script>
    """
    return render_page("Chart", content, "chart")
