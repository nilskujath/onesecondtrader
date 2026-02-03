from __future__ import annotations

import json
import pathlib
import sqlite3
import time

from onesecondtrader import events, messaging


BATCH_SIZE = 1000


class RunRecorder(messaging.Subscriber):
    """
    Subscriber that records all trading system events to a SQLite runs database.

    The recorder subscribes to market data events, order requests, broker responses,
    fills, and expirations, inserting them into the appropriate tables as defined
    in the runs schema.

    Events are buffered and inserted in batches for performance. The buffer is
    flushed on shutdown via `_cleanup`.
    """

    def __init__(
        self,
        event_bus: messaging.EventBus,
        db_path: pathlib.Path,
        run_id: str,
        name: str,
        config: dict | None = None,
        metadata: dict | None = None,
    ) -> None:
        """
        Initialize the recorder and register a new run in the database.

        The database is created if it does not exist. A new row is inserted into the `runs`
        table with status `running` and the current timestamp as `ts_start`.

        Parameters:
            event_bus:
                Event bus used for subscribing to system events.
            db_path:
                Filesystem path to the SQLite runs database.
            run_id:
                Unique identifier for this run.
            name:
                Human-readable name for this run.
            config:
                Optional configuration dictionary to store as JSON.
            metadata:
                Optional metadata dictionary to store as JSON.
        """
        self._db_path = db_path
        self._run_id = run_id
        self._name = name
        self._config = config
        self._metadata = metadata

        self._conn = self._init_db()
        self._buffers: dict[str, list[tuple]] = {
            "bars": [],
            "bars_processed": [],
            "order_submissions": [],
            "order_cancellations": [],
            "order_modifications": [],
            "orders_accepted": [],
            "orders_rejected": [],
            "cancellations_accepted": [],
            "cancellations_rejected": [],
            "modifications_accepted": [],
            "modifications_rejected": [],
            "fills": [],
            "expirations": [],
        }

        self._register_run()

        super().__init__(event_bus)
        self._subscribe(
            events.market.BarReceived,
            events.market.BarProcessed,
            events.requests.OrderSubmissionRequest,
            events.requests.OrderCancellationRequest,
            events.requests.OrderModificationRequest,
            events.responses.OrderAccepted,
            events.responses.OrderRejected,
            events.responses.CancellationAccepted,
            events.responses.CancellationRejected,
            events.responses.ModificationAccepted,
            events.responses.ModificationRejected,
            events.orders.FillEvent,
            events.orders.OrderExpired,
        )

    def _init_db(self) -> sqlite3.Connection:
        """
        Initialize the SQLite database connection.

        Creates the database file and parent directories if they do not exist.
        Applies the runs schema if the database is newly created.

        Returns:
            Open database connection configured with WAL journal mode.
        """
        schema_path = pathlib.Path(__file__).parent / "runs_schema.sql"
        db_exists = self._db_path.is_file()

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")

        if not db_exists:
            conn.executescript(schema_path.read_text())

        return conn

    def _register_run(self) -> None:
        """
        Insert a new run record into the database.

        The run is created with status 'running' and the current timestamp as start time.
        """
        self._conn.execute(
            """
            INSERT INTO runs (run_id, name, ts_start, status, config, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                self._name,
                time.time_ns(),
                "running",
                json.dumps(self._config) if self._config else None,
                json.dumps(self._metadata) if self._metadata else None,
            ),
        )
        self._conn.commit()

    def update_run_status(
        self,
        status: str,
        ts_end: int | None = None,
    ) -> None:
        """
        Update the status and end timestamp of the current run.

        Parameters:
            status:
                New status value (e.g., 'completed', 'failed', 'cancelled').
            ts_end:
                End timestamp in nanoseconds since Unix epoch. Defaults to current time.
        """
        if ts_end is None:
            ts_end = time.time_ns()
        self._conn.execute(
            "UPDATE runs SET status = ?, ts_end = ? WHERE run_id = ?",
            (status, ts_end, self._run_id),
        )
        self._conn.commit()

    def _on_event(self, event: events.EventBase) -> None:
        """
        Dispatch an incoming event to the appropriate buffer method.

        Parameters:
            event:
                Event received from the event bus.
        """
        match event:
            case events.market.BarProcessed() as matched:
                self._buffer_bar_processed(matched)
            case events.market.BarReceived() as matched:
                self._buffer_bar_received(matched)
            case events.requests.OrderSubmissionRequest() as matched:
                self._buffer_order_submission(matched)
            case events.requests.OrderCancellationRequest() as matched:
                self._buffer_order_cancellation(matched)
            case events.requests.OrderModificationRequest() as matched:
                self._buffer_order_modification(matched)
            case events.responses.OrderAccepted() as matched:
                self._buffer_order_accepted(matched)
            case events.responses.OrderRejected() as matched:
                self._buffer_order_rejected(matched)
            case events.responses.CancellationAccepted() as matched:
                self._buffer_cancellation_accepted(matched)
            case events.responses.CancellationRejected() as matched:
                self._buffer_cancellation_rejected(matched)
            case events.responses.ModificationAccepted() as matched:
                self._buffer_modification_accepted(matched)
            case events.responses.ModificationRejected() as matched:
                self._buffer_modification_rejected(matched)
            case events.orders.FillEvent() as matched:
                self._buffer_fill(matched)
            case events.orders.OrderExpired() as matched:
                self._buffer_expiration(matched)

    def _on_exception(self, exc: Exception) -> None:
        """
        Handle an exception raised during event processing.

        Parameters:
            exc:
                Exception that was raised.
        """
        pass

    def _cleanup(self) -> None:
        """
        Flush all buffered records and close the database connection.

        Called automatically during subscriber shutdown.
        """
        self._flush_all()
        self._conn.close()

    def _flush_all(self) -> None:
        """
        Flush all event buffers to the database.
        """
        self._flush_bars()
        self._flush_bars_processed()
        self._flush_order_submissions()
        self._flush_order_cancellations()
        self._flush_order_modifications()
        self._flush_orders_accepted()
        self._flush_orders_rejected()
        self._flush_cancellations_accepted()
        self._flush_cancellations_rejected()
        self._flush_modifications_accepted()
        self._flush_modifications_rejected()
        self._flush_fills()
        self._flush_expirations()

    def _buffer_bar_received(self, event: events.market.BarReceived) -> None:
        """
        Buffer a bar received event for batch insertion.

        Parameters:
            event:
                Bar received event to buffer.
        """
        self._buffers["bars"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.symbol,
                event.bar_period.name,
                event.open,
                event.high,
                event.low,
                event.close,
                event.volume,
            )
        )
        if len(self._buffers["bars"]) >= BATCH_SIZE:
            self._flush_bars()

    def _buffer_bar_processed(self, event: events.market.BarProcessed) -> None:
        """
        Buffer a bar processed event for batch insertion.

        Parameters:
            event:
                Bar processed event to buffer.
        """
        self._buffers["bars_processed"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.symbol,
                event.bar_period.name,
                event.open,
                event.high,
                event.low,
                event.close,
                event.volume,
                json.dumps(event.indicators),
            )
        )
        if len(self._buffers["bars_processed"]) >= BATCH_SIZE:
            self._flush_bars_processed()

    def _buffer_order_submission(
        self, event: events.requests.OrderSubmissionRequest
    ) -> None:
        """
        Buffer an order submission request for batch insertion.

        Parameters:
            event:
                Order submission request to buffer.
        """
        self._buffers["order_submissions"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                str(event.system_order_id),
                event.symbol,
                event.order_type.name,
                event.side.name,
                event.quantity,
                event.limit_price,
                event.stop_price,
                event.action.name if event.action else None,
                event.signal,
            )
        )
        if len(self._buffers["order_submissions"]) >= BATCH_SIZE:
            self._flush_order_submissions()

    def _buffer_order_cancellation(
        self, event: events.requests.OrderCancellationRequest
    ) -> None:
        """
        Buffer an order cancellation request for batch insertion.

        Parameters:
            event:
                Order cancellation request to buffer.
        """
        self._buffers["order_cancellations"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                str(event.system_order_id),
                event.symbol,
            )
        )
        if len(self._buffers["order_cancellations"]) >= BATCH_SIZE:
            self._flush_order_cancellations()

    def _buffer_order_modification(
        self, event: events.requests.OrderModificationRequest
    ) -> None:
        """
        Buffer an order modification request for batch insertion.

        Parameters:
            event:
                Order modification request to buffer.
        """
        self._buffers["order_modifications"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                str(event.system_order_id),
                event.symbol,
                event.quantity,
                event.limit_price,
                event.stop_price,
            )
        )
        if len(self._buffers["order_modifications"]) >= BATCH_SIZE:
            self._flush_order_modifications()

    def _buffer_order_accepted(self, event: events.responses.OrderAccepted) -> None:
        """
        Buffer an order accepted response for batch insertion.

        Parameters:
            event:
                Order accepted response to buffer.
        """
        self._buffers["orders_accepted"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.broker_order_id,
            )
        )
        if len(self._buffers["orders_accepted"]) >= BATCH_SIZE:
            self._flush_orders_accepted()

    def _buffer_order_rejected(self, event: events.responses.OrderRejected) -> None:
        """
        Buffer an order rejected response for batch insertion.

        Parameters:
            event:
                Order rejected response to buffer.
        """
        self._buffers["orders_rejected"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.rejection_reason.name,
                event.rejection_message,
            )
        )
        if len(self._buffers["orders_rejected"]) >= BATCH_SIZE:
            self._flush_orders_rejected()

    def _buffer_cancellation_accepted(
        self, event: events.responses.CancellationAccepted
    ) -> None:
        """
        Buffer a cancellation accepted response for batch insertion.

        Parameters:
            event:
                Cancellation accepted response to buffer.
        """
        self._buffers["cancellations_accepted"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.broker_order_id,
            )
        )
        if len(self._buffers["cancellations_accepted"]) >= BATCH_SIZE:
            self._flush_cancellations_accepted()

    def _buffer_cancellation_rejected(
        self, event: events.responses.CancellationRejected
    ) -> None:
        """
        Buffer a cancellation rejected response for batch insertion.

        Parameters:
            event:
                Cancellation rejected response to buffer.
        """
        self._buffers["cancellations_rejected"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.rejection_reason.name,
                event.rejection_message,
            )
        )
        if len(self._buffers["cancellations_rejected"]) >= BATCH_SIZE:
            self._flush_cancellations_rejected()

    def _buffer_modification_accepted(
        self, event: events.responses.ModificationAccepted
    ) -> None:
        """
        Buffer a modification accepted response for batch insertion.

        Parameters:
            event:
                Modification accepted response to buffer.
        """
        self._buffers["modifications_accepted"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.broker_order_id,
            )
        )
        if len(self._buffers["modifications_accepted"]) >= BATCH_SIZE:
            self._flush_modifications_accepted()

    def _buffer_modification_rejected(
        self, event: events.responses.ModificationRejected
    ) -> None:
        """
        Buffer a modification rejected response for batch insertion.

        Parameters:
            event:
                Modification rejected response to buffer.
        """
        self._buffers["modifications_rejected"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.rejection_reason.name,
                event.rejection_message,
            )
        )
        if len(self._buffers["modifications_rejected"]) >= BATCH_SIZE:
            self._flush_modifications_rejected()

    def _buffer_fill(self, event: events.orders.FillEvent) -> None:
        """
        Buffer a fill event for batch insertion.

        Parameters:
            event:
                Fill event to buffer.
        """
        self._buffers["fills"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.broker_order_id,
                event.symbol,
                str(event.fill_id),
                event.broker_fill_id,
                event.side.name,
                event.quantity_filled,
                event.fill_price,
                event.commission,
                event.exchange,
            )
        )
        if len(self._buffers["fills"]) >= BATCH_SIZE:
            self._flush_fills()

    def _buffer_expiration(self, event: events.orders.OrderExpired) -> None:
        """
        Buffer an order expiration event for batch insertion.

        Parameters:
            event:
                Order expiration event to buffer.
        """
        self._buffers["expirations"].append(
            (
                self._run_id,
                event.ts_event_ns,
                event.ts_created_ns,
                event.ts_broker_ns,
                str(event.associated_order_id),
                event.broker_order_id,
                event.symbol,
            )
        )
        if len(self._buffers["expirations"]) >= BATCH_SIZE:
            self._flush_expirations()

    def _flush_bars(self) -> None:
        """
        Insert buffered bar received records into the database.
        """
        if not self._buffers["bars"]:
            return
        self._conn.executemany(
            """
            INSERT INTO bars (run_id, ts_event_ns, ts_created_ns, symbol, bar_period, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["bars"],
        )
        self._conn.commit()
        self._buffers["bars"].clear()

    def _flush_bars_processed(self) -> None:
        """
        Insert buffered bar processed records into the database.
        """
        if not self._buffers["bars_processed"]:
            return
        self._conn.executemany(
            """
            INSERT INTO bars_processed (run_id, ts_event_ns, ts_created_ns, symbol, bar_period, open, high, low, close, volume, indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["bars_processed"],
        )
        self._conn.commit()
        self._buffers["bars_processed"].clear()

    def _flush_order_submissions(self) -> None:
        """
        Insert buffered order submission records into the database.
        """
        if not self._buffers["order_submissions"]:
            return
        self._conn.executemany(
            """
            INSERT INTO order_submissions (run_id, ts_event_ns, ts_created_ns, system_order_id, symbol, order_type, side, quantity, limit_price, stop_price, action, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["order_submissions"],
        )
        self._conn.commit()
        self._buffers["order_submissions"].clear()

    def _flush_order_cancellations(self) -> None:
        """
        Insert buffered order cancellation records into the database.
        """
        if not self._buffers["order_cancellations"]:
            return
        self._conn.executemany(
            """
            INSERT INTO order_cancellations (run_id, ts_event_ns, ts_created_ns, system_order_id, symbol)
            VALUES (?, ?, ?, ?, ?)
            """,
            self._buffers["order_cancellations"],
        )
        self._conn.commit()
        self._buffers["order_cancellations"].clear()

    def _flush_order_modifications(self) -> None:
        """
        Insert buffered order modification records into the database.
        """
        if not self._buffers["order_modifications"]:
            return
        self._conn.executemany(
            """
            INSERT INTO order_modifications (run_id, ts_event_ns, ts_created_ns, system_order_id, symbol, quantity, limit_price, stop_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["order_modifications"],
        )
        self._conn.commit()
        self._buffers["order_modifications"].clear()

    def _flush_orders_accepted(self) -> None:
        """
        Insert buffered order accepted records into the database.
        """
        if not self._buffers["orders_accepted"]:
            return
        self._conn.executemany(
            """
            INSERT INTO orders_accepted (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, broker_order_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            self._buffers["orders_accepted"],
        )
        self._conn.commit()
        self._buffers["orders_accepted"].clear()

    def _flush_orders_rejected(self) -> None:
        """
        Insert buffered order rejected records into the database.
        """
        if not self._buffers["orders_rejected"]:
            return
        self._conn.executemany(
            """
            INSERT INTO orders_rejected (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, rejection_reason, rejection_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["orders_rejected"],
        )
        self._conn.commit()
        self._buffers["orders_rejected"].clear()

    def _flush_cancellations_accepted(self) -> None:
        """
        Insert buffered cancellation accepted records into the database.
        """
        if not self._buffers["cancellations_accepted"]:
            return
        self._conn.executemany(
            """
            INSERT INTO cancellations_accepted (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, broker_order_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            self._buffers["cancellations_accepted"],
        )
        self._conn.commit()
        self._buffers["cancellations_accepted"].clear()

    def _flush_cancellations_rejected(self) -> None:
        """
        Insert buffered cancellation rejected records into the database.
        """
        if not self._buffers["cancellations_rejected"]:
            return
        self._conn.executemany(
            """
            INSERT INTO cancellations_rejected (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, rejection_reason, rejection_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["cancellations_rejected"],
        )
        self._conn.commit()
        self._buffers["cancellations_rejected"].clear()

    def _flush_modifications_accepted(self) -> None:
        """
        Insert buffered modification accepted records into the database.
        """
        if not self._buffers["modifications_accepted"]:
            return
        self._conn.executemany(
            """
            INSERT INTO modifications_accepted (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, broker_order_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            self._buffers["modifications_accepted"],
        )
        self._conn.commit()
        self._buffers["modifications_accepted"].clear()

    def _flush_modifications_rejected(self) -> None:
        """
        Insert buffered modification rejected records into the database.
        """
        if not self._buffers["modifications_rejected"]:
            return
        self._conn.executemany(
            """
            INSERT INTO modifications_rejected (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, rejection_reason, rejection_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["modifications_rejected"],
        )
        self._conn.commit()
        self._buffers["modifications_rejected"].clear()

    def _flush_fills(self) -> None:
        """
        Insert buffered fill records into the database.
        """
        if not self._buffers["fills"]:
            return
        self._conn.executemany(
            """
            INSERT INTO fills (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, broker_order_id, symbol, fill_id, broker_fill_id, side, quantity_filled, fill_price, commission, exchange)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["fills"],
        )
        self._conn.commit()
        self._buffers["fills"].clear()

    def _flush_expirations(self) -> None:
        """
        Insert buffered expiration records into the database.
        """
        if not self._buffers["expirations"]:
            return
        self._conn.executemany(
            """
            INSERT INTO expirations (run_id, ts_event_ns, ts_created_ns, ts_broker_ns, associated_order_id, broker_order_id, symbol)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._buffers["expirations"],
        )
        self._conn.commit()
        self._buffers["expirations"].clear()
