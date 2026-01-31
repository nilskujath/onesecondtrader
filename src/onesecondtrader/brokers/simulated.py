from __future__ import annotations

import dataclasses
import uuid

from onesecondtrader import events, messaging, models
from onesecondtrader.brokers.base import BrokerBase


@dataclasses.dataclass
class _PendingOrder:
    """
    Internal order state tracked by the simulated broker.

    This structure represents broker-side pending order state and is distinct from order request events.
    It is used to evaluate trigger conditions against incoming market bars and to generate fills when conditions are met.
    """

    order_id: uuid.UUID
    symbol: str
    order_type: models.OrderType
    side: models.TradeSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None


class SimulatedBroker(BrokerBase):
    """
    Event-driven simulated broker for backtesting.

    The broker subscribes to order request events and market bar events.
    Order requests are validated and accepted or rejected immediately.
    Accepted orders are stored as pending broker-side state and evaluated against each incoming
    bar.
    When an order triggers, a fill event is published with a deterministic fill price model based on the bar's OHLC values.

    The broker publishes response events using the event timestamp to preserve simulated time consistency.
    """

    commission_per_unit: float = 0.0
    minimum_commission_per_order: float = 0.0

    def __init__(self, event_bus: messaging.EventBus) -> None:
        """
        parameters:
            event_bus:
                Event bus used to receive order requests and market bars, and to publish broker responses and fills.
        """
        self._pending_market_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_limit_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_stop_orders: dict[uuid.UUID, _PendingOrder] = {}
        self._pending_stop_limit_orders: dict[uuid.UUID, _PendingOrder] = {}

        super().__init__(event_bus)
        self._subscribe(events.market.BarReceived)

    def connect(self) -> None:
        """
        Establish broker readiness.

        The simulated broker has no external connectivity requirements.
        This method is a no-op and exists to satisfy the broker interface.
        """
        pass

    def _on_event(self, event: events.EventBase) -> None:
        """
        Dispatch incoming events.

        Market bar events are routed to bar processing.
        All other events are delegated to the broker base class for order request handling.

        parameters:
            event:
                Incoming event received from the event bus.
        """
        match event:
            case events.market.BarReceived() as bar:
                self._on_bar(bar)
            case _:
                super()._on_event(event)

    def _on_bar(self, event: events.market.BarReceived) -> None:
        """
        Process an incoming market bar.

        Pending orders are evaluated against the bar in a fixed sequence to provide deterministic behavior.
        Crucially, limit orders are processed after stop limit orders to ensure that limit orders created by stop limit orders are evaluated against the same bar.

        parameters:
            event:
                Market bar used to trigger and price simulated fills.
        """
        self._process_market_orders(event)
        self._process_stop_orders(event)
        self._process_stop_limit_orders(event)
        self._process_limit_orders(event)

    def _process_market_orders(self, event: events.market.BarReceived) -> None:
        """
        Fill pending market orders for the bar symbol.

        Market orders are filled at the bar open price on the next received bar for the matching symbol.

        parameters:
            event:
                Market bar providing the simulated fill price and timestamps.
        """
        for order_id, order in list(self._pending_market_orders.items()):
            if order.symbol != event.symbol:
                continue

            self._publish(
                events.orders.FillEvent(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
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

    def _process_stop_orders(self, event: events.market.BarReceived) -> None:
        """
        Evaluate and fill pending stop orders for the bar symbol.

        Stop orders trigger when the bar crosses the stop level.
        The fill price is modeled as the worse of the stop price and the bar open in the direction of the trade.

        parameters:
            event:
                Market bar used to evaluate triggers and determine fill prices.
        """
        for order_id, order in list(self._pending_stop_orders.items()):
            if order.symbol != event.symbol:
                continue

            # This is for mypy, it has already been validated on submission
            assert order.stop_price is not None

            triggered = False
            match order.side:
                case models.TradeSide.BUY:
                    triggered = event.high >= order.stop_price
                case models.TradeSide.SELL:
                    triggered = event.low <= order.stop_price

            if not triggered:
                continue

            fill_price = 0.0
            match order.side:
                case models.TradeSide.BUY:
                    fill_price = max(order.stop_price, event.open)
                case models.TradeSide.SELL:
                    fill_price = min(order.stop_price, event.open)

            self._publish(
                events.orders.FillEvent(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
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

    def _process_stop_limit_orders(self, event: events.market.BarReceived) -> None:
        """
        Evaluate pending stop-limit orders for the bar symbol.

        Stop-limit orders trigger on stop conditions.
        When triggered, they are converted into pending limit orders at the same identifier.

        parameters:
            event:
                Market bar used to evaluate stop triggers.
        """
        for order_id, order in list(self._pending_stop_limit_orders.items()):
            if order.symbol != event.symbol:
                continue

            assert order.stop_price is not None

            triggered = False
            match order.side:
                case models.TradeSide.BUY:
                    triggered = event.high >= order.stop_price
                case models.TradeSide.SELL:
                    triggered = event.low <= order.stop_price

            if not triggered:
                continue

            limit_order = dataclasses.replace(order, order_type=models.OrderType.LIMIT)
            self._pending_limit_orders[order_id] = limit_order
            del self._pending_stop_limit_orders[order_id]

    def _process_limit_orders(self, event: events.market.BarReceived) -> None:
        """
        Evaluate and fill pending limit orders for the bar symbol.

        Limit orders trigger when the bar crosses the limit level.
        The fill price is modeled as the better of the limit price and the bar open in the direction of the trade.

        parameters:
            event:
                Market bar used to evaluate triggers and determine fill prices.
        """
        for order_id, order in list(self._pending_limit_orders.items()):
            if order.symbol != event.symbol:
                continue

            assert order.limit_price is not None

            triggered = False
            match order.side:
                case models.TradeSide.BUY:
                    triggered = event.low <= order.limit_price
                case models.TradeSide.SELL:
                    triggered = event.high >= order.limit_price

            if not triggered:
                continue

            fill_price = 0.0
            match order.side:
                case models.TradeSide.BUY:
                    fill_price = min(order.limit_price, event.open)
                case models.TradeSide.SELL:
                    fill_price = max(order.limit_price, event.open)

            self._publish(
                events.orders.FillEvent(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
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

    def _reject_if_invalid_submission(
        self, event: events.requests.OrderSubmissionRequest
    ) -> bool:
        """
        Validate an order submission request.

        Invalid submissions are rejected immediately by publishing an `OrderRejected` response event.

        parameters:
            event:
                Order submission request event to validate.

        returns:
            True if the submission is invalid and was rejected, otherwise False.
        """
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
            self._publish(
                events.responses.OrderRejected(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
                    associated_order_id=event.system_order_id,
                    rejection_reason=models.OrderRejectionReason.UNKNOWN,
                    rejection_message="Unknown",
                )
            )

        return is_invalid

    def _on_submit_order(self, event: events.requests.OrderSubmissionRequest) -> None:
        """
        Handle an order submission request.

        Valid orders are stored as pending broker-side state and acknowledged via an `OrderAccepted` response event.

        parameters:
            event:
                Order submission request event.
        """
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

        self._publish(
            events.responses.OrderAccepted(
                ts_event_ns=event.ts_event_ns,
                ts_broker_ns=event.ts_event_ns,
                associated_order_id=order.order_id,
            )
        )

    def _on_cancel_order(self, event: events.requests.OrderCancellationRequest) -> None:
        """
        Handle an order cancellation request.

        If the referenced order is pending, it is removed and acknowledged via `CancellationAccepted`.
        Otherwise, `CancellationRejected` is published.

        parameters:
            event:
                Order cancellation request event.
        """
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

        if removed:
            self._publish(
                events.responses.CancellationAccepted(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
                    associated_order_id=order_id,
                )
            )
        else:
            self._publish(
                events.responses.CancellationRejected(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
                    associated_order_id=order_id,
                    rejection_reason=models.CancellationRejectionReason.UNKNOWN,
                    rejection_message="Unknown",
                )
            )

    def _reject_if_invalid_modification(
        self, event: events.requests.OrderModificationRequest
    ) -> bool:
        """
        Validate an order modification request.

        Invalid modifications are rejected immediately by publishing a `ModificationRejected` response event.

        parameters:
            event:
                Order modification request event to validate.

        returns:
            True if the modification is invalid and was rejected, otherwise False.
        """
        is_invalid = (
            (event.quantity is not None and event.quantity <= 0)
            or (event.limit_price is not None and event.limit_price <= 0)
            or (event.stop_price is not None and event.stop_price <= 0)
        )

        if is_invalid:
            self._publish(
                events.responses.ModificationRejected(
                    ts_event_ns=event.ts_event_ns,
                    ts_broker_ns=event.ts_event_ns,
                    associated_order_id=event.system_order_id,
                    rejection_reason=models.ModificationRejectionReason.UNKNOWN,
                    rejection_message="Unknown",
                )
            )

        return is_invalid

    def _on_modify_order(self, event: events.requests.OrderModificationRequest) -> None:
        """
        Handle an order modification request.

        If the referenced order is pending, its fields are updated and acknowledged via `ModificationAccepted`.
        Otherwise, `ModificationRejected` is published.

        parameters:
            event:
                Order modification request event.
        """
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

                self._publish(
                    events.responses.ModificationAccepted(
                        ts_event_ns=event.ts_event_ns,
                        ts_broker_ns=event.ts_event_ns,
                        associated_order_id=order_id,
                    )
                )
                return

        self._publish(
            events.responses.ModificationRejected(
                ts_event_ns=event.ts_event_ns,
                ts_broker_ns=event.ts_event_ns,
                associated_order_id=order_id,
                rejection_reason=models.ModificationRejectionReason.UNKNOWN,
                rejection_message="Unknown",
            )
        )
