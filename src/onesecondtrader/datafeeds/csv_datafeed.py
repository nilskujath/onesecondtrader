"""
This module provides a CSV-based simulated live datafeed.
"""

import os
import pandas as pd
import threading
import time
from pathlib import Path
from dotenv import load_dotenv
from onesecondtrader.messaging import events, eventbus
from onesecondtrader.core import models
from onesecondtrader.monitoring import console
from onesecondtrader.datafeeds import base_datafeed
from pandas.io.parsers.readers import TextFileReader


class CSVDatafeed(base_datafeed.BaseDatafeed):
    """
    CSV-based simulated live datafeed.

    Only one instance of any BaseDatafeed subclass can exist at a time.
    """

    _instance = None

    def __init__(
        self,
        event_bus: eventbus.EventBus,
        csv_path: str | Path | None = None,
        streaming_delay: float | None = None,
    ):
        """
        Initialize CSV datafeed.

        Args:
            event_bus: Event bus used to publish market data events.
            csv_path: Optional path to CSV file. Overrides CSV_PATH env var.
            streaming_delay: Optional delay in seconds between processing rows.
                Overrides CSV_STREAMING_DELAY env var.

        Attributes:
            self.csv_path (Path | None): Path to CSV file.
            self.data_iterator (TextFileReader | None): Iterator for reading CSV.
            self._watched_symbols (set[tuple[str, models.RecordType]]): Set of
                symbols and record types currently being watched.
            self._streaming_thread (threading.Thread | None): Background thread
                for streaming data.
            self._symbols_lock (threading.Lock): Lock to protect _watched_symbols
                from concurrent access.
            self._streaming_delay (float): Delay in seconds between processing
                CSV rows (from CSV_STREAMING_DELAY env var, set in connect()).
            self._init_csv_path (str | Path | None): CSV path provided during
                initialization.
            self._init_streaming_delay (float | None): Streaming delay provided
                during initialization.
        """
        if CSVDatafeed._instance is not None:
            console.logger.warning(
                f"Only one BaseDatafeed instance allowed. "
                f"Current: {type(CSVDatafeed._instance).__name__}. "
                f"Initialization failed."
            )
            return

        super().__init__(event_bus)
        CSVDatafeed._instance = self

        self.csv_path: Path | None = None
        self.data_iterator: TextFileReader | None = None
        self._watched_symbols: set[tuple[str, models.RecordType]] = set()
        self._stop_event = threading.Event()
        self._streaming_thread: threading.Thread | None = None
        self._symbols_lock: threading.Lock = threading.Lock()
        self._streaming_delay: float = 0.0

        self._init_csv_path: str | Path | None = csv_path
        self._init_streaming_delay: float | None = streaming_delay

    def connect(self):
        """
        Connect to CSV file specified in .env file (CSV_PATH variable) and
        create data iterator.
        """
        load_dotenv()

        if self._init_csv_path is not None:
            csv_path_str = str(self._init_csv_path)
            console.logger.info(f"Using CSV path from initialization: {csv_path_str}")
        else:
            csv_path_str = os.getenv("CSV_PATH")
            if not csv_path_str:
                console.logger.error(
                    "CSV_PATH not found in environment variables and not "
                    "provided in __init__. Either set CSV_PATH in .env file "
                    "or pass csv_path to CSVDatafeed()"
                )
                return False

        if self._init_streaming_delay is not None:
            self._streaming_delay = self._init_streaming_delay
            if self._streaming_delay < 0:
                console.logger.warning(
                    f"Streaming delay cannot be negative "
                    f"({self._streaming_delay}), using default 0.0"
                )
                self._streaming_delay = 0.0
            else:
                console.logger.info(
                    f"CSV streaming delay set from initialization: "
                    f"{self._streaming_delay} seconds"
                )
        else:
            streaming_delay_str = os.getenv("CSV_STREAMING_DELAY", "0.0")
            try:
                self._streaming_delay = float(streaming_delay_str)
                if self._streaming_delay < 0:
                    console.logger.warning(
                        f"CSV_STREAMING_DELAY cannot be negative "
                        f"({self._streaming_delay}), using default 0.0"
                    )
                    self._streaming_delay = 0.0
                else:
                    console.logger.info(
                        f"CSV streaming delay set from environment: "
                        f"{self._streaming_delay} seconds"
                    )
            except ValueError:
                console.logger.error(
                    f"Invalid CSV_STREAMING_DELAY value "
                    f"'{streaming_delay_str}', must be a number. "
                    f"Using default 0.0"
                )
                self._streaming_delay = 0.0

        self.csv_path = Path(csv_path_str)

        try:
            self.data_iterator = pd.read_csv(
                self.csv_path,
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
                iterator=True,
                chunksize=1,
            )
            console.logger.info(f"CSV datafeed connected to: {self.csv_path}")
            self._stop_event.clear()
            return True

        except Exception as e:
            console.logger.error(f"Failed to connect to CSV file {self.csv_path}: {e}")
            return False

    def watch(self, symbols):
        """
        Start streaming data for specified symbols.
        Can be called multiple times to add more symbols.

        Args:
            symbols (list[tuple[str, models.RecordType]]): List of symbols to
                watch with their respective record types.
        """
        if not self.data_iterator:
            console.logger.error("Not connected. Call connect() first.")
            return

        with self._symbols_lock:
            new_symbols = set(symbols) - self._watched_symbols
            already_watched = set(symbols) & self._watched_symbols

            self._watched_symbols.update(new_symbols)

            if new_symbols:
                console.logger.info(f"Added new symbols: {new_symbols}")
            if already_watched:
                console.logger.info(f"Already watching: {already_watched}")
            console.logger.info(
                f"Currently watching: {len(self._watched_symbols)} symbols"
            )

        if self._streaming_thread is None or not self._streaming_thread.is_alive():
            self._streaming_thread = threading.Thread(
                target=self._stream, name="CSVDatafeedStreaming", daemon=True
            )
            self._streaming_thread.start()
            console.logger.info("Started CSV streaming thread")

    def _stream(self):
        """Internal method that runs in background thread to stream CSV data."""
        console.logger.info("CSV streaming thread started")

        should_delay = self._streaming_delay > 0
        delay_time = self._streaming_delay

        while not self._stop_event.is_set():
            try:
                chunk = next(self.data_iterator)
                row = chunk.iloc[0]

                symbol = row["symbol"]
                rtype = row["rtype"]

                with self._symbols_lock:
                    symbol_key = (symbol, models.RecordType(rtype))
                    if symbol_key not in self._watched_symbols:
                        continue

                bar_event = events.Market.IncomingBar(
                    ts_event=pd.Timestamp(row["ts_event"], unit="ns", tz="UTC"),
                    symbol=symbol,
                    bar=models.Bar(
                        open=row["open"] / 1e9,
                        high=row["high"] / 1e9,
                        low=row["low"] / 1e9,
                        close=row["close"] / 1e9,
                        volume=int(row["volume"]),
                    ),
                )

                self.event_bus.publish(bar_event)

                if should_delay:
                    time.sleep(delay_time)

            except StopIteration:
                console.logger.info("CSV datafeed reached end of file")
                break
            except ValueError as e:
                console.logger.warning(f"Invalid rtype {row['rtype']} in CSV data: {e}")
                continue
            except Exception as e:
                console.logger.error(f"CSV datafeed error reading data: {e}")
                break

        console.logger.info("CSV streaming thread stopped")

    def unwatch(self, symbols):
        """
        Stop watching specific symbols.

        Args:
            symbols (list[tuple[str, models.RecordType]]): List of symbols to
                stop watching.
        """
        with self._symbols_lock:
            for symbol in symbols:
                self._watched_symbols.discard(symbol)

            console.logger.info(f"Stopped watching symbols: {symbols}")
            console.logger.info(f"Still watching: {self._watched_symbols}")

    def disconnect(self):
        """
        Disconnect from CSV datafeed.
        """
        self._stop_event.set()

        if self._streaming_thread and self._streaming_thread.is_alive():
            console.logger.info("Waiting for streaming thread to stop...")
            self._streaming_thread.join(timeout=5.0)
            if self._streaming_thread.is_alive():
                console.logger.warning("Streaming thread did not stop within timeout")

        with self._symbols_lock:
            self._watched_symbols.clear()

        if self.data_iterator is not None:
            try:
                self.data_iterator.close()
                console.logger.info("CSV iterator closed successfully")
            except Exception as e:
                console.logger.warning(f"Error closing CSV iterator: {e}")
            finally:
                self.data_iterator = None

        self.csv_path = None
        self._streaming_thread = None

        CSVDatafeed._instance = None
