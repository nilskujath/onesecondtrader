from __future__ import annotations

import enum


class ActionType(enum.Enum):
    """
    Enumeration of trading action types.

    `ActionType` specifies the intent or purpose of an order from the strategy's perspective,
    describing what the order is meant to accomplish in terms of position management.

    | Value                       | Semantics                                                            |
    |-----------------------------|----------------------------------------------------------------------|
    | `ENTRY_LONG`                | Opens a new long position.                                           |
    | `ENTRY_SHORT`               | Opens a new short position.                                          |
    | `EXIT_LONG`                 | Closes an existing long position.                                    |
    | `EXIT_SHORT`                | Closes an existing short position.                                   |
    | `ADD_LONG`                  | Increases the size of an existing long position.                     |
    | `ADD_SHORT`                 | Increases the size of an existing short position.                    |
    | `REDUCE_LONG`               | Decreases the size of an existing long position without closing it.  |
    | `REDUCE_SHORT`              | Decreases the size of an existing short position without closing it. |
    | `FLATTEN`                   | Closes all open positions regardless of direction.                   |
    | `STOP_LOSS_LONG`            | Exits a long position due to a stop-loss trigger.                    |
    | `STOP_LOSS_SHORT`           | Exits a short position due to a stop-loss trigger.                   |
    | `TAKE_PROFIT_LONG`          | Exits a long position due to a take-profit trigger.                  |
    | `TAKE_PROFIT_SHORT`         | Exits a short position due to a take-profit trigger.                 |
    | `PARTIAL_TAKE_PROFIT_LONG`  | Reduces a long position to lock in partial profits.                  |
    | `PARTIAL_TAKE_PROFIT_SHORT` | Reduces a short position to lock in partial profits.                 |
    """

    ENTRY_LONG = enum.auto()
    ENTRY_SHORT = enum.auto()

    EXIT_LONG = enum.auto()
    EXIT_SHORT = enum.auto()

    ADD_LONG = enum.auto()
    ADD_SHORT = enum.auto()

    REDUCE_LONG = enum.auto()
    REDUCE_SHORT = enum.auto()

    FLATTEN = enum.auto()

    STOP_LOSS_LONG = enum.auto()
    STOP_LOSS_SHORT = enum.auto()

    TAKE_PROFIT_LONG = enum.auto()
    TAKE_PROFIT_SHORT = enum.auto()

    PARTIAL_TAKE_PROFIT_LONG = enum.auto()
    PARTIAL_TAKE_PROFIT_SHORT = enum.auto()
