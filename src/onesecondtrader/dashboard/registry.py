from __future__ import annotations

import enum

from onesecondtrader.core.strategies import StrategyBase
from onesecondtrader.core.brokers import BrokerBase
from onesecondtrader.core.datafeeds import DatafeedBase
from onesecondtrader.core.models import ParamSpec


def _get_subclasses(base: type) -> dict[str, type]:
    result = {}
    for cls in base.__subclasses__():
        if not cls.__name__.startswith("_"):
            result[cls.__name__] = cls
        result.update(_get_subclasses(cls))
    return result


def get_strategies() -> dict[str, type[StrategyBase]]:
    return _get_subclasses(StrategyBase)


def get_brokers() -> dict[str, type[BrokerBase]]:
    return _get_subclasses(BrokerBase)


def get_datafeeds() -> dict[str, type[DatafeedBase]]:
    return _get_subclasses(DatafeedBase)


def get_param_schema(params: dict[str, ParamSpec]) -> list[dict]:
    schema = []
    for name, spec in params.items():
        param_info = {
            "name": name,
            "default": _serialize_value(spec.default),
            "type": _get_type_name(spec.default),
        }
        if spec.min is not None:
            param_info["min"] = spec.min
        if spec.max is not None:
            param_info["max"] = spec.max
        if spec.step is not None:
            param_info["step"] = spec.step
        choices = spec.resolved_choices
        if choices is not None:
            param_info["choices"] = [_serialize_value(c) for c in choices]  # type: ignore[assignment]
        schema.append(param_info)
    return schema


def _serialize_value(value) -> str | int | float | bool:
    if isinstance(value, enum.Enum):
        return value.name
    return value


def _get_type_name(value) -> str:
    if isinstance(value, enum.Enum):
        return "enum"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return "unknown"


def get_strategy_schema(name: str) -> dict | None:
    cls = get_strategies().get(name)
    if cls is None:
        return None
    return {
        "name": name,
        "parameters": get_param_schema(getattr(cls, "parameters", {})),
    }


def get_broker_schema(name: str) -> dict | None:
    cls = get_brokers().get(name)
    if cls is None:
        return None
    return {
        "name": name,
        "parameters": get_param_schema(getattr(cls, "parameters", {})),
    }


def get_datafeed_schema(name: str) -> dict | None:
    cls = get_datafeeds().get(name)
    if cls is None:
        return None
    return {
        "name": name,
        "parameters": get_param_schema(getattr(cls, "parameters", {})),
    }
