"""Task 3 (analysis plan §7): the verdict runner computes the two-tier
conjunction mechanically and writes the results bundle (R7) — this is an
integration check of the runner's own wiring (JSON output, conjunction
logic), not a re-check of the algorithm (that's test_ms_grid.py and
test_mechanism_registry.py's job).
"""

from __future__ import annotations

import json

from newlife.conform.second_world_verdict import (
    VERDICT_PASS,
    compute_verdict,
    execute,
)


def test_execute_writes_a_passing_results_bundle(tmp_path):
    output_dir = tmp_path / "results"
    workdir = tmp_path / "work"
    workdir.mkdir()

    summary = execute(output_dir, workdir)

    assert summary["verdict"] == VERDICT_PASS
    assert summary["passed"] is True
    assert summary["replicate_count"] == 30
    assert summary["structural_checks"]["r2_mapping_correctness"]["passed"] is True
    assert summary["structural_checks"]["segsites_zero_coverage"]["passed"] is True
    for seed_name in ("seedA", "seedB", "seedC"):
        assert summary["tiers"]["tier_a"][seed_name]["all_passed"] is True
        assert summary["tiers"]["tier_a"][seed_name]["leftover"] == 0
        assert summary["tiers"]["tier_b"][seed_name]["all_passed"] is True
        assert summary["tiers"]["tier_b"][seed_name]["leftover"] == 0

    on_disk = json.loads((output_dir / "summary.json").read_text())
    assert on_disk == summary

    replicate_files = sorted((output_dir / "replicates").glob("*.json"))
    assert len(replicate_files) == 30
    sample = json.loads(replicate_files[0].read_text())
    assert sample["tier_a"]["passed"] is True
    assert sample["tier_b"]["passed"] is True
    assert "genotype_hash" in sample["tier_a"]


def test_compute_verdict_withholds_when_any_check_fails():
    """A verdict runner that always reports pass regardless of its inputs
    would be useless — this checks the conjunction actually gates."""
    passing_seed_result = {
        "tier_a": [{"passed": True}],
        "tier_b": [{"passed": True}],
        "tier_a_leftover": 0,
        "segsites_zero_count": 1,
    }
    failing_r2 = {"passed": False}
    passing_r2 = {"passed": True}

    assert compute_verdict({"seedA": passing_seed_result}, passing_r2) == VERDICT_PASS
    assert compute_verdict({"seedA": passing_seed_result}, failing_r2) != VERDICT_PASS

    tier_b_failed = {
        **passing_seed_result,
        "tier_b": [{"passed": False}],
    }
    assert compute_verdict({"seedA": tier_b_failed}, passing_r2) != VERDICT_PASS

    no_zero_coverage = {**passing_seed_result, "segsites_zero_count": 0}
    assert compute_verdict({"seedA": no_zero_coverage}, passing_r2) != VERDICT_PASS
