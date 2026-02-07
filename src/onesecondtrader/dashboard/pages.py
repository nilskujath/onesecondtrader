"""
Page-specific HTML content generators.

Each function generates the HTML content for a specific dashboard page, which is then
wrapped in the standard layout by `render_page`.
"""

from .layout import render_page
from .styles import (
    BACKTEST_CSS,
    BACKTEST_JS,
    CHART_CSS,
    CHART_JS,
    PERFORMANCE_CSS,
    PERFORMANCE_JS,
)


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
    content = f"""
    <style>{BACKTEST_CSS}</style>
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
    <script>{BACKTEST_JS}</script>
    """
    return render_page("Backtest", content, "backtest")


def performance_page() -> str:
    """
    Generate the performance analysis page.

    Returns:
        HTML string for the performance page content.
    """
    content = f"""
    <style>{PERFORMANCE_CSS}</style>
    <div class="performance-layout">
        <div class="settings-card" id="settings-panel"></div>
        <div class="charts-row" id="charts-row"></div>
    </div>
    <script>{PERFORMANCE_JS}</script>
    """
    return render_page("Performance", content, "performance")


def chart_page() -> str:
    """
    Generate the chart viewing page.

    Returns:
        HTML string for the chart page content.
    """
    content = f"""
    <style>{CHART_CSS}</style>
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
    <script>{CHART_JS}</script>
    """
    return render_page("Chart", content, "chart")
