import json
import pathlib
import sqlite3

import pandas as pd

from onesecondtrader.core import events
from onesecondtrader.core.messaging import EventBus, Subscriber


class RunRecorder(Subscriber):
    db_path: str = "runs.db"

    def __init__(
        self,
        event_bus: EventBus,
        run_id: str,
        strategy: str,
        mode: str,
        symbols: list[str] | None = None,
        bar_period: str | None = None,
    ) -> None:
        self._run_id = run_id
        self._strategy = strategy
        self._mode = mode
        self._symbols = symbols or []
        self._bar_period = bar_period
        self._conn = self._init_db()
        self._insert_run()
        super().__init__(event_bus)
        self._subscribe(
            events.BarProcessed,
            events.OrderSubmission,
            events.OrderModification,
            events.OrderCancellation,
            events.OrderSubmissionAccepted,
            events.OrderSubmissionRejected,
            events.OrderModificationAccepted,
            events.OrderModificationRejected,
            events.OrderCancellationAccepted,
            events.OrderCancellationRejected,
            events.OrderFilled,
            events.OrderExpired,
        )

    def _init_db(self) -> sqlite3.Connection:
        schema_path = pathlib.Path(__file__).parent / "schema.sql"
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(schema_path.read_text())
        return conn

    def _insert_run(self) -> None:
        self._conn.execute(
            """
            INSERT INTO runs (run_id, strategy, symbols, bar_period, mode, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                self._strategy,
                json.dumps(self._symbols) if self._symbols else None,
                self._bar_period,
                self._mode,
                "running",
                pd.Timestamp.now(tz="UTC").isoformat(),
            ),
        )
        self._conn.commit()

    def _on_event(self, event: events.EventBase) -> None:
        match event:
            case events.BarProcessed():
                self._record_bar(event)
            case events.OrderSubmission():
                self._record_order_request(event, "submission")
            case events.OrderModification():
                self._record_order_request(event, "modification")
            case events.OrderCancellation():
                self._record_order_request(event, "cancellation")
            case events.OrderFilled():
                self._record_fill(event)
            case events.OrderSubmissionAccepted():
                self._record_order_response(event, "submission_accepted")
            case events.OrderSubmissionRejected():
                self._record_order_response(event, "submission_rejected")
            case events.OrderModificationAccepted():
                self._record_order_response(event, "modification_accepted")
            case events.OrderModificationRejected():
                self._record_order_response(event, "modification_rejected")
            case events.OrderCancellationAccepted():
                self._record_order_response(event, "cancellation_accepted")
            case events.OrderCancellationRejected():
                self._record_order_response(event, "cancellation_rejected")
            case events.OrderExpired():
                self._record_order_response(event, "expired")

    def _record_bar(self, event: events.BarProcessed) -> None:
        self._conn.execute(
            """
            INSERT INTO bars (run_id, ts_event, symbol, bar_period, open, high, low, close, volume, indicators)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                event.ts_event.isoformat(),
                event.symbol,
                event.bar_period.value,
                event.open,
                event.high,
                event.low,
                event.close,
                event.volume,
                json.dumps(event.indicators) if event.indicators else None,
            ),
        )
        self._conn.commit()

    def _record_order_request(
        self, event: events.BrokerRequestEvent, request_type: str
    ) -> None:
        order_type = getattr(event, "order_type", None)
        side = getattr(event, "side", None)
        action = getattr(event, "action", None)
        self._conn.execute(
            """
            INSERT INTO order_requests (run_id, ts_event, request_type, order_id, symbol, order_type, side, quantity, limit_price, stop_price, action, signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                event.ts_event.isoformat(),
                request_type,
                str(event.system_order_id),
                getattr(event, "symbol", None),
                order_type.value if order_type else None,
                side.value if side else None,
                getattr(event, "quantity", None),
                getattr(event, "limit_price", None),
                getattr(event, "stop_price", None),
                action.name if action else None,
                getattr(event, "signal", None),
            ),
        )
        self._conn.commit()

    def _record_order_response(
        self, event: events.BrokerResponseEvent, response_type: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO order_responses (run_id, ts_event, ts_broker, response_type, order_id, broker_order_id, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                event.ts_event.isoformat(),
                event.ts_broker.isoformat(),
                response_type,
                str(event.associated_order_id),
                getattr(event, "broker_order_id", None),
                getattr(event, "reason", None),
            ),
        )
        self._conn.commit()

    def _record_fill(self, event: events.OrderFilled) -> None:
        self._conn.execute(
            """
            INSERT INTO fills (run_id, ts_event, ts_broker, fill_id, order_id, broker_fill_id, symbol, side, quantity, price, commission, exchange)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._run_id,
                event.ts_event.isoformat(),
                event.ts_broker.isoformat(),
                str(event.fill_id),
                str(event.associated_order_id),
                event.broker_fill_id,
                event.symbol,
                event.side.value,
                event.quantity_filled,
                event.fill_price,
                event.commission,
                event.exchange,
            ),
        )
        self._conn.commit()

    def _cleanup(self) -> None:
        self._conn.execute(
            """
            UPDATE runs SET status = ?, completed_at = ? WHERE run_id = ?
            """,
            ("completed", pd.Timestamp.now(tz="UTC").isoformat(), self._run_id),
        )
        self._conn.commit()
        self._conn.close()
