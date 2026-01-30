from __future__ import annotations

import enum


class OrderType(enum.Enum):
    """
    Enumeration of order execution types.

    | Value       | Semantics                                                   |
    |-------------|-------------------------------------------------------------|
    | LIMIT       | Executable only at the specified limit price or better.     |
    | MARKET      | Executable immediately at the best available market price.  |
    | STOP        | Becomes a market order once the stop price is reached.      |
    | STOP_LIMIT  | Becomes a limit order once the stop price is reached.       |
    """

    LIMIT = enum.auto()
    MARKET = enum.auto()
    STOP = enum.auto()
    STOP_LIMIT = enum.auto()
