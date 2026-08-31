"""World-1 calibration units 1-4 for `core.compare` (v0.3, R5).

Runs the four real World-1-derived calibration pairs frozen in
`docs/science-superpowers/preregistrations/2026-08-31-newlife-compare-attribution-declarability-v2.md`
through `core.compare`'s generic diff/locate/attribute functions and
asserts the results against the known-true oracle recorded on each
`CalibrationUnit` — reproducing the frozen transcript exactly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from newlife.core.compare import (
    attribute_causality,
    diff_declarations,
    locate_divergence,
)
from newlife.mechanisms.resource_foraging.calibration import (
    CalibrationUnit,
    build_unit1,
    build_unit2,
    build_unit3,
    build_unit4,
)

CONFIGS_DIR = Path(__file__).resolve().parents[4] / "examples" / "first-world"
INFORMATIVE = CONFIGS_DIR / "informative.toml"
CUE_NEUTRAL = CONFIGS_DIR / "cue_neutral.toml"


def _assert_unit(unit: CalibrationUnit) -> None:
    diff = diff_declarations(
        unit.registry_a, unit.registry_b, unit.config_a, unit.config_b
    )
    assert diff.registry_equal is unit.expected_registry_equal
    assert diff.differing_fields == unit.expected_differing_fields

    locus = locate_divergence(unit.history_a, unit.history_b)
    if unit.expected_locus_tick is None:
        assert locus is None, f"{unit.name}: expected no divergence, found {locus}"
    else:
        assert locus is not None, f"{unit.name}: expected a divergence, found none"
        assert locus.kind == "value"
        assert locus.tick == unit.expected_locus_tick

    result = attribute_causality(diff, unit.history_a, unit.history_b, unit.runner)
    assert dict(result.per_field) == dict(unit.expected_per_field)
    assert result.aggregate == unit.expected_aggregate


def test_unit1_informative_vs_cue_neutral():
    _assert_unit(build_unit1(INFORMATIVE, CUE_NEUTRAL))


@pytest.mark.parametrize("seed", [101, 202])
def test_unit2_assay_true_vs_ablated(seed: int):
    """Two independent seeds (R5 unit 2) — both must resolve the same way,
    ruling out a coincidence tied to one specific RNG draw sequence."""
    _assert_unit(build_unit2(INFORMATIVE, seed))


def test_unit3_irrelevant_difference_control():
    _assert_unit(build_unit3(INFORMATIVE))


def test_unit4_zero_delta_replay_control():
    _assert_unit(build_unit4(INFORMATIVE))
