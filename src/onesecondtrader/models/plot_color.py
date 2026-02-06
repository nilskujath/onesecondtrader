from __future__ import annotations

import enum


class PlotColor(enum.Enum):
    """
    Enumeration of indicator plot colors.

    | Value       | Semantics                          |
    |-------------|------------------------------------|
    | `BLACK`     | Black line color.                  |
    | `RED`       | Red line color.                    |
    | `BLUE`      | Blue line color.                   |
    | `GREEN`     | Green line color.                  |
    | `ORANGE`    | Orange line color.                 |
    | `PURPLE`    | Purple line color.                 |
    | `CYAN`      | Cyan line color.                   |
    | `MAGENTA`   | Magenta line color.                |
    | `YELLOW`    | Yellow line color.                 |
    | `WHITE`     | White line color.                  |
    | `TEAL`      | Teal line color.                   |
    """

    BLACK = enum.auto()
    RED = enum.auto()
    BLUE = enum.auto()
    GREEN = enum.auto()
    ORANGE = enum.auto()
    PURPLE = enum.auto()
    CYAN = enum.auto()
    MAGENTA = enum.auto()
    YELLOW = enum.auto()
    WHITE = enum.auto()
    TEAL = enum.auto()
