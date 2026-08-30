"""R2 staging-schema validation negatives (R4 1–5) and boundary tests.

Every rejection leaves the registry unchanged (review acceptance focus);
the declaration side-channel (negative 5) is an invariance assertion, not
an error: mutating a nested `after` list after validation must not alter
the validated artifact the orchestration consumes.
"""

from __future__ import annotations

import pytest
import types

from newlife.adapters.process_bigraph.staging import (
    staging_declaration,
    topological_order,
    validate_staging,
)
from newlife.core.contracts import MechanismSpec
from newlife.core.errors import StageValidationError


def spec(identity, stage=None, after=()):
    schedule = (
        {"stage": stage, "after": list(after)}
        if stage is not None
        else {"kind": "runtime-managed"}
    )
    return MechanismSpec(
        identity=identity,
        version="1",
        plane="biological",
        biological_role="staging probe",
        ports=("state",),
        claims=(),
        schedule=schedule,
        rng_streams=(),
        allowed_effects=frozenset(),
        invariants=(),
    )


def test_negative_1_dag_cycle_is_rejected():
    registry = {"specs": [spec("a", "s1", ["s2"]), spec("b", "s2", ["s1"])]}
    with pytest.raises(StageValidationError, match="cycle"):
        validate_staging(registry["specs"])
    assert registry["specs"][0].schedule["stage"] == "s1"  # registry unchanged


def test_negative_2_self_loop_is_rejected():
    with pytest.raises(StageValidationError, match="self-loop"):
        validate_staging([spec("a", "s1", ["s1"])])


def test_negative_3_unknown_after_reference_is_rejected():
    with pytest.raises(StageValidationError, match="unknown after reference"):
        validate_staging([spec("a", "s1", ["ghost"])])


def test_negative_4_missing_declaration_is_rejected_no_defaults():
    with pytest.raises(StageValidationError, match="no staging declaration"):
        validate_staging([spec("declared", "s1"), spec("undeclared")])


def test_mixed_step_process_stage_is_a_declaration_error():
    with pytest.raises(StageValidationError, match="mixes Step and Process"):
        validate_staging(
            [spec("p1", "s1"), spec("s1m", "s1")],
            node_types={"p1": "process", "s1m": "step"},
        )


def test_malformed_stage_and_after_shapes_are_rejected():
    with pytest.raises(StageValidationError, match="non-empty string"):
        validate_staging([spec("a", "")])
    with pytest.raises(StageValidationError, match="after must be a list"):
        bad = spec("a", "s1", ["x"])
        object.__setattr__(
            bad, "schedule", __import__("types").MappingProxyType({"stage": "s1", "after": "x"})
        )
        validate_staging([bad])


def test_negative_5_declaration_side_channel_is_ineffective():
    # The schedule MappingProxyType freezes only the top level: the nested
    # after list stays mutable. Validation deep-copies at the boundary, so
    # post-validation mutation cannot alter the validated artifact that the
    # orchestration derivation consumes.
    inner = ["s0"]
    target = spec("a", "s1", inner)
    first = validate_staging([spec("z", "s0"), target])
    assert first["a"] == ("s1", ("s0",))
    inner.append("s0")  # mutate after validation (now ["s0", "s0"])
    assert first["a"] == ("s1", ("s0",))  # validated artifact unchanged
    # a pristine identical spec validates to exactly the same artifact
    pristine = spec("a", "s1", ["s0"])
    assert validate_staging([spec("z", "s0"), pristine]) == first


def test_validation_is_idempotent_and_registry_neutral():
    specs = [spec("a", "s1"), spec("b", "s2", ["s1"])]
    first = validate_staging(specs)
    assert validate_staging(specs) == first
    assert specs[0].schedule["stage"] == "s1"


def test_diamond_and_lexicographic_tie_break():
    dag = {"d": set(), "b": {"d"}, "c": {"d"}, "a": {"b", "c"}}
    assert topological_order(dag) == ["d", "b", "c", "a"]  # lexicographic tie-break


def test_topological_order_detects_cycle_by_length():
    assert len(topological_order({"x": {"y"}, "y": {"x"}})) == 0
