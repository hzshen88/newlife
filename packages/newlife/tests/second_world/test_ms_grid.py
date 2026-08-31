"""Task 1 (analysis plan §7): builds the real, vendored `ms` binary fresh
(R1's exact command), runs the frozen grid (R6) as a real subprocess, and
asserts the standalone Python port (`ms_coalescent.py`) reproduces every
replicate's segsites count and genotype matrix exactly, replayed against
that run's own logged draws — never against drafting-time artifacts
(R6: "re-executed fresh, not reused").
"""

from __future__ import annotations

import pytest

from conftest import HOWMANY, NSAM, SEED_TRIPLES, THETA, parse_ms_stdout, run_ms
from newlife.mechanisms.second_world.ms_coalescent import (
    RecordedDrawStream,
    run_replicate,
)

# Plan §0.5 / prereg § Frozen formal predictions — reproducible on demand
# from the pinned build and these seeds, not itself the frozen evidence
# (plan §1: the drafting-time run only justified the choice of grid).
EXPECTED_DRAWS_LOGGED = {"seedA": 177, "seedB": 163, "seedC": 191}
EXPECTED_SEGSITES_ZERO_COUNT = {"seedA": 0, "seedB": 4, "seedC": 2}


@pytest.mark.parametrize("seed_name", sorted(SEED_TRIPLES))
def test_standalone_port_matches_real_ms_bit_for_bit(ms_binary, tmp_path, seed_name):
    seeds = SEED_TRIPLES[seed_name]
    draw_log = tmp_path / f"{seed_name}.draws"
    stdout = run_ms(ms_binary, seeds, draw_log)
    real_replicates = parse_ms_stdout(stdout, NSAM, HOWMANY)

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
        stdout = run_ms(ms_binary, seeds, draw_log)
        for segsites, _rows in parse_ms_stdout(stdout, NSAM, HOWMANY):
            if segsites == 0:
                total_zero += 1
    assert total_zero > 0, "frozen grid no longer contains a segsites==0 replicate"
