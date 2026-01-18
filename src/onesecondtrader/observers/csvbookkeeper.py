import pathlib

import pandas as pd

from onesecondtrader import events, messaging


class CSVBookkeeper(messaging.Subscriber):
    BATCH_SIZE: int = 1000

    def __init__(
        self, event_bus: messaging.EventBus, results_path: pathlib.Path
    ) -> None:
        self._results_path = results_path
        self._bars_buffer: list[dict] = []
        self._fills_buffer: list[dict] = []
        self._orders_buffer: list[dict] = []

        super().__init__(event_bus)
        self._subscribe(
            events.BarProcessed,
            events.OrderFilled,
            events.OrderSubmission,
            events.OrderModification,
            events.OrderCancellation,
            events.OrderSubmissionAccepted,
            events.OrderModificationAccepted,
            events.OrderCancellationAccepted,
            events.OrderSubmissionRejected,
            events.OrderModificationRejected,
            events.OrderCancellationRejected,
            events.OrderExpired,
        )

    def _on_event(self, event: events.EventBase) -> None:
        match event:
            case events.BarProcessed() as e:
                self._on_processed_bar(e)
            case events.OrderFilled() as e:
                self._on_fill(e)
            case events.OrderSubmission() as e:
                self._on_order_event(e, "submission_requested")
            case events.OrderModification() as e:
                self._on_order_event(e, "modification_requested")
            case events.OrderCancellation() as e:
                self._on_order_event(e, "cancellation_requested")
            case events.OrderSubmissionAccepted() as e:
                self._on_order_event(e, "submission_accepted")
            case events.OrderModificationAccepted() as e:
                self._on_order_event(e, "modification_accepted")
            case events.OrderCancellationAccepted() as e:
                self._on_order_event(e, "cancellation_accepted")
            case events.OrderSubmissionRejected() as e:
                self._on_order_event(e, "submission_rejected")
            case events.OrderModificationRejected() as e:
                self._on_order_event(e, "modification_rejected")
            case events.OrderCancellationRejected() as e:
                self._on_order_event(e, "cancellation_rejected")
            case events.OrderExpired() as e:
                self._on_order_event(e, "expired")

    def _on_processed_bar(self, event: events.BarProcessed) -> None:
        record = {
            "ts_event": event.ts_event,
            "symbol": event.symbol,
            "bar_period": event.bar_period.name,
            "open": event.open,
            "high": event.high,
            "low": event.low,
            "close": event.close,
            "volume": event.volume,
        }
        record.update(event.indicators)
        self._bars_buffer.append(record)
        if len(self._bars_buffer) >= self.BATCH_SIZE:
            self._flush_bars()

    def _on_fill(self, event: events.OrderFilled) -> None:
        self._fills_buffer.append(
            {
                "ts_event": event.ts_event,
                "fill_id": str(event.fill_id),
                "broker_fill_id": event.broker_fill_id,
                "order_id": str(event.associated_order_id),
                "symbol": event.symbol,
                "side": event.side.name,
                "quantity": event.quantity_filled,
                "price": event.fill_price,
                "commission": event.commission,
                "exchange": event.exchange,
            }
        )
        if len(self._fills_buffer) >= self.BATCH_SIZE:
            self._flush_fills()

    def _on_order_event(self, event: events.EventBase, event_type: str) -> None:
        record: dict = {
            "ts_event": event.ts_event,
            "event_type": event_type,
        }
        match event:
            case events.OrderSubmission():
                record.update(
                    {
                        "order_id": str(event.system_order_id),
                        "symbol": event.symbol,
                        "order_type": event.order_type.name,
                        "side": event.side.name,
                        "quantity": event.quantity,
                        "limit_price": event.limit_price,
                        "stop_price": event.stop_price,
                    }
                )
            case events.OrderModification():
                record.update(
                    {
                        "order_id": str(event.system_order_id),
                        "symbol": event.symbol,
                        "quantity": event.quantity,
                        "limit_price": event.limit_price,
                        "stop_price": event.stop_price,
                    }
                )
            case events.OrderCancellation():
                record.update(
                    {
                        "order_id": str(event.system_order_id),
                        "symbol": event.symbol,
                    }
                )
            case events.OrderSubmissionAccepted() | events.OrderModificationAccepted():
                record.update(
                    {
                        "order_id": str(event.associated_order_id),
                        "broker_order_id": event.broker_order_id,
                    }
                )
            case events.OrderCancellationAccepted():
                record.update({"order_id": str(event.associated_order_id)})
            case (
                events.OrderSubmissionRejected()
                | events.OrderModificationRejected()
                | events.OrderCancellationRejected()
            ):
                record.update({"order_id": str(event.associated_order_id)})
            case events.OrderExpired():
                record.update({"order_id": str(event.associated_order_id)})

        self._orders_buffer.append(record)
        if len(self._orders_buffer) >= self.BATCH_SIZE:
            self._flush_orders()

    def _flush_bars(self) -> None:
        if not self._bars_buffer:
            return
        df = pd.DataFrame(self._bars_buffer)
        path = self._results_path / "processed_bars.csv"
        df.to_csv(path, mode="a", header=not path.exists(), index=False)
        self._bars_buffer.clear()

    def _flush_fills(self) -> None:
        if not self._fills_buffer:
            return
        df = pd.DataFrame(self._fills_buffer)
        path = self._results_path / "fills.csv"
        df.to_csv(path, mode="a", header=not path.exists(), index=False)
        self._fills_buffer.clear()

    def _flush_orders(self) -> None:
        if not self._orders_buffer:
            return
        df = pd.DataFrame(self._orders_buffer)
        path = self._results_path / "orders.csv"
        df.to_csv(path, mode="a", header=not path.exists(), index=False)
        self._orders_buffer.clear()

    def _cleanup(self) -> None:
        self._flush_bars()
        self._flush_fills()
        self._flush_orders()
