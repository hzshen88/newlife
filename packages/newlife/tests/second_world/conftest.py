"""Shared fixtures for the second-world (Hudson `ms`) test suite: builds
the vendored `ms` binary fresh once per test session (R1's exact command)
and exposes the frozen grid's parameters (R6)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

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
    binary = build_dir / "ms"
    cmd = [
        "cc",
        "-O2",
        "-ffp-contract=off",
        "-std=gnu89",
        "-Wno-error=implicit-function-declaration",
        "-Wno-error=implicit-int",
        "-Wno-error=return-type",
        str(VENDOR_ROOT / "ms.c"),
        str(VENDOR_ROOT / "streec.c"),
        str(VENDOR_ROOT / "verification" / "rand1_instrumented.c"),
        "-o",
        str(binary),
        "-lm",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"ms build failed:\n{result.stderr}"
    assert binary.is_file()
    return binary


def run_ms(ms_binary: Path, seeds: tuple[int, int, int], draw_log: Path) -> str:
    cmd = [
        str(ms_binary),
        str(NSAM),
        str(HOWMANY),
        "-t",
        str(THETA),
        "-seeds",
        str(seeds[0]),
        str(seeds[1]),
        str(seeds[2]),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env={"MS_DRAW_LOG": str(draw_log), "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, f"ms run failed:\n{result.stderr}"
    return result.stdout


def parse_ms_stdout(
    stdout: str, nsam: int, howmany: int
) -> list[tuple[int, list[str]]]:
    """Parses `howmany` "//"-delimited replicate blocks (ms.c:177-193):
    "segsites: N", then (only if N>0) a "positions:" line followed by N
    genotype rows — a "segsites==0" replicate prints neither (R3)."""
    lines = stdout.split("\n")
    replicates: list[tuple[int, list[str]]] = []
    i = 0
    while i < len(lines) and len(replicates) < howmany:
        if lines[i].strip() == "//" or lines[i].startswith("//"):
            i += 1
            assert lines[i].startswith("segsites: "), lines[i]
            segsites = int(lines[i].removeprefix("segsites: "))
            i += 1
            if segsites > 0:
                assert lines[i].startswith("positions: "), lines[i]
                i += 1
                rows = [lines[i + k] for k in range(nsam)]
                i += nsam
            else:
                # the unconditional trailing "\n" after the (skipped)
                # positions loop (ms.c:188-191) — a blank line, no rows.
                i += 1
                rows = []
            replicates.append((segsites, rows))
        else:
            i += 1
    assert len(replicates) == howmany, (
        f"expected {howmany} replicates, parsed {len(replicates)}"
    )
    return replicates
