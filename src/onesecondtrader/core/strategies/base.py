from __future__ import annotations

import abc
import uuid
from types import SimpleNamespace

import pandas as pd

from onesecondtrader.core import events, indicators, messaging, models


class StrategyBase(messaging.Subscriber, abc.ABC):
    name: str = ""
    symbols: list[str] = []
    parameters: dict[str, models.ParamSpec] = {}

    def __init__(self, event_bus: messaging.EventBus, **overrides) -> None:
        super().__init__(event_bus)

        for name, spec in self.parameters.items():
            value = overrides.get(name, spec.default)
            setattr(self, name, value)

        self._subscribe(
            events.BarReceived,
            events.OrderSubmissionAccepted,
            events.OrderModificationAccepted,
            events.OrderCancellationAccepted,
            events.OrderSubmissionRejected,
            events.OrderModificationRejected,
            events.OrderCancellationRejected,
            events.OrderFilled,
            events.OrderExpired,
        )

        self._current_symbol: str = ""
        self._current_ts: pd.Timestamp = pd.Timestamp.now(tz="UTC")
        self._indicators: list[indicators.Indicator] = []

        self._fills: dict[str, list[models.FillRecord]] = {}
        self._positions: dict[str, float] = {}
        self._avg_prices: dict[str, float] = {}
        self._pending_orders: dict[uuid.UUID, models.OrderRecord] = {}
        self._submitted_orders: dict[uuid.UUID, models.OrderRecord] = {}
        self._submitted_modifications: dict[uuid.UUID, models.OrderRecord] = {}
        self._submitted_cancellations: dict[uuid.UUID, models.OrderRecord] = {}

        # OHLCV as indicators for history access: self.bar.close.history
        self.bar = SimpleNamespace(
            open=self.add_indicator(indicators.Open()),
            high=self.add_indicator(indicators.High()),
            low=self.add_indicator(indicators.Low()),
            close=self.add_indicator(indicators.Close()),
            volume=self.add_indicator(indicators.Volume()),
        )

        # Hook for subclasses to register indicators without overriding __init__
        self.setup()

    def add_indicator(self, ind: indicators.Indicator) -> indicators.Indicator:
        self._indicators.append(ind)
        return ind

    @property
    def position(self) -> float:
        return self._positions.get(self._current_symbol, 0.0)

    @property
    def avg_price(self) -> float:
        return self._avg_prices.get(self._current_symbol, 0.0)

    def submit_order(
        self,
        order_type: models.OrderType,
        side: models.OrderSide,
        quantity: float,
        limit_price: float | None = None,
        stop_price: float | None = None,
        action: models.ActionType | None = None,
        signal: str | None = None,
    ) -> uuid.UUID:
        order_id = uuid.uuid4()

        event = events.OrderSubmission(
            ts_event=self._current_ts,
            system_order_id=order_id,
            symbol=self._current_symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            action=action,
            signal=signal,
        )

        order = models.OrderRecord(
            order_id=order_id,
            symbol=self._current_symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            action=action,
            signal=signal,
        )

        self._submitted_orders[order_id] = order
        self._publish(event)
        return order_id

    def submit_modification(
        self,
        order_id: uuid.UUID,
        quantity: float | None = None,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> bool:
        original_order = self._pending_orders.get(order_id)
        if original_order is None:
            return False

        event = events.OrderModification(
            ts_event=self._current_ts,
            system_order_id=order_id,
            symbol=original_order.symbol,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
        )

        modified_order = models.OrderRecord(
            order_id=order_id,
            symbol=original_order.symbol,
            order_type=original_order.order_type,
            side=original_order.side,
            quantity=quantity if quantity is not None else original_order.quantity,
            limit_price=(
                limit_price if limit_price is not None else original_order.limit_price
            ),
            stop_price=(
                stop_price if stop_price is not None else original_order.stop_price
            ),
            action=original_order.action,
            signal=original_order.signal,
            filled_quantity=original_order.filled_quantity,
        )

        self._submitted_modifications[order_id] = modified_order
        self._publish(event)
        return True

    def submit_cancellation(self, order_id: uuid.UUID) -> bool:
        original_order = self._pending_orders.get(order_id)
        if original_order is None:
            return False

        event = events.OrderCancellation(
            ts_event=self._current_ts,
            system_order_id=order_id,
            symbol=original_order.symbol,
        )

        self._submitted_cancellations[order_id] = original_order
        self._publish(event)
        return True

    def _on_event(self, event: events.EventBase) -> None:
        match event:
            case events.BarReceived() as bar_event:
                self._on_bar_received(bar_event)
            case events.OrderSubmissionAccepted() as accepted:
                self._on_order_submission_accepted(accepted)
            case events.OrderModificationAccepted() as accepted:
                self._on_order_modification_accepted(accepted)
            case events.OrderCancellationAccepted() as accepted:
                self._on_order_cancellation_accepted(accepted)
            case events.OrderSubmissionRejected() as rejected:
                self._on_order_submission_rejected(rejected)
            case events.OrderModificationRejected() as rejected:
                self._on_order_modification_rejected(rejected)
            case events.OrderCancellationRejected() as rejected:
                self._on_order_cancellation_rejected(rejected)
            case events.OrderFilled() as filled:
                self._on_order_filled(filled)
            case events.OrderExpired() as expired:
                self._on_order_expired(expired)
            case _:
                return

    def _on_bar_received(self, event: events.BarReceived) -> None:
        if event.symbol not in self.symbols:
            return
        if event.bar_period != self.bar_period:  # type: ignore[attr-defined]
            return

        self._current_symbol = event.symbol
        self._current_ts = event.ts_event

        for ind in self._indicators:
            ind.update(event)

        self._emit_processed_bar(event)
        self.on_bar(event)

    def _emit_processed_bar(self, event: events.BarReceived) -> None:
        ohlcv_names = {"OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"}

        indicator_values = {
            f"{ind.plot_at:02d}_{ind.name}": ind.latest
            for ind in self._indicators
            if ind.name not in ohlcv_names
        }

        processed_bar = events.BarProcessed(
            ts_event=event.ts_event,
            symbol=event.symbol,
            bar_period=event.bar_period,
            open=event.open,
            high=event.high,
            low=event.low,
            close=event.close,
            volume=event.volume,
            indicators=indicator_values,
        )

        self._publish(processed_bar)

    def _on_order_submission_accepted(
        self, event: events.OrderSubmissionAccepted
    ) -> None:
        order = self._submitted_orders.pop(event.associated_order_id, None)
        if order is not None:
            self._pending_orders[event.associated_order_id] = order

    def _on_order_modification_accepted(
        self, event: events.OrderModificationAccepted
    ) -> None:
        modified_order = self._submitted_modifications.pop(
            event.associated_order_id, None
        )
        if modified_order is not None:
            self._pending_orders[event.associated_order_id] = modified_order

    def _on_order_cancellation_accepted(
        self, event: events.OrderCancellationAccepted
    ) -> None:
        self._submitted_cancellations.pop(event.associated_order_id, None)
        self._pending_orders.pop(event.associated_order_id, None)

    def _on_order_submission_rejected(
        self, event: events.OrderSubmissionRejected
    ) -> None:
        self._submitted_orders.pop(event.associated_order_id, None)

    def _on_order_modification_rejected(
        self, event: events.OrderModificationRejected
    ) -> None:
        self._submitted_modifications.pop(event.associated_order_id, None)

    def _on_order_cancellation_rejected(
        self, event: events.OrderCancellationRejected
    ) -> None:
        self._submitted_cancellations.pop(event.associated_order_id, None)

    def _on_order_filled(self, event: events.OrderFilled) -> None:
        # Track partial fills: only remove order when fully filled
        order = self._pending_orders.get(event.associated_order_id)
        if order:
            order.filled_quantity += event.quantity_filled
            if order.filled_quantity >= order.quantity:
                self._pending_orders.pop(event.associated_order_id)

        fill = models.FillRecord(
            fill_id=event.fill_id,
            order_id=event.associated_order_id,
            symbol=event.symbol,
            side=event.side,
            quantity=event.quantity_filled,
            price=event.fill_price,
            commission=event.commission,
            ts_event=event.ts_event,
        )

        self._fills.setdefault(event.symbol, []).append(fill)
        self._update_position(event)

    def _update_position(self, event: events.OrderFilled) -> None:
        symbol = event.symbol
        fill_qty = event.quantity_filled
        fill_price = event.fill_price

        signed_qty = 0.0
        match event.side:
            case models.OrderSide.BUY:
                signed_qty = fill_qty
            case models.OrderSide.SELL:
                signed_qty = -fill_qty

        old_pos = self._positions.get(symbol, 0.0)
        old_avg = self._avg_prices.get(symbol, 0.0)
        new_pos = old_pos + signed_qty

        if new_pos == 0.0:
            new_avg = 0.0
        elif old_pos == 0.0:
            new_avg = fill_price
        elif (old_pos > 0 and signed_qty > 0) or (old_pos < 0 and signed_qty < 0):
            new_avg = (old_avg * abs(old_pos) + fill_price * abs(signed_qty)) / abs(
                new_pos
            )
        else:
            if abs(new_pos) <= abs(old_pos):
                new_avg = old_avg
            else:
                new_avg = fill_price

        self._positions[symbol] = new_pos
        self._avg_prices[symbol] = new_avg

    def _on_order_expired(self, event: events.OrderExpired) -> None:
        self._pending_orders.pop(event.associated_order_id, None)

    # Override to register indicators. Called at end of __init__.
    def setup(self) -> None:
        pass

    @abc.abstractmethod
    def on_bar(self, event: events.BarReceived) -> None:
        pass
