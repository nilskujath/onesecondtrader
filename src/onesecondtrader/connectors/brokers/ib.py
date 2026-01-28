from __future__ import annotations

import dataclasses
import logging
import os
import sqlite3
import uuid

import pandas as pd
from ib_async import LimitOrder, MarketOrder, StopLimitOrder, StopOrder, Trade

from onesecondtrader.connectors.gateways.ib import _get_gateway, make_contract
from onesecondtrader.core import events, messaging, models
from onesecondtrader.core.brokers import BrokerBase

_logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _OrderMapping:
    system_order_id: uuid.UUID
    symbol: str
    side: models.OrderSide
    trade: Trade


class IBBroker(BrokerBase):
    """
    Live order execution broker for Interactive Brokers.

    Submits orders to IB and translates IB order events back to system events.

    Symbol Resolution:
        Uses the same resolution logic as IBDatafeed:

        1. Explicit format: ``SYMBOL:SECTYPE:CURRENCY:EXCHANGE[:EXPIRY[:STRIKE[:RIGHT]]]``
        2. Secmaster lookup: If ``db_path`` is configured
        3. Default: US stock on SMART routing

    Order Types:
        - ``OrderType.MARKET``: Market order
        - ``OrderType.LIMIT``: Limit order
        - ``OrderType.STOP``: Stop order (becomes market when triggered)
        - ``OrderType.STOP_LIMIT``: Stop-limit order

    Attributes:
        db_path: Optional path to secmaster database for symbol resolution.
    """

    db_path: str = ""

    def __init__(self, event_bus: messaging.EventBus) -> None:
        super().__init__(event_bus)
        self._gateway = _get_gateway()
        self._connected = False
        self._db_connection: sqlite3.Connection | None = None
        self._order_mappings: dict[uuid.UUID, _OrderMapping] = {}
        self._ib_to_system_id: dict[int, uuid.UUID] = {}
        self._pending_cancellations: set[uuid.UUID] = set()
        self._pending_modifications: dict[uuid.UUID, events.OrderModification] = {}
        self._filled_quantities: dict[uuid.UUID, float] = {}

    def connect(self) -> None:
        if self._connected:
            return
        _logger.info("Connecting to IB")
        self._gateway.acquire()
        self._gateway.register_reconnect_callback(self._on_reconnect)
        self._gateway.register_disconnect_callback(self._on_disconnect)
        db_path = self.db_path or os.environ.get("SECMASTER_DB_PATH", "")
        if db_path and os.path.exists(db_path):
            self._db_connection = sqlite3.connect(db_path, check_same_thread=False)

        self._register_ib_events()
        self._connected = True
        _logger.info("Connected to IB")

    def disconnect(self) -> None:
        if not self._connected:
            return
        _logger.info("Disconnecting from IB")

        self._gateway.unregister_reconnect_callback(self._on_reconnect)
        self._gateway.unregister_disconnect_callback(self._on_disconnect)
        self._unregister_ib_events()

        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None
        self._gateway.release()
        self._connected = False
        self.shutdown()
        _logger.info("Disconnected from IB")

    def _register_ib_events(self) -> None:
        ib = self._gateway.ib
        ib.orderStatusEvent += self._on_order_status
        ib.execDetailsEvent += self._on_exec_details
        ib.errorEvent += self._on_error

    def _unregister_ib_events(self) -> None:
        ib = self._gateway.ib
        ib.orderStatusEvent -= self._on_order_status
        ib.execDetailsEvent -= self._on_exec_details
        ib.errorEvent -= self._on_error

    def _on_disconnect(self) -> None:
        pending_count = len(self._order_mappings)
        _logger.warning("IB disconnected, expiring %d pending orders", pending_count)
        now = pd.Timestamp.now(tz="UTC")
        for order_id in list(self._order_mappings.keys()):
            self._publish(
                events.OrderExpired(
                    ts_event=now,
                    ts_broker=now,
                    associated_order_id=order_id,
                )
            )
        self._order_mappings.clear()
        self._ib_to_system_id.clear()
        self._pending_cancellations.clear()
        self._pending_modifications.clear()
        self._filled_quantities.clear()

    def _on_reconnect(self) -> None:
        _logger.info("IB reconnected, re-registering event handlers")
        self._register_ib_events()

    def _on_submit_order(self, event: events.OrderSubmission) -> None:
        _logger.info(
            "Submitting order: %s %s %s %s",
            event.side.name,
            event.quantity,
            event.symbol,
            event.order_type.name,
        )
        contract = self._make_contract(event.symbol)
        action = "BUY" if event.side == models.OrderSide.BUY else "SELL"

        order = self._create_ib_order(event, action)
        if order is None:
            _logger.warning(
                "Order rejected (invalid params): %s", event.system_order_id
            )
            self._publish(
                events.OrderSubmissionRejected(
                    ts_event=pd.Timestamp.now(tz="UTC"),
                    ts_broker=pd.Timestamp.now(tz="UTC"),
                    associated_order_id=event.system_order_id,
                    reason="Invalid order parameters",
                )
            )
            return

        async def _place():
            return self._gateway.ib.placeOrder(contract, order)

        trade = self._gateway.run_coro(_place())

        mapping = _OrderMapping(
            system_order_id=event.system_order_id,
            symbol=event.symbol,
            side=event.side,
            trade=trade,
        )
        self._order_mappings[event.system_order_id] = mapping
        self._ib_to_system_id[trade.order.orderId] = event.system_order_id
        self._filled_quantities[event.system_order_id] = 0.0

        _logger.info(
            "Order accepted: %s -> IB order %d",
            event.system_order_id,
            trade.order.orderId,
        )
        self._publish(
            events.OrderSubmissionAccepted(
                ts_event=pd.Timestamp.now(tz="UTC"),
                ts_broker=pd.Timestamp.now(tz="UTC"),
                associated_order_id=event.system_order_id,
                broker_order_id=str(trade.order.orderId),
            )
        )

    def _on_cancel_order(self, event: events.OrderCancellation) -> None:
        order_id = event.system_order_id
        _logger.info("Cancelling order: %s", order_id)
        mapping = self._order_mappings.get(order_id)

        if mapping is None:
            _logger.warning("Cancel rejected (not found): %s", order_id)
            self._publish(
                events.OrderCancellationRejected(
                    ts_event=pd.Timestamp.now(tz="UTC"),
                    ts_broker=pd.Timestamp.now(tz="UTC"),
                    associated_order_id=order_id,
                    reason="Order not found",
                )
            )
            return

        self._pending_cancellations.add(order_id)

        async def _cancel():
            self._gateway.ib.cancelOrder(mapping.trade.order)

        self._gateway.run_coro(_cancel())

    def _on_modify_order(self, event: events.OrderModification) -> None:
        order_id = event.system_order_id
        _logger.info("Modifying order: %s", order_id)
        mapping = self._order_mappings.get(order_id)

        if mapping is None:
            _logger.warning("Modify rejected (not found): %s", order_id)
            self._publish(
                events.OrderModificationRejected(
                    ts_event=pd.Timestamp.now(tz="UTC"),
                    ts_broker=pd.Timestamp.now(tz="UTC"),
                    associated_order_id=order_id,
                    reason="Order not found",
                )
            )
            return

        trade = mapping.trade
        order = trade.order

        if event.quantity is not None:
            order.totalQuantity = event.quantity
        if event.limit_price is not None:
            order.lmtPrice = event.limit_price
        if event.stop_price is not None:
            order.auxPrice = event.stop_price

        self._pending_modifications[order_id] = event

        async def _modify():
            self._gateway.ib.placeOrder(trade.contract, order)

        self._gateway.run_coro(_modify())

    def _on_order_status(self, trade: Trade) -> None:
        ib_order_id = trade.order.orderId
        system_order_id = self._ib_to_system_id.get(ib_order_id)
        if system_order_id is None:
            return

        status = trade.orderStatus.status
        now = pd.Timestamp.now(tz="UTC")

        if system_order_id in self._pending_cancellations:
            if status == "Cancelled":
                _logger.info("Order cancelled: %s", system_order_id)
                self._pending_cancellations.discard(system_order_id)
                self._publish(
                    events.OrderCancellationAccepted(
                        ts_event=now,
                        ts_broker=now,
                        associated_order_id=system_order_id,
                    )
                )
                self._cleanup_order(system_order_id)
            return

        if system_order_id in self._pending_modifications:
            if status in ("PreSubmitted", "Submitted"):
                _logger.info("Order modified: %s", system_order_id)
                self._pending_modifications.pop(system_order_id, None)
                self._publish(
                    events.OrderModificationAccepted(
                        ts_event=now,
                        ts_broker=now,
                        associated_order_id=system_order_id,
                        broker_order_id=str(ib_order_id),
                    )
                )
            return

        if status == "Inactive":
            mapping = self._order_mappings.get(system_order_id)
            if mapping:
                _logger.warning("Order expired (inactive): %s", system_order_id)
                self._publish(
                    events.OrderExpired(
                        ts_event=now,
                        ts_broker=now,
                        associated_order_id=system_order_id,
                    )
                )
                self._cleanup_order(system_order_id)

    def _on_exec_details(self, trade: Trade, fill) -> None:
        ib_order_id = trade.order.orderId
        system_order_id = self._ib_to_system_id.get(ib_order_id)
        if system_order_id is None:
            return

        mapping = self._order_mappings.get(system_order_id)
        if mapping is None:
            return

        execution = fill.execution
        now = pd.Timestamp.now(tz="UTC")
        exec_time = pd.Timestamp(execution.time, tz="UTC") if execution.time else now

        commission = 0.0
        if fill.commissionReport and fill.commissionReport.commission:
            commission = fill.commissionReport.commission

        _logger.info(
            "Order filled: %s %s %s @ %.4f (qty=%.2f)",
            system_order_id,
            mapping.side.name,
            mapping.symbol,
            execution.price,
            execution.shares,
        )
        self._publish(
            events.OrderFilled(
                ts_event=now,
                ts_broker=exec_time,
                associated_order_id=system_order_id,
                broker_fill_id=execution.execId,
                symbol=mapping.symbol,
                side=mapping.side,
                quantity_filled=execution.shares,
                fill_price=execution.price,
                commission=commission,
                exchange=execution.exchange or "IB",
            )
        )

        self._filled_quantities[system_order_id] = (
            self._filled_quantities.get(system_order_id, 0.0) + execution.shares
        )

        if trade.orderStatus.status == "Filled":
            self._cleanup_order(system_order_id)

    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract) -> None:
        system_order_id = self._ib_to_system_id.get(reqId)
        if system_order_id is None:
            return

        _logger.error(
            "IB error %d for order %s: %s", errorCode, system_order_id, errorString
        )
        now = pd.Timestamp.now(tz="UTC")

        if system_order_id in self._pending_cancellations:
            _logger.warning("Cancel rejected: %s - %s", system_order_id, errorString)
            self._pending_cancellations.discard(system_order_id)
            self._publish(
                events.OrderCancellationRejected(
                    ts_event=now,
                    ts_broker=now,
                    associated_order_id=system_order_id,
                    reason=errorString,
                )
            )
            return

        if system_order_id in self._pending_modifications:
            _logger.warning("Modify rejected: %s - %s", system_order_id, errorString)
            self._pending_modifications.pop(system_order_id, None)
            self._publish(
                events.OrderModificationRejected(
                    ts_event=now,
                    ts_broker=now,
                    associated_order_id=system_order_id,
                    reason=errorString,
                )
            )
            return

        if errorCode in (201, 202, 203, 321, 322):
            _logger.warning("Order rejected: %s - %s", system_order_id, errorString)
            self._publish(
                events.OrderSubmissionRejected(
                    ts_event=now,
                    ts_broker=now,
                    associated_order_id=system_order_id,
                    reason=errorString,
                )
            )
            self._cleanup_order(system_order_id)

    def _cleanup_order(self, system_order_id: uuid.UUID) -> None:
        mapping = self._order_mappings.pop(system_order_id, None)
        if mapping:
            self._ib_to_system_id.pop(mapping.trade.order.orderId, None)
        self._filled_quantities.pop(system_order_id, None)
        self._pending_cancellations.discard(system_order_id)
        self._pending_modifications.pop(system_order_id, None)

    def _create_ib_order(self, event: events.OrderSubmission, action: str):
        match event.order_type:
            case models.OrderType.MARKET:
                return MarketOrder(action, event.quantity)
            case models.OrderType.LIMIT:
                if event.limit_price is None:
                    return None
                return LimitOrder(action, event.quantity, event.limit_price)
            case models.OrderType.STOP:
                if event.stop_price is None:
                    return None
                return StopOrder(action, event.quantity, event.stop_price)
            case models.OrderType.STOP_LIMIT:
                if event.limit_price is None or event.stop_price is None:
                    return None
                return StopLimitOrder(
                    action, event.quantity, event.limit_price, event.stop_price
                )
            case _:
                return None

    def _make_contract(self, symbol: str):
        return make_contract(symbol, self._db_connection)
