"""The deliberately narrow canonicalization frozen by the preregistration."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


RUNTIME_TOP_LEVEL_KEYS = frozenset({"global_time", "__runtime__"})


def canonicalize(value: Any, *, remove_runtime_keys: bool = False) -> Any:
    if isinstance(value, float):
        return str(Decimal(str(value)))
    if isinstance(value, dict):
        items = value.items()
        if remove_runtime_keys:
            items = ((key, item) for key, item in items if key not in RUNTIME_TOP_LEVEL_KEYS)
        return {
            key: canonicalize(item, remove_runtime_keys=False)
            for key, item in sorted(items, key=lambda pair: pair[0])
        }
    if isinstance(value, list):
        return [canonicalize(item, remove_runtime_keys=False) for item in value]
    if isinstance(value, tuple):
        return [canonicalize(item, remove_runtime_keys=False) for item in value]
    return value


def canonical_state(state: dict[str, Any]) -> dict[str, Any]:
    return canonicalize(state, remove_runtime_keys=True)


def canonical_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return canonicalize(trace)


def canonical_bytes(value: Any, *, remove_runtime_keys: bool = False) -> bytes:
    normalized = canonicalize(value, remove_runtime_keys=remove_runtime_keys)
    return json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8")

