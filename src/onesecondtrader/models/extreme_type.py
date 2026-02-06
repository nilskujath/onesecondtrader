from __future__ import annotations

import enum


class ExtremeType(enum.Enum):
    """
    Enumeration of extreme types for n-period extreme calculations.

    | Value | Semantics                          |
    |-------|-------------------------------------|
    | `MIN` | Minimum value over the period.      |
    | `MAX` | Maximum value over the period.      |
    """

    MIN = enum.auto()
    MAX = enum.auto()
