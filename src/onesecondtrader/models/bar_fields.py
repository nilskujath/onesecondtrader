from __future__ import annotations

import enum


class BarField(enum.Enum):
    """
    Enumeration of bar fields used as indicator inputs.

    | Value    | Semantics                          |
    |----------|------------------------------------|
    | `OPEN`   | Bar's opening value.               |
    | `HIGH`   | Bar's highest value.               |
    | `LOW`    | Bar's lowest value.                |
    | `CLOSE`  | Bar's closing value.               |
    | `VOLUME` | Bar's traded volume.               |
    """

    OPEN = enum.auto()
    HIGH = enum.auto()
    LOW = enum.auto()
    CLOSE = enum.auto()
    VOLUME = enum.auto()
