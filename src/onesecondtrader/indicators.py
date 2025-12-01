"""
OneSecondTrader's library of pre-built indicators.
"""

import abc
import enum
import numpy as np
import threading

from collections import deque
from onesecondtrader.core import Events


class BaseIndicator(abc.ABC):
    """
    Base class for indicators. Subclasses must set the `name` property and implement
    the `_compute_indicator()` method. See `SimpleMovingAverage` for an example.
    """

    def __init__(self, max_history: int = 100) -> None:
        self._lock = threading.Lock()
        self._history: deque[float] = deque(maxlen=max(1, int(max_history)))

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    def update(self, incoming_bar: Events.IncomingBar) -> None:
        _latest_value: float = self._compute_indicator(incoming_bar)
        with self._lock:
            self._history.append(_latest_value)

    @abc.abstractmethod
    def _compute_indicator(self, incoming_bar: Events.IncomingBar) -> float:
        pass

    @property
    def latest(self) -> float:
        with self._lock:
            return self._history[-1] if self._history else np.nan

    @property
    def history(self) -> deque[float]:
        return self._history


class InputSource(enum.Enum):
    """
    Enum of supported input sources for indicators. Indicators with a `input_source`
    parameter can be configured to use one of these sources for their calculations.
    """

    OPEN = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()
    CLOSE = enum.auto()
    VOLUME = enum.auto()


class SimpleMovingAverage(BaseIndicator):
    """
    Simple Moving Average (SMA) indicator. Can be configured to use different input
    sources (see `InputSource` enum, default is `InputSource.CLOSE`).
    """

    def __init__(
        self,
        period: int = 200,
        max_history: int = 100,
        input_source: InputSource = InputSource.CLOSE,
    ) -> None:
        super().__init__(max_history=max_history)
        self.period: int = max(1, int(period))
        self.input_source: InputSource = input_source
        self._window: deque[float] = deque(maxlen=self.period)

    @property
    def name(self) -> str:
        return f"SMA_{self.period}_{self.input_source.name}"

    def _compute_indicator(self, incoming_bar: Events.IncomingBar) -> float:
        value: float = self._extract_input(incoming_bar)
        self._window.append(value)
        if len(self._window) < self.period:
            return np.nan
        return sum(self._window) / self.period

    def _extract_input(self, incoming_bar: Events.IncomingBar) -> float:
        match self.input_source:
            case InputSource.OPEN:
                return incoming_bar.open
            case InputSource.HIGH:
                return incoming_bar.high
            case InputSource.LOW:
                return incoming_bar.low
            case InputSource.CLOSE:
                return incoming_bar.close
            case InputSource.VOLUME:
                return (
                    float(incoming_bar.volume)
                    if incoming_bar.volume is not None
                    else np.nan
                )
            case _:
                return incoming_bar.close
