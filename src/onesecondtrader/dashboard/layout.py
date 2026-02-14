"""
HTML layout templates and page rendering utilities.

Provides the base page structure including sidebar navigation and main content area.
All dashboard pages are rendered through `render_page` which wraps content in the
standard layout with navigation and base styles.
"""

SIDEBAR_HTML = """
<aside class="sidebar">
    <div class="sidebar-header">
        <h1>OneSecondTrader</h1>
        <button class="sidebar-toggle" aria-label="Toggle sidebar">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
        </button>
    </div>
    <nav class="sidebar-nav">
        <a href="/explorer" class="{explorer_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            <span class="nav-label">Explorer</span>
        </a>
        <a href="/backtest" class="{backtest_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            <span class="nav-label">Backtest</span>
        </a>
        <a href="/splits" class="{splits_active}">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
            <span class="nav-label">Splits</span>
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
        explorer_active="active" if active == "explorer" else "",
        backtest_active="active" if active == "backtest" else "",
        splits_active="active" if active == "splits" else "",
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
    <link rel="stylesheet" href="/static/css/base.css">
</head>
<body>
    <script>if(sessionStorage.getItem('sidebarCollapsed')==='true')document.body.classList.add('collapsed')</script>
    {sidebar}
    <main class="main-content">
        <div class="container">
            {content}
        </div>
    </main>
    <script>
        (function() {{
            document.querySelector('.sidebar-toggle').addEventListener('click', function() {{
                document.body.classList.toggle('collapsed');
                sessionStorage.setItem('sidebarCollapsed', document.body.classList.contains('collapsed'));
            }});
            document.querySelectorAll('.sidebar-nav a').forEach(function(link) {{
                link.addEventListener('click', function() {{
                    sessionStorage.setItem('sidebarCollapsed', 'true');
                }});
            }});
        }})();
    </script>
</body>
</html>"""
