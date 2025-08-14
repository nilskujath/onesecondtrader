import importlib
import logging

import src.onesecondtrader.log_config as log_config


def test_logger_captures_info_with_expected_name(caplog):
    caplog.set_level(logging.INFO, logger="onesecondtrader")
    log_config.logger.info("probe")
    assert caplog.messages == ["probe"]
    assert caplog.records[0].name == "onesecondtrader"


def test_log_config_is_idempotent_on_reload():
    before = len(log_config.logger.handlers)
    importlib.reload(log_config)
    after = len(log_config.logger.handlers)
    assert after == before
