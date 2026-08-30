"""Read-only access to the five frozen expected JSON files (immutable data).

Checksums are pinned to the frozen v0.1a preregistration; the checksum test
fails the suite if a vendored copy drifts by a single byte.
"""

from __future__ import annotations

import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

EXPECTED_ROOT = Path(__file__).resolve().parent / "fixtures" / "expected"

EXPECTED_FIXTURE_NAMES = (
    "continuous_next_event.json",
    "coupled_mechanics_division.json",
    "effect_algebra_transfer.json",
    "execution_budget.json",
    "hook_authority.json",
)

# Frozen v0.1a preregistration (2026-08-30), environment lock section.
FROZEN_FIXTURE_SHA256 = {
    "execution_budget.json": "0e3127626a3ebe031be5a6ec157be93584fea0d25b528aef05175a99435a7759",
    "coupled_mechanics_division.json": "61c99228204f5fa4de6488dc7125d1f7f7df850c8bb41ca3defde3c3dfbe6e22",
    "hook_authority.json": "b4cfea020bb5f292ddccbffdcb57189de41c747ef1a88c2f85fc96bc3c615d63",
    "continuous_next_event.json": "44a66e143a6c4a31671150f533f9c1730a748f02b4fa9ce9912c29f1cfde655c",
    "effect_algebra_transfer.json": "4ee1098eefbef0a417714f829bf574c53f8cc18ab316dbc9b1542ea3ecdcee33",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fixture_hashes() -> dict[str, str]:
    return {name: sha256_file(EXPECTED_ROOT / name) for name in EXPECTED_FIXTURE_NAMES}


@lru_cache(maxsize=None)
def _load(name: str) -> str:
    if name not in EXPECTED_FIXTURE_NAMES:
        raise KeyError(f"unknown frozen fixture: {name}")
    return (EXPECTED_ROOT / name).read_text(encoding="utf-8")


def load_fixture(name: str) -> dict[str, Any]:
    return copy.deepcopy(json.loads(_load(name)))
