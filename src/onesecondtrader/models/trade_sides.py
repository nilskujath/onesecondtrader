from __future__ import annotations

import enum


class TradeSide(enum.Enum):
    """
    Enumeration of trade direction.

    `OrderSide` specifies the direction of change applied to the (net) signed position
    quantity from the perspective of the trading account.

    | Value | Semantics                                      |
    |-------|------------------------------------------------|
    | BUY   | Increases the signed position quantity.        |
    | SELL  | Decreases the signed position quantity.        |
    """

    BUY = enum.auto()
    SELL = enum.auto()
