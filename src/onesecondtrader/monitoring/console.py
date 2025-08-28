"""Console logging utilities for OneSecondTrader.

Simple console logging configuration for terminal output.
"""

import logging


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(threadName)s - %(message)s",
)

logger = logging.getLogger("onesecondtrader")
