# Console

::: onesecondtrader.monitoring.console
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

??? quote "Source code in `console.py`"

    ```python linenums="1"
    """Console logging utilities for OneSecondTrader.
    
    Simple console logging configuration for terminal output.
    """
    
    import logging
    
    
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    )
    
    logger = logging.getLogger("onesecondtrader")
    
    ```
