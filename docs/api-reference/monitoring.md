# Monitoring

::: onesecondtrader.monitoring
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

??? quote "Source code in `monitoring.py`"

    ```python linenums="1"
    """Logging configuration for the OneSecondTrader package.
    
    This module sets up the default logging configuration and provides
    a logger instance for use throughout the package.
    """
    
    import logging
    
    
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
    )
    
    logger = logging.getLogger("onesecondtrader")
    
    ```
