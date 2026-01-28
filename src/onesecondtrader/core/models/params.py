from __future__ import annotations

import dataclasses
import enum


@dataclasses.dataclass
class ParamSpec:
    default: int | float | str | bool | enum.Enum
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    choices: list | None = None

    @property
    def resolved_choices(self) -> list | None:
        if self.choices is not None:
            return self.choices
        if isinstance(self.default, enum.Enum):
            return list(type(self.default))
        return None
