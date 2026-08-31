"""Generic tests for newlife.core.compare — no World 1 dependency.

Covers the calibration cases from the frozen v0.3 preregistration
(`2026-08-31-newlife-compare-attribution-declarability-v2.md`, R1/R3/R4)
using synthetic dataclasses and hand-written runners: n=0,1,2,3 causal
attribution, the length-mismatch locus, and all three aggregate outcomes
including the precedence regression case (unit 6c) where the "no causal"
and "any unresolved" conditions are both true of the same observation.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from newlife.core.compare import (
    attribute_causality,
    diff_declarations,
    locate_divergence,
)


@dataclasses.dataclass(frozen=True)
class TwoFieldConfig:
    alpha: str
    beta: str


@dataclasses.dataclass(frozen=True)
class ThreeFieldConfig:
    alpha: str
    beta: str
    gamma: str


@dataclasses.dataclass(frozen=True)
class OtherConfig:
    alpha: str


def test_diff_declarations_type_mismatch_raises_type_error():
    with pytest.raises(TypeError):
        diff_declarations((), (), TwoFieldConfig("a", "a"), OtherConfig("a"))


def test_diff_declarations_names_differing_fields_sorted():
    diff = diff_declarations(
        ("m1", "m2"),
        ("m1", "m2"),
        TwoFieldConfig(alpha="a1", beta="b1"),
        TwoFieldConfig(alpha="a2", beta="b1"),
    )
    assert diff.registry_equal is True
    assert diff.differing_fields == ("alpha",)


def test_diff_declarations_detects_registry_difference():
    diff = diff_declarations(
        ("m1",),
        ("m1", "m2"),
        TwoFieldConfig("a", "b"),
        TwoFieldConfig("a", "b"),
    )
    assert diff.registry_equal is False
    assert diff.differing_fields == ()


def test_locate_divergence_identical_sequences_returns_none():
    seq = [{"tick": 0, "x": 1}, {"tick": 1, "x": 2}]
    assert locate_divergence(seq, list(seq)) is None


def test_locate_divergence_value_difference_reports_index_and_tick():
    seq_a = [{"tick": 0, "x": 1}, {"tick": 1, "x": 2}]
    seq_b = [{"tick": 0, "x": 1}, {"tick": 1, "x": 9}]
    locus = locate_divergence(seq_a, seq_b)
    assert locus.kind == "value"
    assert locus.index == 1
    assert locus.tick == 1


def test_locate_divergence_length_mismatch_is_distinct_from_value_divergence():
    seq_a = [{"tick": 0, "x": 1}, {"tick": 1, "x": 2}, {"tick": 2, "x": 3}]
    seq_b = [{"tick": 0, "x": 1}, {"tick": 1, "x": 2}]
    locus = locate_divergence(seq_a, seq_b)
    assert locus.kind == "length_mismatch"
    assert locus.index == 2


def test_attribute_causality_n0_no_divergence_is_normal():
    config = TwoFieldConfig("a", "b")
    diff = diff_declarations((), (), config, config)
    seq = [{"tick": 0, "x": 1}]

    def runner(_cfg):
        raise AssertionError("no rerun should be executed when n=0")

    result = attribute_causality(diff, seq, list(seq), runner)
    assert result.per_field == {}
    assert result.aggregate == "normal"


def test_attribute_causality_n1_no_divergence_is_incidental_no_rerun():
    config_a = TwoFieldConfig(alpha="a1", beta="shared")
    config_b = TwoFieldConfig(alpha="a2", beta="shared")
    diff = diff_declarations((), (), config_a, config_b)
    seq = [{"tick": 0, "x": 1}]

    def runner(_cfg):
        raise AssertionError("no rerun should be executed when there is no divergence")

    result = attribute_causality(diff, seq, list(seq), runner)
    assert result.per_field == {"alpha": "incidental"}
    assert result.aggregate == "normal"


def test_attribute_causality_n1_divergence_causal_by_rerun_not_elimination():
    """A single differing field with a divergence must still be *verified*
    by a rerun (R4) — not declared causal by elimination."""
    config_a = TwoFieldConfig(alpha="a1", beta="shared")
    config_b = TwoFieldConfig(alpha="a2", beta="shared")
    diff = diff_declarations((), (), config_a, config_b)
    history_a = [{"tick": 0}, {"tick": 1, "x": "from-a1"}]
    history_b = [{"tick": 0}, {"tick": 1, "x": "from-a2"}]

    def runner(cfg):
        return [{"tick": 0}, {"tick": 1, "x": f"from-{cfg.alpha}"}]

    result = attribute_causality(diff, history_a, history_b, runner)
    assert result.per_field == {"alpha": "causal"}
    assert result.aggregate == "normal"


def test_attribute_causality_n2_one_causal_one_incidental():
    """Mirrors calibration unit 1 (informative vs cue-neutral)."""
    config_a = TwoFieldConfig(alpha="a1", beta="b1")
    config_b = TwoFieldConfig(alpha="a2", beta="b2")
    diff = diff_declarations((), (), config_a, config_b)

    def runner(cfg):
        # alpha drives the observation; beta is cosmetic.
        return [{"tick": 0}, {"tick": 1, "x": f"driven-by-{cfg.alpha}"}]

    history_a = runner(config_a)
    history_b = runner(config_b)
    result = attribute_causality(diff, history_a, history_b, runner)
    assert result.per_field == {"alpha": "causal", "beta": "incidental"}
    assert result.aggregate == "normal"


def test_attribute_causality_n3_one_causal_two_incidental():
    """Mirrors synthetic calibration unit 5."""
    config_a = ThreeFieldConfig(alpha="a1", beta="b1", gamma="g1")
    config_b = ThreeFieldConfig(alpha="a2", beta="b2", gamma="g2")
    diff = diff_declarations((), (), config_a, config_b)

    def runner(cfg):
        return [{"tick": 0}, {"tick": 1, "x": f"driven-by-{cfg.alpha}"}]

    history_a = runner(config_a)
    history_b = runner(config_b)
    result = attribute_causality(diff, history_a, history_b, runner)
    assert result.per_field == {
        "alpha": "causal",
        "beta": "incidental",
        "gamma": "incidental",
    }
    assert result.aggregate == "normal"


def test_attribute_causality_unattributed_divergence():
    """Mirrors synthetic calibration unit 6a: the real cause lies outside
    the declared basis entirely — every declared field must classify
    incidental, and the aggregate must flag the basis as insufficient."""
    config_a = TwoFieldConfig(alpha="a1", beta="b1")
    config_b = TwoFieldConfig(alpha="a2", beta="b2")
    diff = diff_declarations((), (), config_a, config_b)

    hidden = {"flag": "A"}

    def runner(_cfg):
        # depends only on module-level state, never on the config's fields
        return [{"tick": 0}, {"tick": 1, "x": hidden["flag"]}]

    hidden["flag"] = "A"
    history_a = runner(config_a)
    hidden["flag"] = "B"
    history_b = runner(config_b)

    def rerun(_cfg):
        # every rerun happens with hidden["flag"] still at "B"
        return runner(_cfg)

    result = attribute_causality(diff, history_a, history_b, rerun)
    assert result.per_field == {"alpha": "incidental", "beta": "incidental"}
    assert result.aggregate == "UNATTRIBUTED_DIVERGENCE"


def test_attribute_causality_multi_causal():
    """Mirrors synthetic calibration unit 6b: two fields are each
    independently sufficient to reproduce the divergence when flipped alone."""
    config_a = TwoFieldConfig(alpha="X", beta="X")
    config_b = TwoFieldConfig(alpha="Y", beta="Y")
    diff = diff_declarations((), (), config_a, config_b)

    def runner(cfg):
        # "diverged" only when NEITHER field is at its A value — so flipping
        # either field alone back to "X" is independently sufficient to undo it.
        diverged = not (cfg.alpha == "X" or cfg.beta == "X")
        return [{"tick": 0}, {"tick": 1, "diverged": diverged}]

    history_a = runner(config_a)
    history_b = runner(config_b)
    result = attribute_causality(diff, history_a, history_b, runner)
    # flipping alpha alone back to "X" (beta stays "Y") already undoes the divergence
    # flipping beta alone back to "X" (alpha stays "Y") also already undoes it
    # both reruns reproduce history_a exactly -> both classify causal
    assert result.per_field == {"alpha": "causal", "beta": "causal"}
    assert result.aggregate == "MULTI_CAUSAL_OR_UNRESOLVED"


def test_attribute_causality_unresolved_takes_precedence_over_unattributed():
    """Mirrors synthetic calibration unit 6c — the round-2 red-team's
    precedence regression test. One field is genuinely coupled to another
    (its flip reproduces neither side exactly); a second field is cleanly
    incidental. Both the "no causal field" condition and the "a field is
    unresolved" condition are true of this exact observation; the aggregate
    must resolve to MULTI_CAUSAL_OR_UNRESOLVED (unresolved checked first),
    never UNATTRIBUTED_DIVERGENCE."""
    config_a = TwoFieldConfig(alpha="a1", beta="b1")
    config_b = TwoFieldConfig(alpha="a2", beta="b2")
    diff = diff_declarations((), (), config_a, config_b)

    def runner(cfg):
        if cfg.alpha == "a1":
            if cfg.beta == "b1":
                return [{"tick": 0}, {"tick": 1, "x": "A"}]  # == history_a
            return [{"tick": 0}, {"tick": 1, "x": "coupled"}]  # neither side
        return [{"tick": 0}, {"tick": 1, "x": "B"}]  # == history_b, beta irrelevant

    history_a = runner(config_a)
    history_b = runner(config_b)
    result = attribute_causality(diff, history_a, history_b, runner)

    assert result.per_field == {"alpha": "unresolved", "beta": "incidental"}
    assert result.aggregate == "MULTI_CAUSAL_OR_UNRESOLVED"


def test_core_compare_never_hardcodes_a_field_name():
    """R4's no-peeking control: core/compare.py must operate on whatever
    field names dataclasses.fields() returns, never a specific one."""
    source = (
        Path(__file__).resolve().parents[2] / "src" / "newlife" / "core" / "compare.py"
    )
    text = source.read_text(encoding="utf-8")
    assert "condition" not in text
    assert '"name"' not in text and "'name'" not in text
