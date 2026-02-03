from __future__ import annotations

import abc
import dataclasses
import enum
import uuid
from types import SimpleNamespace

import pandas as pd

from onesecondtrader import events, indicators, messaging, models


@dataclasses.dataclass
class ParamSpec:
    """
    Specification for a strategy parameter.

    Defines the default value and optional constraints for a configurable strategy parameter.
    Used to declare tunable parameters that can be overridden at strategy instantiation.

    | Field     | Type                                      | Semantics                                                    |
    |-----------|-------------------------------------------|--------------------------------------------------------------|
    | `default` | `int`, `float`, `str`, `bool`, or `Enum`  | Default value of the parameter.                              |
    | `min`     | `int`, `float`, or `None`                 | Minimum allowed value, if applicable.                        |
    | `max`     | `int`, `float`, or `None`                 | Maximum allowed value, if applicable.                        |
    | `step`    | `int`, `float`, or `None`                 | Step size for parameter sweeps, if applicable.               |
    | `choices` | `list` or `None`                          | Explicit list of allowed values, if applicable.              |
    """

    default: int | float | str | bool | enum.Enum
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    choices: list | None = None

    @property
    def resolved_choices(self) -> list | None:
        """
        Return the effective list of allowed values for this parameter.

        If `choices` is explicitly set, returns that list.
        If `default` is an enum member, returns all members of that enum type.
        Otherwise, returns `None`.
        """
        if self.choices is not None:
            return self.choices
        if isinstance(self.default, enum.Enum):
            return list(type(self.default))
        return None


@dataclasses.dataclass
class OrderRecord:
    """
    Internal record of an order submitted by a strategy.

    Tracks the state of an order from submission through fill or cancellation.

    | Field             | Type               | Semantics                                           |
    |-------------------|--------------------|-----------------------------------------------------|
    | `order_id`        | `uuid.UUID`        | System-assigned unique identifier for the order.    |
    | `symbol`          | `str`              | Identifier of the traded instrument.                |
    | `order_type`      | `models.OrderType` | Execution constraint of the order.                  |
    | `side`            | `models.TradeSide` | Direction of the trade.                             |
    | `quantity`        | `float`            | Requested order quantity.                           |
    | `limit_price`     | `float` or `None`  | Limit price, if applicable to the order type.       |
    | `stop_price`      | `float` or `None`  | Stop price, if applicable to the order type.        |
    | `signal`          | `str` or `None`    | Optional signal name associated with the order.     |
    | `filled_quantity` | `float`            | Cumulative quantity filled for this order.          |
    """

    order_id: uuid.UUID
    symbol: str
    order_type: models.OrderType
    side: models.TradeSide
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None
    signal: str | None = None
    filled_quantity: float = 0.0


@dataclasses.dataclass
class FillRecord:
    """
    Internal record of a fill received by a strategy.

    Captures execution details for a single fill event.

    | Field        | Type               | Semantics                                                 |
    |--------------|--------------------|-----------------------------------------------------------|
    | `fill_id`    | `uuid.UUID`        | System-assigned unique identifier for the fill.           |
    | `order_id`   | `uuid.UUID`        | Identifier of the order associated with the fill.         |
    | `symbol`     | `str`              | Identifier of the traded instrument.                      |
    | `side`       | `models.TradeSide` | Trade direction of the executed quantity.                 |
    | `quantity`   | `float`            | Quantity executed in this fill.                           |
    | `price`      | `float`            | Execution price of the fill.                              |
    | `commission` | `float`            | Commission or fee associated with the fill.               |
    | `ts_event`   | `pd.Timestamp`     | Timestamp at which the fill was observed by the strategy. |
    """

    fill_id: uuid.UUID
    order_id: uuid.UUID
    symbol: str
    side: models.TradeSide
    quantity: float
    price: float
    commission: float
    ts_event: pd.Timestamp


