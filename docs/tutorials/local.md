# Running the Dashboard Locally 

This guide shows how to install OneSecondTrader and run the dashboard on your local machine.

## Prerequisites
* Python 3.11 or higher
* A `secmaster.db` file containing your market data

## Virtual Environment Setup

Create and activate a virtual environment:

=== "macOS / Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

=== "Windows (PowerShell)"

    ```powershell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

=== "Windows (CMD)"

    ```cmd
    python -m venv .venv
    .venv\Scripts\activate.bat
    ```

## Installation


```bash
pip install onesecondtrader
```

## Configuration

Set the path to your security master database:

=== "macOS / Linux"

    ```bash
    export SECMASTER_DB_PATH=/path/to/your/secmaster.db
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:SECMASTER_DB_PATH = "C:\path\to\your\secmaster.db"
    ```

=== "Windows (CMD)"

    ```cmd
    set SECMASTER_DB_PATH=C:\path\to\your\secmaster.db
    ```

Optionally, set a custom path for the runs database (defaults to `runs.db` in the current directory):

=== "macOS / Linux"

    ```bash
    export RUNS_DB_PATH=/path/to/runs.db
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:RUNS_DB_PATH = "C:\path\to\runs.db"
    ```

=== "Windows (CMD)"

    ```cmd
    set RUNS_DB_PATH=C:\path\to\runs.db
    ```


## Running the Dashboard

Start the dashboard server:

```bash
onesecondtrader
```

Open your browser and navigate to [http://127.0.0.1:8001](http://127.0.0.1:8001).
