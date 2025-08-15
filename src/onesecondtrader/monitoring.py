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
