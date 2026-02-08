"""
API endpoint for discovering available indicator classes and their parameters.
"""

from __future__ import annotations

import enum
import inspect

from fastapi import APIRouter

from onesecondtrader.dashboard.indicators_util import get_registered_indicators

router = APIRouter(prefix="/api", tags=["indicators"])

OHLCV_NAMES = {"Open", "High", "Low", "Close", "Volume"}
SKIP_PARAMS = {"self", "max_history", "kwargs"}


def _build_param_specs(cls, class_name, registry, *, _nested=False):
    """Build parameter spec dicts for an indicator class.

    When *_nested* is True (sub-parameter introspection), ``indicator_class``
    type params are skipped to avoid infinite recursion.
    """
    sig = inspect.signature(cls.__init__)

    # First pass: identify indicator_class params and their linked kwargs dicts
    indicator_class_params = {}
    linked_kwargs_names = set()
    for pname, param in sig.parameters.items():
        ann = param.annotation
        ann_str = str(ann) if ann is not inspect.Parameter.empty else ""
        if "type[" in ann_str:
            # Look for explicit X_kwargs parameter
            kw_name = f"{pname}_kwargs"
            if kw_name in sig.parameters:
                indicator_class_params[pname] = kw_name
                linked_kwargs_names.add(kw_name)
            else:
                # Fall back to source_kwargs (legacy pattern)
                indicator_class_params[pname] = "source_kwargs"
                linked_kwargs_names.add("source_kwargs")

    # Dynamically skip linked kwargs + VAR_KEYWORD source_kwargs
    skip = SKIP_PARAMS | linked_kwargs_names

    params = []
    for pname, param in sig.parameters.items():
        if pname in skip:
            continue
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        default = param.default
        if default is inspect.Parameter.empty:
            default = None

        ann = param.annotation
        ann_str = str(ann) if ann is not inspect.Parameter.empty else ""
        if "type[" in ann_str:
            if _nested:
                continue
            choices = sorted(name for name in registry if name != class_name)
            kwargs_name = indicator_class_params.get(pname, "source_kwargs")
            params.append(
                {
                    "name": pname,
                    "default": "Close",
                    "type": "indicator_class",
                    "choices": choices,
                    "source_params": {
                        name: _build_param_specs(
                            registry[name], name, registry, _nested=True
                        )
                        for name in choices
                    },
                    "kwargs_name": kwargs_name,
                }
            )
            continue

        if isinstance(default, enum.Enum):
            enum_cls = type(default)
            choices = [e.name for e in enum_cls]
            params.append(
                {
                    "name": pname,
                    "default": default.name,
                    "type": "enum",
                    "choices": choices,
                }
            )
        elif isinstance(default, bool):
            params.append({"name": pname, "default": default, "type": "bool"})
        elif isinstance(default, int):
            params.append({"name": pname, "default": default, "type": "int"})
        elif isinstance(default, float):
            params.append({"name": pname, "default": default, "type": "float"})
        else:
            params.append(
                {
                    "name": pname,
                    "default": str(default) if default is not None else None,
                    "type": "str",
                }
            )

    return params


@router.get("/indicators")
async def api_indicators() -> dict:
    """Return available indicator classes with their parameter specs."""
    registry = get_registered_indicators()
    indicators = []
    for class_name, cls in sorted(registry.items()):
        if class_name in OHLCV_NAMES:
            continue

        params = _build_param_specs(cls, class_name, registry)
        indicators.append({"class_name": class_name, "params": params})

    return {"indicators": indicators}
