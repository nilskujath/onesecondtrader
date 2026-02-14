"""
Page-specific HTML content generators.

Each function returns a complete HTML document for a specific dashboard page,
using React 18 with in-browser Babel for JSX compilation.
"""


def explorer_page() -> str:
    """
    Generate the React-based data explorer page.

    Returns:
        Complete HTML document with React CDN and JSX component.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <title>Explorer - OneSecondTrader</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { height: 100%; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" src="/static/js/explorer.jsx"></script>
</body>
</html>"""


def backtest_page() -> str:
    """
    Generate the React-based backtest page.

    Returns:
        Complete HTML document with React CDN and JSX component.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <title>Backtest - OneSecondTrader</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { height: 100%; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" src="/static/js/backtest.jsx"></script>
</body>
</html>"""


def splits_page() -> str:
    """
    Generate the React-based train/dev/test splits page.

    Returns:
        Complete HTML document with React CDN and JSX component.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <title>Splits - OneSecondTrader</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { height: 100%; }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel" src="/static/js/splits.jsx"></script>
</body>
</html>"""
