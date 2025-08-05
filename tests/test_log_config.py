"""
Test suite for logging configuration.

This module validates the logging configuration for the trading infrastructure,
ensuring that log messages are properly formatted, routed, and captured during
testing scenarios.

Test Coverage:
- Logger instance creation and configuration
- Log message capture and validation
- Logger name assignment and hierarchy
- Integration with pytest's caplog fixture

Testing Philosophy:
The logging system is critical for debugging and monitoring trading operations.
These tests ensure that the logging configuration works correctly and that
log messages can be captured and validated during testing.
"""

from src.onesecondtrader.log_config import logger


def test_log_config(caplog):
    """
    Test basic logging configuration and message capture.

    Validates that the logger is properly configured with the correct name
    and that log messages can be captured and verified during testing.

    This test ensures that:
    - Logger accepts and processes INFO level messages
    - Messages are properly captured by pytest's caplog fixture
    - Logger name is correctly set to "onesecondtrader"
    """
    with caplog.at_level("INFO", logger="onesecondtrader"):
        logger.info("Test log message")

    assert any("Test log message" in message for message in caplog.messages)
    assert caplog.records[0].name == "onesecondtrader"
