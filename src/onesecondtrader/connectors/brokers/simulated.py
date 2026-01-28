from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader.core import events, messaging, models
from onesecondtrader.core.brokers import BrokerBase


@dataclasses.dataclass
class _PendingOrder:
    # Order state tracked by the broker, distinct from the OrderSubmission event
    order_id: uuid.UUID
    symbol: str
    order_type: models.OrderType
    side: models.OrderSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None


class SimulatedBroker(BrokerBase):
    commission_per_unit: float = 0.0
    minimum_commission_per_order: float = 0.0

    def __init__(self, event_bus: messaging.EventBus) -> None:
        self._pending_market_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_limit_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_stop_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_stop_limit_orders: dict[uuid.UUID, _PendingOrder] = {}

        super().__init__(event_bus)
        self._subscribe(events.BarReceived)

    def connect(self) -> None:
        pass

    def _on_event(self, event: events.EventBase) -> None:
        match event:
            case events.BarReceived() as bar:
                self._on_bar(bar)
            case _:
                super()._on_event(event)

    def _on_bar(self, event: events.BarReceived) -> None:
        self._process_market_orders(event)
        self._process_stop_orders(event)
        self._process_stop_limit_orders(event)
        self._process_limit_orders(event)

    def _process_market_orders(self, event: events.BarReceived) -> None:
        for order_id, order in list(self._pending_market_orders.items()):
            if order.symbol != event.symbol:
                continue

            self._publish(
                events.OrderFilled(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity_filled=order.quantity,
                    fill_price=event.open,
                    commission=max(
                        order.quantity * self.commission_per_unit,
                        self.minimum_commission_per_order,
                    ),
                )
            )
            del self._pending_market_orders[order_id]

    def _process_stop_orders(self, event: events.BarReceived) -> None:
        for order_id, order in list(self._pending_stop_orders.items()):
            if order.symbol != event.symbol:
                continue

            # This is for mypy, it has already been validated on submission
            assert order.stop_price is not None

            triggered = False
            match order.side:
                case models.OrderSide.BUY:
                    triggered = event.high >= order.stop_price
                case models.OrderSide.SELL:
                    triggered = event.low <= order.stop_price

            if not triggered:
                continue

            fill_price = 0.0
            match order.side:
                case models.OrderSide.BUY:
                    fill_price = max(order.stop_price, event.open)
                case models.OrderSide.SELL:
                    fill_price = min(order.stop_price, event.open)

            self._publish(
                events.OrderFilled(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity_filled=order.quantity,
                    fill_price=fill_price,
                    commission=max(
                        order.quantity * self.commission_per_unit,
                        self.minimum_commission_per_order,
                    ),
                )
            )
            del self._pending_stop_orders[order_id]

    def _process_stop_limit_orders(self, event: events.BarReceived) -> None:
        for order_id, order in list(self._pending_stop_limit_orders.items()):
            if order.symbol != event.symbol:
                continue

            # This is for mypy, it has already been validated on submission
            assert order.stop_price is not None

            triggered = False
            match order.side:
                case models.OrderSide.BUY:
                    triggered = event.high >= order.stop_price
                case models.OrderSide.SELL:
                    triggered = event.low <= order.stop_price

            if not triggered:
                continue

            limit_order = dataclasses.replace(order, order_type=models.OrderType.LIMIT)
            self._pending_limit_orders[order_id] = limit_order
            del self._pending_stop_limit_orders[order_id]

    def _process_limit_orders(self, event: events.BarReceived) -> None:
        for order_id, order in list(self._pending_limit_orders.items()):
            if order.symbol != event.symbol:
                continue

            # This is for mypy, it has already been validated on submission
            assert order.limit_price is not None

            triggered = False
            match order.side:
                case models.OrderSide.BUY:
                    triggered = event.low <= order.limit_price
                case models.OrderSide.SELL:
                    triggered = event.high >= order.limit_price

            if not triggered:
                continue

            fill_price = 0.0
            match order.side:
                case models.OrderSide.BUY:
                    fill_price = min(order.limit_price, event.open)
                case models.OrderSide.SELL:
                    fill_price = max(order.limit_price, event.open)

            self._publish(
                events.OrderFilled(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity_filled=order.quantity,
                    fill_price=fill_price,
                    commission=max(
                        order.quantity * self.commission_per_unit,
                        self.minimum_commission_per_order,
                    ),
                )
            )
            del self._pending_limit_orders[order_id]

    def _reject_if_invalid_submission(self, event: events.OrderSubmission) -> bool:
        is_invalid = event.quantity <= 0

        match event.order_type:
            case models.OrderType.LIMIT:
                is_invalid = (
                    is_invalid or event.limit_price is None or event.limit_price <= 0
                )
            case models.OrderType.STOP:
                is_invalid = (
                    is_invalid or event.stop_price is None or event.stop_price <= 0
                )
            case models.OrderType.STOP_LIMIT:
                is_invalid = is_invalid or (
                    event.limit_price is None
                    or event.limit_price <= 0
                    or event.stop_price is None
                    or event.stop_price <= 0
                )

        if is_invalid:
            # Use event timestamp to maintain simulated time consistency in backtesting
            self._publish(
                events.OrderSubmissionRejected(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=event.system_order_id,
                )
            )

        return is_invalid

    def _on_submit_order(self, event: events.OrderSubmission) -> None:
        if self._reject_if_invalid_submission(event):
            return

        order = _PendingOrder(
            order_id=event.system_order_id,
            symbol=event.symbol,
            order_type=event.order_type,
            side=event.side,
            quantity=event.quantity,
            limit_price=event.limit_price,
            stop_price=event.stop_price,
        )

        match order.order_type:
            case models.OrderType.MARKET:
                self._pending_market_orders[order.order_id] = order
            case models.OrderType.LIMIT:
                self._pending_limit_orders[order.order_id] = order
            case models.OrderType.STOP:
                self._pending_stop_orders[order.order_id] = order
            case models.OrderType.STOP_LIMIT:
                self._pending_stop_limit_orders[order.order_id] = order

        # Use event timestamp to maintain simulated time consistency in backtesting
        self._publish(
            events.OrderSubmissionAccepted(
                ts_event=event.ts_event,
                ts_broker=event.ts_event,
                associated_order_id=order.order_id,
            )
        )

    def _on_cancel_order(self, event: events.OrderCancellation) -> None:
        order_id = event.system_order_id

        removed = False
        for pending_orders in (
            self._pending_market_orders,
            self._pending_limit_orders,
            self._pending_stop_orders,
            self._pending_stop_limit_orders,
        ):
            if order_id in pending_orders:
                del pending_orders[order_id]
                removed = True
                break

        # Use event timestamp to maintain simulated time consistency in backtesting
        if removed:
            self._publish(
                events.OrderCancellationAccepted(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=order_id,
                )
            )
        else:
            self._publish(
                events.OrderCancellationRejected(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=order_id,
                )
            )

    def _reject_if_invalid_modification(self, event: events.OrderModification) -> bool:
        is_invalid = (
            (event.quantity is not None and event.quantity <= 0)
            or (event.limit_price is not None and event.limit_price <= 0)
            or (event.stop_price is not None and event.stop_price <= 0)
        )

        if is_invalid:
            # Use event timestamp to maintain simulated time consistency in backtesting
            self._publish(
                events.OrderModificationRejected(
                    ts_event=event.ts_event,
                    ts_broker=event.ts_event,
                    associated_order_id=event.system_order_id,
                )
            )

        return is_invalid

    def _on_modify_order(self, event: events.OrderModification) -> None:
        if self._reject_if_invalid_modification(event):
            return

        order_id = event.system_order_id

        for pending_orders in (
            self._pending_market_orders,
            self._pending_limit_orders,
            self._pending_stop_orders,
            self._pending_stop_limit_orders,
        ):
            if order_id in pending_orders:
                order = pending_orders[order_id]

                new_quantity = (
                    event.quantity if event.quantity is not None else order.quantity
                )
                new_limit_price = (
                    event.limit_price
                    if event.limit_price is not None
                    else order.limit_price
                )
                new_stop_price = (
                    event.stop_price
                    if event.stop_price is not None
                    else order.stop_price
                )

                pending_orders[order_id] = dataclasses.replace(
                    order,
                    quantity=new_quantity,
                    limit_price=new_limit_price,
                    stop_price=new_stop_price,
                )

                # Use event timestamp to maintain simulated time consistency in backtesting
                self._publish(
                    events.OrderModificationAccepted(
                        ts_event=event.ts_event,
                        ts_broker=event.ts_event,
                        associated_order_id=order_id,
                    )
                )
                return

        # Use event timestamp to maintain simulated time consistency in backtesting
        self._publish(
            events.OrderModificationRejected(
                ts_event=event.ts_event,
                ts_broker=event.ts_event,
                associated_order_id=order_id,
            )
        )
