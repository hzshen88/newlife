"""Task 1 (analysis plan §7): builds the real, vendored `ms` binary fresh
(R1's exact command), runs the frozen grid (R6) as a real subprocess, and
asserts the standalone Python port (`ms_coalescent.py`) reproduces every
replicate's segsites count and genotype matrix exactly, replayed against
that run's own logged draws — never against drafting-time artifacts
(R6: "re-executed fresh, not reused").
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newlife.mechanisms.second_world.ms_coalescent import (
    RecordedDrawStream,
    run_replicate,
)

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

# Plan §0.5 / prereg § Frozen formal predictions — reproducible on demand
# from the pinned build and these seeds, not itself the frozen evidence
# (plan §1: the drafting-time run only justified the choice of grid).
EXPECTED_DRAWS_LOGGED = {"seedA": 177, "seedB": 163, "seedC": 191}
EXPECTED_SEGSITES_ZERO_COUNT = {"seedA": 0, "seedB": 4, "seedC": 2}


@pytest.fixture(scope="module")
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


def _run_ms(ms_binary: Path, seeds: tuple[int, int, int], draw_log: Path) -> str:
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


def _parse_ms_stdout(
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


@pytest.mark.parametrize("seed_name", sorted(SEED_TRIPLES))
def test_standalone_port_matches_real_ms_bit_for_bit(ms_binary, tmp_path, seed_name):
    seeds = SEED_TRIPLES[seed_name]
    draw_log = tmp_path / f"{seed_name}.draws"
    stdout = _run_ms(ms_binary, seeds, draw_log)
    real_replicates = _parse_ms_stdout(stdout, NSAM, HOWMANY)

    draws = RecordedDrawStream.from_log_file(draw_log)
    zero_count = 0
    for index, (expected_segsites, expected_rows) in enumerate(real_replicates):
        result = run_replicate(NSAM, THETA, draws)
        assert result.segsites == expected_segsites, (
            f"{seed_name} replicate {index}: segsites {result.segsites} != {expected_segsites}"
        )
        assert result.genotype_rows == expected_rows, (
            f"{seed_name} replicate {index}: genotype rows differ"
        )
        if result.segsites == 0:
            zero_count += 1

    assert draws.leftover == 0, f"{seed_name}: {draws.leftover} draws left over"
    assert draws.consumed == EXPECTED_DRAWS_LOGGED[seed_name], (
        f"{seed_name}: consumed {draws.consumed}, expected {EXPECTED_DRAWS_LOGGED[seed_name]}"
    )
    assert zero_count == EXPECTED_SEGSITES_ZERO_COUNT[seed_name]


def test_frozen_grid_still_contains_a_segsites_zero_replicate(ms_binary, tmp_path):
    """Round-1 red-team requirement (plan §0/§7 Task 1): the segsites==0
    output shape's coverage must stay declared, not incidental."""
    total_zero = 0
    for seed_name, seeds in SEED_TRIPLES.items():
        draw_log = tmp_path / f"{seed_name}-coverage.draws"
        stdout = _run_ms(ms_binary, seeds, draw_log)
        for segsites, _rows in _parse_ms_stdout(stdout, NSAM, HOWMANY):
            if segsites == 0:
                total_zero += 1
    assert total_zero > 0, "frozen grid no longer contains a segsites==0 replicate"
