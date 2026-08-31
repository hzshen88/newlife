"""Task 2 (analysis plan §7/§8, tier b): does the mechanism registry
(`MechanismSpec`/`StructuralRewrite`/`Event`/`ReferenceKernel`) reproduce
tier (a)'s own output exactly, replicate-for-replicate, when fed the exact
same draw sequence? This is the step that actually tests whether newlife's
contract layer is time-model-agnostic — the question this whole program
exists to answer (plan §8) — not a second, independent verification of the
algorithm against real `ms` (that is Task 1's job).
"""

from __future__ import annotations

import pytest

from conftest import HOWMANY, NSAM, SEED_TRIPLES, THETA, run_ms
from newlife.mechanisms.second_world.ms_coalescent import (
    RecordedDrawStream,
    run_replicate,
)
from newlife.mechanisms.second_world.world import CoalescentWorld, run_from_rng_bank


@pytest.mark.parametrize("seed_name", sorted(SEED_TRIPLES))
def test_mechanism_registry_matches_standalone_port(ms_binary, tmp_path, seed_name):
    seeds = SEED_TRIPLES[seed_name]
    draw_log = tmp_path / f"{seed_name}.draws"
    # Only the draw log is used here — tier (b) is compared against tier
    # (a)'s own output (plan § Primary analysis), not against real ms
    # stdout directly; that comparison is Task 1's (test_ms_grid.py).
    run_ms(ms_binary, seeds, draw_log)

    tier_a_draws = RecordedDrawStream.from_log_file(draw_log)
    tier_b_draws = RecordedDrawStream.from_log_file(draw_log)

    for index in range(HOWMANY):
        tier_a = run_replicate(NSAM, THETA, tier_a_draws)
        tier_b = CoalescentWorld(NSAM, THETA, tier_b_draws, replicate_index=index).run()
        assert tier_b.segsites == tier_a.segsites, (
            f"{seed_name} replicate {index}: segsites differ (tier a={tier_a.segsites}, "
            f"tier b={tier_b.segsites})"
        )
        assert tier_b.genotype_rows == tier_a.genotype_rows, (
            f"{seed_name} replicate {index}: genotype rows differ"
        )

    assert tier_a_draws.leftover == 0
    assert tier_b_draws.leftover == 0
    assert tier_a_draws.consumed == tier_b_draws.consumed


def test_run_from_rng_bank_produces_a_valid_tree():
    """Plan §7 Task 2's separate, non-frozen-grid requirement: the
    seed-derivation path (RngBank -> derive_stream_seed -> R2's mapping)
    must produce a runnable world end-to-end. Not compared to `ms` output —
    no `ms` run ever consumes a derived seed."""
    outcome = run_from_rng_bank(root_seed=42, nsam=NSAM, theta=THETA)
    assert isinstance(outcome.segsites, int)
    assert outcome.segsites >= 0
    if outcome.segsites == 0:
        assert outcome.genotype_rows == []
    else:
        assert len(outcome.genotype_rows) == NSAM
        assert all(len(row) == outcome.segsites for row in outcome.genotype_rows)
        assert all(set(row) <= {"0", "1"} for row in outcome.genotype_rows)
