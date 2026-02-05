# Getting Started 


This guide will teach you how to develop indicators, design strategies, and run backtests using OneSecondTrader. 


## Installation


=== "Pip"
    
    **Step 0**

    Make sure that pip is installed. If not, install it by following the [:material-link-variant:Official Documentation](https://pip.pypa.io/en/stable/installation/).

    **Step 1**

    Navigate to the folder you want to use or create a new one. Then run the following comand inside this folder to create a virtual environment:

    ```bash 
    python3 -m venv .venv
    source .venv/bin/activate
    ```

    **Step 2**

    Install OneSecondTrader by running the following command:

    ```bash
    pip install onesecondtrader
    ```



=== "Poetry"

    **Step 0**

    Make sure that poetry is installed. If not, install it by following the [:material-link-variant:Official Documentation](https://python-poetry.org/docs/#installation).

    **Step 1**

    Navigate to the folder you want to use or create a new one. Then run the following comand inside this folder:

    ```bash
    poetry init
    ```

    **Step 2**

    Add `package-mode = false` to your `pyproject.toml` file. It should look similar to this:
 
    ``` toml linenums="1" hl_lines="8"
    [project]
    name = "stratdev"
    version = "0.1.0"
    description = ""
    authors = [
        {name = "...",email = "..."}
    ]
    package-mode = false

    [tool.poetry.dependencies]
    python = ">=3.11,<4.0"

    [build-system]
    requires = ["poetry-core>=2.0.0,<3.0.0"]
    build-backend = "poetry.core.masonry.api"
    ```

    **Step 3**

    Install OneSecondTrader by running the following command:

    ```bash
    poetry add onesecondtrader
    ```

    **Step 4**

    Activate the virtual environment by running the following command:

    ```bash
    poetry env activate
    ```

## Historical Market Data

Running backtests requires historical market data.
For serious work, we recommend using a data provider like Databento.

=== "Databento"

    **Step 0**

    Assuming you already have a Databento account, download the data you want to use for backtesting in `.dbn` format and `.zst` compression (note that it does not matter how you choose to split the files).
    For more information, see the [:material-link-variant:Databento Documentation](https://databento.com/docs).
    You should receive a .zip file that contains a `.dbn` file(s) and some metadata `.json` files (importantly, `symbology.json`).


    **Step 1**

    Start an interactive Python session (`poetry run python` if you use poetry, `python` or `python3` if you are using venv) and run the following commands to create an empty securities master database:

    ```python
    from onesecondtrader import secmaster
    from pathlib import Path
    secmaster.create_secmaster_db(Path("secmaster.db"))
    ```

    **Step 2**

    Still in an interactive Python session, run the following commands to ingest the data into the database:

    ```python
    secmaster.ingest_databento_zip(Path("path/to/your/download.zip"), Path("./secmaster.db"))
    ```

    This may take a while. After it's done, you can exit the interactive Python session (`exit()`).

    
=== "Other Providers"

    !!! warning "Coming Soon"

        Other providers will be supported soon. If you want to contribute, please open an issue or submit a pull request.


## Exploring the Dashboard

Now it is time to explore the dashboard.
It will allow you to run backtests and analyze performance metrics.
The OneSecondTrader package provides a simple SMA crossover strategy that you will backtest to acquaint yourself with the dashboard.
Afterward, you will learn how to create your own indicators and strategies and backtest them via the dashboard.
