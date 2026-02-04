"""
Command-line entry point for launching the dashboard server.

Starts the FastAPI application using uvicorn on localhost port 8001.
"""

import uvicorn


def main():
    """
    Launch the dashboard server.

    Runs the FastAPI application at http://127.0.0.1:8001 using uvicorn.
    """
    uvicorn.run(
        "onesecondtrader.dashboard.app:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
    )


if __name__ == "__main__":
    main()
