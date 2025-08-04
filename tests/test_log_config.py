from src.onesecondtrader.log_config import logger


def test_log_config(caplog):
    with caplog.at_level("INFO", logger="onesecondtrader"):
        logger.info("Test log message")

    assert any("Test log message" in message for message in caplog.messages)
    assert caplog.records[0].name == "onesecondtrader"
