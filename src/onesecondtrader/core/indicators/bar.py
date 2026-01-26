from onesecondtrader.core import events
from .base import Indicator


class Open(Indicator):
    @property
    def name(self) -> str:
        return "OPEN"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        return incoming_bar.open


class High(Indicator):
    @property
    def name(self) -> str:
        return "HIGH"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        return incoming_bar.high


class Low(Indicator):
    @property
    def name(self) -> str:
        return "LOW"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        return incoming_bar.low


class Close(Indicator):
    @property
    def name(self) -> str:
        return "CLOSE"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        return incoming_bar.close


class Volume(Indicator):
    @property
    def name(self) -> str:
        return "VOLUME"

    def _compute_indicator(self, incoming_bar: events.BarReceived) -> float:
        return float(incoming_bar.volume) if incoming_bar.volume is not None else 0.0
