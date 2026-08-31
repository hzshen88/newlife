"""Shared fixtures for the second-world (Hudson `ms`) test suite: builds
the vendored `ms` binary fresh once per test session (R1's exact command,
via `newlife.mechanisms.second_world.ms_binary`) and exposes the frozen
grid's parameters (R6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from newlife.mechanisms.second_world import ms_binary as _ms_binary
from newlife.mechanisms.second_world.ms_binary import parse_ms_stdout as parse_ms_stdout

VENDOR_ROOT = (
    Path(__file__).resolve().parents[2] / ".." / ".." / "vendor" / "ms"
).resolve()

NSAM = 4
THETA = 2.0
HOWMANY = 10

# The frozen grid (plan R6 / prereg § Fixed units and fixed sample).
SEED_TRIPLES = {
    "seedA": (3579, 27011, 59243),
    "seedB": (12345, 6789, 999),
    "seedC": (101, 202, 303),
}


@pytest.fixture(scope="session")
def ms_binary(tmp_path_factory) -> Path:
    build_dir = tmp_path_factory.mktemp("ms-build")
    binary = _ms_binary.build_ms(VENDOR_ROOT, build_dir / "ms")
    assert binary.is_file()
    return binary


def run_ms(ms_binary: Path, seeds: tuple[int, int, int], draw_log: Path) -> str:
    return _ms_binary.run_ms(ms_binary, NSAM, HOWMANY, THETA, seeds, draw_log)
