"""
This module provides the event bus for managing event-driven communication between
 the trading infrastructure's components via a publish-subscribe messaging pattern.
"""

import collections
import inspect
import logging
import threading
from collections.abc import Callable
from onesecondtrader.messaging import events
from onesecondtrader.monitoring import console


class EventBus:
    # noinspection PyTypeChecker
    """
    Event bus for managing event-driven communication between the trading
     infrastructure's components via a publish-subscribe messaging pattern.
    Supports inheritance-based subscriptions where handlers subscribed to a parent event
     type will receive events of child types.
    Each subscription can include an optional filter function to receive only specific
     events of a given type (e.g. filtering `IncomingBar` events for a specific symbol).

    Examples:
        >>> # Import necessary modules
        >>> import pandas as pd
        >>> from onesecondtrader.messaging.eventbus import EventBus
        >>> from onesecondtrader.messaging import events
        >>> from onesecondtrader.core import models

        >>> # Instantiate event bus
        >>> event_bus = EventBus()

        >>> # Create a dummy handler that simply prints the symbol of the received event
        >>> def dummy_handler(incoming_bar_event: events.Market.IncomingBar):
        ...     print(f"Received: {incoming_bar_event.symbol}")

        >>> # Subscribe to IncomingBar events whose symbol is AAPL
        >>> event_bus.subscribe(
        ...     events.Market.IncomingBar,
        ...     dummy_handler,
        ...     lambda event: event.symbol == "AAPL" # Lambda filter function
        ... )

        >>> # Create events to publish
        >>> aapl_event = events.Market.IncomingBar(
        ...     ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
        ...     symbol="AAPL",
        ...     bar=models.Bar(
        ...         open=100.0, high=101.0, low=99.0,
        ...         close=100.5, volume=1000
        ...     )
        ... )
        >>> googl_event = events.Market.IncomingBar(
        ...     ts_event=pd.Timestamp("2023-01-01", tz="UTC"),
        ...     symbol="GOOGL",
        ...     bar=models.Bar(
        ...         open=2800.0, high=2801.0, low=2799.0,
        ...         close=2800.5, volume=500
        ...     )
        ... )

        >>> # Publish events - only AAPL passes filter and will be printed
        >>> event_bus.publish(aapl_event)
        Received: AAPL
        >>> event_bus.publish(googl_event)

        >>> # Unsubscribe the dummy handler
        >>> event_bus.unsubscribe(events.Market.IncomingBar, dummy_handler)

        >>> # Publish again - no handler receives it (warning will be logged)
        >>> event_bus.publish(aapl_event)  # doctest: +SKIP
        WARNING:root:Published IncomingBar but no subscribers exist - check event wiring
    """

    def __init__(self) -> None:
        """
        Initializes the event bus with optimized data structures for high-performance
        event publishing.

        Attributes:
            self._handlers (collections.defaultdict): Direct storage mapping event types
                 to handler lists
            self._publish_cache (dict): Pre-computed cache for O(1) publish operations
            self._lock (threading.Lock): Single lock for all operations
                (subscribe/unsubscribe are rare)
            self._sequence_number (int): Sequence number counter for events
        """
        self._handlers: dict[
            type[events.Base.Event],
            list[
                tuple[
                    Callable[[events.Base.Event], None],
                    Callable[[events.Base.Event], bool],
                ]
            ],
        ] = collections.defaultdict(list)

        self._publish_cache: dict[
            type[events.Base.Event],
            list[
                tuple[
                    Callable[[events.Base.Event], None],
                    Callable[[events.Base.Event], bool],
                ]
            ],
        ] = {}

        self._lock: threading.Lock = threading.Lock()
        self._sequence_number: int = -1

        self._rebuild_cache()

    def subscribe(
        self,
        event_type: type[events.Base.Event],
        event_handler: Callable[[events.Base.Event], None],
        event_filter: Callable[[events.Base.Event], bool] | None = None,
    ) -> None:
        """
        The `subscribe` method registers an event handler for event messages of a
         specified type and all its subtypes (expressed as subclasses in the event
          dataclass hierarchy, so-called inheritance-based subscription).
        When an event of that type or any subtype is published, the handler will be
         invoked if the associated `event_filter` returns `True` for that event
         instance.
        A given handler can only be subscribed once per event type.
        If the handler is already subscribed to the given event type
         —regardless of the filter function—
        the subscription attempt is ignored and a warning is logged.

        Arguments:
            event_type (type[events.Base.Event]): Type of the event to subscribe to,
             must be a subclass of `events.Base.Event`.
            event_handler (Callable[events.Base.Event, None]): Function to call when an
                 event of the given type is published.
                This callable must accept a single argument of type `events.Base.Event`
                 (or its subclass).
            event_filter (Callable[[events.Base.Event], bool] | None): Function to
                 determine whether to call the event handler for a given event.
                Should accept one event and return `True` to handle or `False` to
                 ignore.
                Defaults to `None`, which creates a filter that always returns `True`
                 (i.e. always call the event handler).
        """

        if not issubclass(event_type, events.Base.Event):
            console.logger.error(
                f"Invalid subscription attempt: event_type must be a subclass of "
                f"Event, got {type(event_type).__name__}"
            )
            return

        if not callable(event_handler):
            console.logger.error(
                f"Invalid subscription attempt: event_handler must be callable, "
                f"got {type(event_handler).__name__}"
            )
            return

        if event_filter is None:

            def event_filter(event: events.Base.Event) -> bool:
                return True

        if not callable(event_filter):
            console.logger.error(
                f"Invalid subscription attempt: event_filter must be callable, "
                f"got {type(event_filter).__name__}"
            )
            return

        is_valid, error_msg = self._validate_filter_signature(event_filter)
        if not is_valid:
            console.logger.error(f"Invalid subscription attempt: {error_msg}")
            return

        with self._lock:
            if any(
                event_handler == existing_handler
                for existing_handler, _ in self._handlers[event_type]
            ):
                console.logger.warning(
                    f"Duplicate subscription attempt: event_handler was already "
                    f"subscribed to {event_type.__name__}"
                )
                return

            self._handlers[event_type].append((event_handler, event_filter))

            self._rebuild_cache()

            handler_name = getattr(event_handler, "__name__", "<lambda>")
            console.logger.info(f"Subscribed {handler_name} to {event_type.__name__}.")

    def unsubscribe(
        self,
        event_type: type[events.Base.Event],
        event_handler: Callable[[events.Base.Event], None],
    ) -> None:
        """
        The `unsubscribe` method removes an event handler from the subscribers list for
         the specified event type.
        If the event handler is not subscribed to the given event type, the
         unsubscription attempt is ignored and a warning is logged.
        After removing the event handler, the event type may have an empty subscribers
         list but remains in the `subscribers` dictionary.

        Arguments:
            event_type (type[events.Base.Event]): Type of the event to unsubscribe from,
                 must be a subclass of `events.Base.Event`.
            event_handler (Callable[events.Base.Event, None]): Event handler to remove
                 from the subscribers list (this will also remove the associated filter
                 function).
        """
        if not issubclass(event_type, events.Base.Event):
            console.logger.error(
                f"Invalid unsubscription attempt: event_type must be a subclass of "
                f"Event, got {type(event_type).__name__}"
            )
            return

        if not callable(event_handler):
            console.logger.error(
                f"Invalid unsubscription attempt: callback must be callable, "
                f"got {type(event_handler).__name__}"
            )
            return

        with self._lock:
            if event_type not in self._handlers:
                console.logger.warning(
                    f"Attempted to unsubscribe from {event_type.__name__}, "
                    f"but no subscribers exist"
                )
                return

            current_handlers = self._handlers[event_type]
            new_handlers = [
                (existing_handler, existing_filter)
                for existing_handler, existing_filter in current_handlers
                if existing_handler != event_handler
            ]

            removed_count = len(current_handlers) - len(new_handlers)
            if removed_count == 0:
                handler_name = getattr(event_handler, "__name__", "<lambda>")
                console.logger.warning(
                    f"Attempted to unsubscribe {handler_name} from "
                    f"{event_type.__name__}, but it was not subscribed"
                )
                return

            if new_handlers:
                self._handlers[event_type] = new_handlers
            else:
                # Clean up empty lists
                del self._handlers[event_type]

            self._rebuild_cache()

            handler_name = getattr(event_handler, "__name__", "<lambda>")
            console.logger.info(
                f"Unsubscribed {handler_name} from "
                f"{event_type.__name__} (removed {removed_count} subscription(s))"
            )

    def publish(self, event: events.Base.Event) -> None:
        """
        The `publish` method delivers the event to all handlers subscribed to the
         event's type or any of its parent types (inheritance-based subscription).
        Handlers are only called if their filter function returns True for this event.
        Handlers are called synchronously in the order they were subscribed.

        This method uses a pre-computed handler cache for O(1) lookup performance
        and runs without locks for maximum concurrency.

        Arguments:
            event (events.Base.Event): Event to publish. Must be an instance of
                 `events.Base.Event` or one of its subclasses.
        """
        if not isinstance(event, events.Base.Event):
            console.logger.error(
                f"Invalid publish attempt: event must be an instance of Event, "
                f"got {type(event).__name__}"
            )
            return

        object.__setattr__(
            event, "event_bus_sequence_number", self._set_sequence_number()
        )

        event_type: type[events.Base.Event] = type(event)

        handlers = self._publish_cache.get(event_type, [])

        if not handlers:
            console.logger.warning(
                f"Published {event_type.__name__} but no subscribers exist - "
                f"check event wiring"
            )
            return

        delivered_count = 0
        for event_handler, event_filter in handlers:
            try:
                should_handle = event_filter(event)

                if not isinstance(should_handle, bool):
                    handler_name = getattr(event_handler, "__name__", "<lambda>")
                    console.logger.warning(
                        f"Filter for handler {handler_name} returned "
                        f"{type(should_handle).__name__}, expected bool. "
                        f"Treating as False."
                    )
                    should_handle = False

            except TypeError as type_error:
                handler_name = getattr(event_handler, "__name__", "<lambda>")
                if "takes" in str(type_error) and "positional argument" in str(
                    type_error
                ):
                    console.logger.error(
                        f"Filter for handler {handler_name} has wrong signature: "
                        f"{type_error}"
                    )
                else:
                    console.logger.exception(
                        f"Filter function for handler {handler_name} failed "
                        f"processing {event_type.__name__}: {type_error}"
                    )
                continue
            except Exception as filter_exception:
                handler_name = getattr(event_handler, "__name__", "<lambda>")
                console.logger.exception(
                    f"Filter function for handler {handler_name} failed "
                    f"processing {event_type.__name__}: {filter_exception}"
                )
                continue

            if should_handle:
                try:
                    event_handler(event)
                    delivered_count += 1
                except Exception as handler_exception:
                    handler_name = getattr(event_handler, "__name__", "<lambda>")
                    console.logger.exception(
                        f"Handler {handler_name} failed processing "
                        f"{event_type.__name__}: {handler_exception}"
                    )

        if delivered_count == 0:
            console.logger.warning(
                f"Published {event_type.__name__} but no handlers received it - "
                f"all {len(handlers)} handler(s) filtered out the event"
            )
        else:
            # Conditional debug logging to avoid string formatting overhead
            if console.logger.isEnabledFor(logging.DEBUG):
                console.logger.debug(
                    f"Published {event_type.__name__} to {delivered_count} handler(s)"
                )

    @staticmethod
    def _validate_filter_signature(
        event_filter: Callable[[events.Base.Event], bool],
    ) -> tuple[bool, str | None]:
        """
        Validate that filter function has the correct signature.

        A valid filter function must:
        - Accept exactly 1 parameter (the event)
        - Not use *args or **kwargs
        - Optionally return bool (if type annotated)

        Arguments:
            event_filter (Callable): The filter function to validate

        Returns:
            tuple[bool, str | None]: (is_valid, error_message)
                is_valid: True if signature is valid, False otherwise
                error_message: Description of the issue if invalid, None if valid
        """
        try:
            sig = inspect.signature(event_filter)
            params = list(sig.parameters.values())

            if len(params) != 1:
                return (
                    False,
                    f"Filter must accept exactly 1 parameter, got {len(params)}",
                )

            param = params[0]
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                return (
                    False,
                    "Filter cannot use *args - must accept exactly 1 event parameter",
                )
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                return (
                    False,
                    "Filter cannot use **kwargs - must accept exactly 1 event "
                    "parameter",
                )

            if sig.return_annotation is not inspect.Parameter.empty:
                if sig.return_annotation is not bool:
                    return (
                        False,
                        f"Filter return type should be bool, got "
                        f"{sig.return_annotation}",
                    )

            return True, None

        except Exception as e:
            return False, f"Could not inspect filter signature: {e}"

    def _set_sequence_number(self) -> int:
        """
        Increment and return the event bus sequence number in a thread-safe manner.
        """
        with self._lock:
            self._sequence_number += 1
            return self._sequence_number

    @staticmethod
    def _get_all_concrete_event_types() -> list[type[events.Base.Event]]:
        """
        Dynamically discover all concrete event types from the events module.
        Automatically adapts to namespace changes without code modifications.

        Returns:
            list[type[events.Base.Event]]: List of concrete event classes that can be
                instantiated and published.
        """
        concrete_types = []

        for attr_name in dir(events):
            if attr_name.startswith("_"):
                continue

            attr = getattr(events, attr_name)

            if not inspect.isclass(attr) or attr_name == "Base":
                continue

            for member_name, member_obj in inspect.getmembers(attr, inspect.isclass):
                if (
                    issubclass(member_obj, events.Base.Event)
                    and member_obj != events.Base.Event
                    and not inspect.isabstract(member_obj)
                ):
                    concrete_types.append(member_obj)

        return concrete_types

    def _rebuild_cache(self) -> None:
        """
        Rebuild the pre-computed publish cache for all concrete event types.
        This method should be called whenever subscriptions change.
        """
        new_cache = {}
        concrete_event_types = self._get_all_concrete_event_types()

        for concrete_event_type in concrete_event_types:
            handlers = []
            seen_handler_ids = set()

            for handler_type, handler_list in self._handlers.items():
                if issubclass(concrete_event_type, handler_type):
                    for handler, filter_func in handler_list:
                        handler_id = id(handler)
                        if handler_id not in seen_handler_ids:
                            handlers.append((handler, filter_func))
                            seen_handler_ids.add(handler_id)

            if handlers:
                new_cache[concrete_event_type] = handlers

        self._publish_cache = new_cache

        if console.logger.isEnabledFor(logging.DEBUG):
            console.logger.debug(
                f"Publish cache rebuilt: {len(new_cache)} event types cached, "
                f"total handlers: "
                f"{sum(len(handlers) for handlers in new_cache.values())}"
            )
