import abc
import pandas as pd
import threading

from pathlib import Path
from onesecondtrader.core import Events, Models, event_bus, logger


class DatafeedBase(abc.ABC):
    """
    Base class for all datafeeds.
    """

    def __init__(self) -> None:
        self._is_connected: bool = False
        self._watched_symbols: set[tuple[str, Models.RecordType]] = set()
        self._lock: threading.Lock = threading.Lock()

    @abc.abstractmethod
    def watch(self, symbols: list[tuple[str, Models.RecordType]]) -> bool:
        pass

    @abc.abstractmethod
    def unwatch(self, symbols: list[str]) -> None:
        pass


class SimulatedDatafeedCSV(DatafeedBase):
    """
    CSV-based simulated datafeed for backtesting.
    """

    csv_path: str | Path = ""
    artificial_delay: float = 0.0

    def __init__(self) -> None:
        super().__init__()
        self._stop_event = threading.Event()
        self._streaming_thread: threading.Thread | None = None
        self._data_iterator: pd.io.parsers.readers.TextFileReader | None = None
        self._connected_path: str | Path = ""

    def watch(self, symbols: list[tuple[str, Models.RecordType]]) -> bool:
        with self._lock:
            if not self._is_connected:
                try:
                    self._data_iterator = pd.read_csv(
                        Path(self.csv_path),
                        usecols=[
                            "ts_event",
                            "rtype",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                            "symbol",
                        ],
                        dtype={
                            "ts_event": int,
                            "rtype": int,
                            "open": int,
                            "high": int,
                            "low": int,
                            "close": int,
                            "volume": int,
                            "symbol": str,
                        },
                        chunksize=1,
                    )
                    self._is_connected = True
                    self._connected_path = self.csv_path
                    logger.info(
                        f"{self.__class__.__name__} connected to {self.csv_path}"
                    )
                except Exception as e:
                    logger.error(f"{self.__class__.__name__} failed to connect: {e}")
                    self._data_iterator = None
                    self._is_connected = False
                    return False
            elif self._connected_path != self.csv_path:
                logger.warning(
                    "csv_path changed while connected; unwatch all symbols first"
                )

            self._watched_symbols.update(symbols)
            formatted = ", ".join(f"{s} ({r.name})" for s, r in symbols)
            logger.info(f"{self.__class__.__name__} watching {formatted}")

            if not self._streaming_thread or not self._streaming_thread.is_alive():
                self._stop_event.clear()
                self._streaming_thread = threading.Thread(
                    target=self._stream, name="CSVDatafeedStreaming", daemon=False
                )
                self._streaming_thread.start()

        return True

    def unwatch(self, symbols: list[str]) -> None:
        thread_to_join = None
        with self._lock:
            symbols_set = set(symbols)
            self._watched_symbols.difference_update(
                {
                    (symbol, rtype)
                    for (symbol, rtype) in self._watched_symbols
                    if symbol in symbols_set
                }
            )
            logger.info(f"{self.__class__.__name__} unwatched {', '.join(symbols)}")
            if not self._watched_symbols:
                self._stop_event.set()
                thread_to_join = self._streaming_thread
                self._streaming_thread = None

        if thread_to_join and thread_to_join.is_alive():
            thread_to_join.join(timeout=5.0)
            if thread_to_join.is_alive():
                logger.warning("Streaming thread did not terminate within timeout")
            else:
                logger.info(f"{self.__class__.__name__} disconnected")

    def _stream(self) -> None:
        if self._data_iterator is None:
            logger.error("_stream called with no data iterator")
            return
        should_delay = self.artificial_delay > 0
        delay_time = self.artificial_delay
        while not self._stop_event.is_set():
            try:
                chunk = next(self._data_iterator)
                row = chunk.iloc[0]

                symbol = row["symbol"]
                record_type = Models.RecordType(row["rtype"])
                symbol_key = (symbol, record_type)

                with self._lock:
                    if symbol_key not in self._watched_symbols:
                        continue

                bar_event = Events.IncomingBar(
                    ts_event=pd.Timestamp(row["ts_event"], unit="ns", tz="UTC"),
                    symbol=symbol,
                    record_type=record_type,
                    open=row["open"] / 1e9,
                    high=row["high"] / 1e9,
                    low=row["low"] / 1e9,
                    close=row["close"] / 1e9,
                    volume=row["volume"],
                )

                event_bus.publish(bar_event)
                event_bus.wait_until_idle()

                if should_delay and self._stop_event.wait(delay_time):
                    break
            except StopIteration:
                logger.info("CSV datafeed reached end of file")
                break
            except Exception as e:
                logger.error(f"CSV datafeed error reading data: {e}")
                break

        with self._lock:
            self._data_iterator = None
            self._is_connected = False


simulated_datafeed_csv = SimulatedDatafeedCSV()
"""
Global instance of `SimulatedDatafeedCSV`.
"""
