import abc
import threading
from onesecondtrader.messaging.eventbus import EventBus, system_event_bus
from onesecondtrader.core import models


class Strategy(abc.ABC):
    def __init__(self, name: str, event_bus: EventBus | None = None):
        self.name = name
        self.event_bus = event_bus if event_bus else system_event_bus
        self._lock = threading.Lock()
        self._active_symbols: set[str] = set()
        self._close_only_symbols: set[str] = set()
        self._close_open_positions_only: bool = False
        self._close_mode: models.StrategyShutdownMode | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name='{self.name}')"

    def request_close(
        self, mode: models.StrategyShutdownMode = models.StrategyShutdownMode.SOFT
    ) -> None:
        # Minimalist soft/hard close signalling; subclasses act on this
        self._close_open_positions_only = True
        self._close_mode = mode

    @abc.abstractmethod
    def is_flat(self) -> bool:
        raise NotImplementedError

    def add_symbols(self, symbols: list[str]) -> None:
        """
        Add symbols to the strategy. Thread-safe and idempotent.
        """
        clean = [s.strip() for s in symbols if s and s.strip()]
        with self._lock:
            self._active_symbols.update(clean)

    def remove_symbols(self, symbols: list[str]) -> None:
        """
        Remove symbols from the strategy. Thread-safe and idempotent.
        """
        clean = [s.strip() for s in symbols if s and s.strip()]
        with self._lock:
            for sym in clean:
                self._active_symbols.discard(sym)
