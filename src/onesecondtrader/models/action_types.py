from __future__ import annotations

import enum


class ActionType(enum.Enum):
    """
    Enumeration of trading action types.

    `ActionType` specifies the intent or purpose of an order from the strategy's perspective,
    describing what the order is meant to accomplish in terms of position management.

    | Value         | Semantics                                                                  |
    |---------------|----------------------------------------------------------------------------|
    | `ENTRY`       | Opens a new position (direction-agnostic).                                 |
    | `ENTRY_LONG`  | Opens a new long position.                                                 |
    | `ENTRY_SHORT` | Opens a new short position.                                                |
    | `EXIT`        | Closes an existing position (direction-agnostic).                          |
    | `EXIT_LONG`   | Closes an existing long position.                                          |
    | `EXIT_SHORT`  | Closes an existing short position.                                         |
    | `ADD`         | Increases the size of an existing position.                                |
    | `REDUCE`      | Decreases the size of an existing position without fully closing it.       |
    | `REVERSE`     | Closes the current position and opens a new one in the opposite direction. |
    """

    ENTRY = enum.auto()
    ENTRY_LONG = enum.auto()
    ENTRY_SHORT = enum.auto()
    EXIT = enum.auto()
    EXIT_LONG = enum.auto()
    EXIT_SHORT = enum.auto()
    ADD = enum.auto()
    REDUCE = enum.auto()
    REVERSE = enum.auto()
