from __future__ import annotations

import enum


class ExtremeType(enum.Enum):
    """
    Enumeration of extreme types.

    | Value | Semantics           |
    |-------|---------------------|
    | `MIN` | Minimum value.      |
    | `MAX` | Maximum value.      |
    """

    MIN = enum.auto()
    MAX = enum.auto()
