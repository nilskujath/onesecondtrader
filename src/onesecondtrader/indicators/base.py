from __future__ import annotations

import abc
import collections
import importlib.util
import threading
from pathlib import Path

import numpy as np

from onesecondtrader import events, models


_indicator_registry: dict[str, type[IndicatorBase]] = {}


def get_registered_indicators() -> dict[str, type[IndicatorBase]]:
    """
    Return all registered indicator classes.

    Returns:
        Dictionary mapping indicator class names to their class objects.
    """
    return dict(_indicator_registry)


def discover_indicators(directory: str | Path = "indicators") -> list[str]:
    """
    Import all Python files from a directory to register indicators.

    Any class inheriting from IndicatorBase in the imported files will be
    automatically registered via __init_subclass__.

    Parameters:
        directory:
            Path to the directory containing indicator files.
            Defaults to "indicators" relative to the current working directory.

    Returns:
        List of successfully imported module names.
    """
    import sys
    import types

    path = Path(directory)
    if not path.is_dir():
        return []

    if "indicators" not in sys.modules:
        sys.modules["indicators"] = types.ModuleType("indicators")

    imported = []
    for file in path.glob("*.py"):
        if file.name.startswith("_"):
            continue

        module_name = f"indicators.{file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            imported.append(file.stem)
        except Exception:
            del sys.modules[module_name]

    return imported


class IndicatorBase(abc.ABC):
    """
    Base class for scalar technical indicators with per-symbol history.

    The class provides a thread-safe mechanism for storing and retrieving indicator values computed from incoming market bars, keyed by symbol.
    It does not manage input windows or rolling computation state.

    Subclasses define a stable indicator identifier via the `name` property and implement `_compute_indicator`, which computes a single scalar value per incoming bar.
    Indicators with multiple conceptual outputs must be implemented as multiple single-output indicators (e.g. Bollinger Bands must be implemented via three separate indicators `BBUpper`, `BBMiddle`, and `BBLower`).

    The update mechanism is thread-safe.
    Indicator computation is performed outside the internal lock.
    Subclasses that maintain internal state are responsible for ensuring its thread safety and must not access `_history_data`.

    Indicator values are stored per symbol in bounded FIFO buffers.
    Missing data and out-of-bounds access yield `numpy.nan`.

    The `plot_at` attribute is an opaque identifier forwarded to the charting backend and has no intrinsic meaning within the indicator subsystem.
    The `plot_as` attribute specifies the visual style used to render the indicator.

    Subclasses are automatically registered for discovery when defined.
    """

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.__name__.startswith("_"):
            _indicator_registry[cls.__name__] = cls

    def __init__(
        self,
        max_history: int = 100,
        plot_at: int = 99,
        plot_as: models.PlotStyle = models.PlotStyle.LINE,
    ) -> None:
        """
        Parameters:
            max_history:
                Maximum number of indicator values retained per symbol.
                Cannot be less than 1.
            plot_at:
                Opaque plotting identifier forwarded to the charting backend.
            plot_as:
                Visual style used to render the indicator.
        """
        self._lock = threading.Lock()
        self._max_history = max(1, int(max_history))
        self._history_data: dict[str, collections.deque[float]] = {}
        self._plot_at = plot_at
        self._plot_as = plot_as

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """
        Canonical indicator name.

        Returns:
            Stable identifier used for charting and downstream integration.
        """
        pass

    @abc.abstractmethod
    def _compute_indicator(self, incoming_bar: events.market.BarReceived) -> float:
        """
        Compute the indicator value for a single market bar.

        This method is executed outside the internal lock.
        Implementations must not access `_history_data` and must ensure thread safety of any internal computation state.

        Parameters:
            incoming_bar:
                Market bar used as input for indicator computation.

        Returns:
            Computed indicator value.
        """
        pass

    def update(self, incoming_bar: events.market.BarReceived) -> None:
        """
        Update the indicator with a new market bar.

        The computed value is appended to the per-symbol history buffer.

        Parameters:
            incoming_bar:
                Market bar triggering the update.
        """
        symbol = incoming_bar.symbol

        value = self._compute_indicator(incoming_bar)

        with self._lock:
            if symbol not in self._history_data:
                self._history_data[symbol] = collections.deque(maxlen=self._max_history)

            self._history_data[symbol].append(value)

    def latest(self, symbol: str) -> float:
        """
        Return the most recent indicator value for a symbol.

        Parameters:
            symbol:
                Symbol identifier.

        Returns:
            Most recent value, or `numpy.nan` if unavailable.
        """
        return self[symbol, -1]

    def __getitem__(self, key: tuple[str, int]) -> float:
        """
        Retrieve an indicator value by symbol and index.

        Indexing follows standard Python sequence semantics.
        Negative indices refer to positions relative to the most recent value.

        Parameters:
            key:
                `(symbol, index)` pair specifying the symbol and history offset.

        Returns:
            Indicator value at the specified position, or `numpy.nan` if unavailable.
        """
        symbol, index = key

        with self._lock:
            history = self._history_data.get(symbol)

            if history is None:
                return np.nan

            try:
                return history[index]
            except IndexError:
                return np.nan

    @property
    def plot_at(self) -> int:
        """
        Plotting identifier.

        Returns:
            Opaque identifier consumed by the charting backend.
        """
        return self._plot_at

    @property
    def plot_as(self) -> models.PlotStyle:
        """
        Plotting style.

        Returns:
            Visual style used to render the indicator.
        """
        return self._plot_as
