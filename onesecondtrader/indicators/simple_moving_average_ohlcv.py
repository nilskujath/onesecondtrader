from onesecondtrader.indicators import Indicator
from onesecondtrader.ontology.event_messages import IncomingBarEventMessage, OHLCV
from onesecondtrader.backbone import logger
import sys
import numpy as np
import collections


class SimpleMovingAverage(Indicator):
    def __init__(self, period: int, applied_on: str):
        _valid_fields = OHLCV._fields
        if applied_on not in _valid_fields:
            logger.error(
                f"Invalid 'applied_on' value: {applied_on}. Must be one of {_valid_fields}."
            )
            sys.exit(1)
        self.period = period
        self.applied_on = applied_on
        self.values = collections.deque(maxlen=self.period)
        self._current_value = np.nan

    @property
    def name(self) -> str:
        return f"SMA_ohlcv_{self.period}_{self.applied_on}"

    def update(self, bar: IncomingBarEventMessage):
        value = getattr(bar.ohlcv, self.applied_on)
        self.values.append(value)
        if len(self.values) == self.period:
            self._current_value = sum(self.values) / self.period

    def value(self):
        return self._current_value