class StrategyBase(messaging.Subscriber, abc.ABC):
    """
    Abstract base class for trading strategies.

    A strategy subscribes to market data and order events, maintains position state,
    and submits orders through the event bus. Subclasses implement `on_bar` to define
    trading logic and optionally override `setup` to register indicators.

    Class Attributes:
        name:
            Human-readable name of the strategy.
        symbols:
            List of instrument symbols the strategy trades.
        parameters:
            Dictionary mapping parameter names to their specifications.
    """

    name: str = ""
    symbols: list[str] = []
    parameters: dict[str, ParamSpec] = {}

    def __init__(self, event_bus: messaging.EventBus, **overrides) -> None:
        """
        Initialize the strategy and start event processing.

        Parameters:
            event_bus:
                Event bus used for subscribing to and publishing events.
            **overrides:
                Parameter values to override defaults defined in `parameters`.
        """
        super().__init__(event_bus)

        for name, spec in self.parameters.items():
            value = overrides.get(name, spec.default)
            setattr(self, name, value)

        self._subscribe(
            events.market.BarReceived,
            events.responses.OrderAccepted,
            events.responses.ModificationAccepted,
            events.responses.CancellationAccepted,
            events.responses.OrderRejected,
            events.responses.ModificationRejected,
            events.responses.CancellationRejected,
            events.orders.FillEvent,
            events.orders.OrderExpired,
        )

        self._current_symbol: str = ""
        self._current_ts: pd.Timestamp = pd.Timestamp.now(tz="UTC")
        self._indicators: list[indicators.IndicatorBase] = []

        self._fills: dict[str, list[FillRecord]] = {}
        self._positions: dict[str, float] = {}
        self._avg_prices: dict[str, float] = {}
        self._pending_orders: dict[uuid.UUID, OrderRecord] = {}
        self._submitted_orders: dict[uuid.UUID, OrderRecord] = {}
        self._submitted_modifications: dict[uuid.UUID, OrderRecord] = {}
        self._submitted_cancellations: dict[uuid.UUID, OrderRecord] = {}

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

    def add_indicator(self, ind: indicators.IndicatorBase) -> indicators.IndicatorBase:
        """
        Register an indicator with the strategy.

        Registered indicators are automatically updated on each bar event.

        Parameters:
            ind:
                Indicator instance to register.

        Returns:
            The registered indicator instance.
        """
        self._indicators.append(ind)
        return ind

    @property
    def position(self) -> float:
        """
        Return the current position for the active symbol.

        The active symbol is set by the most recently processed bar event.
        """
        return self._positions.get(self._current_symbol, 0.0)

    @property
    def avg_price(self) -> float:
        """
        Return the average entry price for the current position on the active symbol.

        Returns zero if there is no open position.
        """
        return self._avg_prices.get(self._current_symbol, 0.0)

    def submit_order(
        self,
        order_type: models.OrderType,
        side: models.TradeSide,
        quantity: float,
        limit_price: float | None = None,
        stop_price: float | None = None,
        action: models.ActionType | None = None,
        signal: str | None = None,
    ) -> uuid.UUID:
        """
        Submit a new order for the active symbol.

        Parameters:
            order_type:
                Execution constraint of the order.
            side:
                Direction of the trade.
            quantity:
                Requested order quantity.
            limit_price:
                Limit price, if applicable to the order type.
            stop_price:
                Stop price, if applicable to the order type.
            action:
                Intent of the order from the strategy's perspective (e.g., entry, exit).
            signal:
                Optional signal name associated with the order.

        Returns:
            System-assigned unique identifier for the submitted order.
        """
        order_id = uuid.uuid4()

        event = events.requests.OrderSubmissionRequest(
            ts_event_ns=int(self._current_ts.value),
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

        order = OrderRecord(
            order_id=order_id,
            symbol=self._current_symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
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
        """
        Submit a modification request for a pending order.

        Parameters:
            order_id:
                Identifier of the order to modify.
            quantity:
                Updated order quantity, or `None` to keep unchanged.
            limit_price:
                Updated limit price, or `None` to keep unchanged.
            stop_price:
                Updated stop price, or `None` to keep unchanged.

        Returns:
            `True` if the modification request was submitted, `False` if the order was not found.
        """
        original_order = self._pending_orders.get(order_id)
        if original_order is None:
            return False

        event = events.requests.OrderModificationRequest(
            ts_event_ns=int(self._current_ts.value),
            system_order_id=order_id,
            symbol=original_order.symbol,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
        )

        modified_order = OrderRecord(
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
            signal=original_order.signal,
            filled_quantity=original_order.filled_quantity,
        )

        self._submitted_modifications[order_id] = modified_order
        self._publish(event)
        return True

    def submit_cancellation(self, order_id: uuid.UUID) -> bool:
        """
        Submit a cancellation request for a pending order.

        Parameters:
            order_id:
                Identifier of the order to cancel.

        Returns:
            `True` if the cancellation request was submitted, `False` if the order was not found.
        """
        original_order = self._pending_orders.get(order_id)
        if original_order is None:
            return False

        event = events.requests.OrderCancellationRequest(
            ts_event_ns=int(self._current_ts.value),
            system_order_id=order_id,
            symbol=original_order.symbol,
        )

        self._submitted_cancellations[order_id] = original_order
        self._publish(event)
        return True

    def _on_event(self, event: events.EventBase) -> None:
        match event:
            case events.market.BarReceived() as bar_event:
                self._on_bar_received(bar_event)
            case events.responses.OrderAccepted() as accepted:
                self._on_order_submission_accepted(accepted)
            case events.responses.ModificationAccepted() as accepted:
                self._on_order_modification_accepted(accepted)
            case events.responses.CancellationAccepted() as accepted:
                self._on_order_cancellation_accepted(accepted)
            case events.responses.OrderRejected() as rejected:
                self._on_order_submission_rejected(rejected)
            case events.responses.ModificationRejected() as rejected:
                self._on_order_modification_rejected(rejected)
            case events.responses.CancellationRejected() as rejected:
                self._on_order_cancellation_rejected(rejected)
            case events.orders.FillEvent() as filled:
                self._on_order_filled(filled)
            case events.orders.OrderExpired() as expired:
                self._on_order_expired(expired)
            case _:
                return

    def _on_bar_received(self, event: events.market.BarReceived) -> None:
        if event.symbol not in self.symbols:
            return
        if event.bar_period != self.bar_period:  # type: ignore[attr-defined]
            return

        self._current_symbol = event.symbol
        self._current_ts = pd.Timestamp(event.ts_event_ns, tz="UTC")

        for ind in self._indicators:
            ind.update(event)

        self._emit_processed_bar(event)
        self.on_bar(event)

    def _emit_processed_bar(self, event: events.market.BarReceived) -> None:
        ohlcv_names = {"OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"}

        indicator_values = {
            f"{ind.plot_at:02d}_{ind.name}": ind.latest(event.symbol)
            for ind in self._indicators
            if ind.name not in ohlcv_names
        }

        processed_bar = events.market.BarProcessed(
            ts_event_ns=event.ts_event_ns,
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
        self, event: events.responses.OrderAccepted
    ) -> None:
        order = self._submitted_orders.pop(event.associated_order_id, None)
        if order is not None:
            self._pending_orders[event.associated_order_id] = order

    def _on_order_modification_accepted(
        self, event: events.responses.ModificationAccepted
    ) -> None:
        modified_order = self._submitted_modifications.pop(
            event.associated_order_id, None
        )
        if modified_order is not None:
            self._pending_orders[event.associated_order_id] = modified_order

    def _on_order_cancellation_accepted(
        self, event: events.responses.CancellationAccepted
    ) -> None:
        self._submitted_cancellations.pop(event.associated_order_id, None)
        self._pending_orders.pop(event.associated_order_id, None)

    def _on_order_submission_rejected(
        self, event: events.responses.OrderRejected
    ) -> None:
        self._submitted_orders.pop(event.associated_order_id, None)

    def _on_order_modification_rejected(
        self, event: events.responses.ModificationRejected
    ) -> None:
        self._submitted_modifications.pop(event.associated_order_id, None)

    def _on_order_cancellation_rejected(
        self, event: events.responses.CancellationRejected
    ) -> None:
        self._submitted_cancellations.pop(event.associated_order_id, None)

    def _on_order_filled(self, event: events.orders.FillEvent) -> None:
        order = self._pending_orders.get(event.associated_order_id)
        if order:
            order.filled_quantity += event.quantity_filled
            if order.filled_quantity >= order.quantity:
                self._pending_orders.pop(event.associated_order_id)

        fill = FillRecord(
            fill_id=event.fill_id,
            order_id=event.associated_order_id,
            symbol=event.symbol,
            side=event.side,
            quantity=event.quantity_filled,
            price=event.fill_price,
            commission=event.commission,
            ts_event=pd.Timestamp(event.ts_event_ns, tz="UTC"),
        )

        self._fills.setdefault(event.symbol, []).append(fill)
        self._update_position(event)

    def _update_position(self, event: events.orders.FillEvent) -> None:
        symbol = event.symbol
        fill_qty = event.quantity_filled
        fill_price = event.fill_price

        signed_qty = 0.0
        match event.side:
            case models.TradeSide.BUY:
                signed_qty = fill_qty
            case models.TradeSide.SELL:
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

    def _on_order_expired(self, event: events.orders.OrderExpired) -> None:
        self._pending_orders.pop(event.associated_order_id, None)

    def setup(self) -> None:
        """
        Hook for subclasses to register indicators and perform initialization.

        Called at the end of `__init__`. Override this method to register indicators
        using `add_indicator` without needing to override `__init__`.
        """
        pass

    @abc.abstractmethod
    def on_bar(self, event: events.market.BarReceived) -> None:
        """
        Handle a bar event for a subscribed symbol.

        Called after all registered indicators have been updated. Subclasses implement
        this method to define trading logic.

        Parameters:
            event:
                Bar event containing OHLCV data for the current bar.
        """
        pass
