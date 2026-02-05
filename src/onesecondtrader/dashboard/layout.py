"""
HTML layout templates and page rendering utilities.

Provides the base page structure including sidebar navigation and main content area.
All dashboard pages are rendered through `render_page` which wraps content in the
standard layout with navigation and base styles.
"""

from .styles import BASE_CSS

SIDEBAR_HTML = """
<aside class="sidebar">
    <div class="sidebar-header">
        <h1>OneSecondTrader</h1>
    </div>
    <nav class="sidebar-nav">
        <a href="/backtest" class="{backtest_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
            Backtest
        </a>
        <a href="/performance" class="{performance_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            Performance
        </a>
    </nav>
</aside>
"""


def render_sidebar(active: str = "") -> str:
    """
    Render the sidebar navigation HTML.

    Parameters:
        active:
            Name of the currently active page for highlighting.

    Returns:
        HTML string for the sidebar.
    """
    return SIDEBAR_HTML.format(
        backtest_active="active" if active == "backtest" else "",
        performance_active="active" if active == "performance" else "",
    )


def render_page(title: str, content: str, active: str = "") -> str:
    """
    Render a complete HTML page with layout.

    Parameters:
        title:
            Page title displayed in the browser tab.
        content:
            HTML content to render in the main content area.
        active:
            Name of the currently active page for sidebar highlighting.

    Returns:
        Complete HTML document string.
    """
    sidebar = render_sidebar(active)
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title} - OneSecondTrader</title>
    <style>{BASE_CSS}</style>
</head>
<body>
    {sidebar}
    <main class="main-content">
        <div class="container">
            {content}
        </div>
    </main>
</body>
</html>"""
