"""R3 derivation unit tests against synthetic DAGs + R4 negatives 6 & 8 setup
+ the R6 reference predicate. All pure functions over the closed basis — no
engine, no fixtures. The orchestration-tamper control (negative 8) runs
against the real budget slice in test_staging_cases.py (it needs the engine).
"""

from __future__ import annotations

import dataclasses

import pytest

from newlife.adapters.process_bigraph.staging import (
    compile_staging,
    derive_orchestration,
    order_is_consistent_with_dag,
    validate_staging,
)
from newlife.core.contracts import MechanismSpec
from newlife.core.errors import StageValidationError


def spec(identity, stage, after=()):
    return MechanismSpec(
        identity=identity,
        version="1",
        plane="biological",
        biological_role="derivation probe",
        ports=("state",),
        claims=(),
        schedule={"stage": stage, "after": list(after)},
        rng_streams=(),
        allowed_effects=frozenset(),
        invariants=(),
    )


def node(mech, node_type="process", interval=1.0, inputs=None, outputs=None):
    node_dict = {"_type": node_type, "address": f"local:{mech}", "config": {"mechanism_id": mech}}
    if node_type == "process":
        node_dict["interval"] = interval
    if inputs:
        node_dict["inputs"] = inputs
    if outputs:
        node_dict["outputs"] = outputs
    return node_dict


# ── P1: state-root derivation ────────────────────────────────────────────────


def test_p1_initial_roots_minus_internal_roots():
    # budget shape: internal root produced and consumed within one stage
    validated = validate_staging(
        [spec("alloc", "allocate"), spec("resolver", "allocate"), spec("inst", "instruct", ["allocate"])]
    )
    nodes = {
        "alloc": node("alloc", "step", inputs={"merit": ["organisms", "A", "merit"]},
                      outputs={"proposal": ["budget_proposal"]}),
        "resolver": node("resolver", "step", inputs={"proposal": ["budget_proposal"]},
                         outputs={"budget": ["execution_budget"]}),
        "inst": node("inst", interval=1.0, inputs={"budget": ["execution_budget", "A"]},
                     outputs={"executed": ["organisms", "A", "executed"]}),
    }
    initial = {"execution_budget": {"A": 0}, "organisms": {"A": {"executed": 0, "merit": "2"}}}
    orch = derive_orchestration(
        validated, nodes, initial,
        output_schemas={("alloc", "proposal"): {"A": "integer", "B": "integer", "available": "integer"}},
    )
    assert orch.carried_roots == ("execution_budget", "organisms")
    allocate = orch.plan[0]
    assert allocate.label == "allocate"
    assert allocate.internal_roots == ("budget_proposal",)
    assert allocate.state["budget_proposal"] == {"A": 0, "B": 0, "available": 0}  # schema zero
    assert set(allocate.state) == {"execution_budget", "organisms", "budget_proposal"}
    instruct = orch.plan[1]
    assert instruct.state_roots == ("execution_budget", "organisms")  # dropped after its stage
    assert allocate.duration == 0.0 and instruct.duration == 1.0  # P2


def test_p1_root_closure_cross_stage_root_is_rejected():
    validated = validate_staging([spec("p", "s1"), spec("c", "s2", ["s1"])])
    nodes = {
        "p": node("p", outputs={"out": ["scratch"]}),
        "c": node("c", inputs={"in": ["scratch"]}),
    }
    with pytest.raises(StageValidationError, match="created across stages"):
        derive_orchestration(validated, nodes, {"init": 1})


def test_p1_root_closure_consumer_without_producer_is_rejected():
    validated = validate_staging([spec("c", "s1")])
    nodes = {"c": node("c", inputs={"in": ["ghost"]})}
    with pytest.raises(StageValidationError, match="never produced"):
        derive_orchestration(validated, nodes, {"init": 1})


def test_p1_internal_root_without_declared_schema_is_rejected():
    validated = validate_staging([spec("p", "s1"), spec("c", "s1")])
    nodes = {
        "p": node("p", outputs={"out": ["scratch"]}),
        "c": node("c", inputs={"in": ["scratch"]}),
    }
    with pytest.raises(StageValidationError, match="no declared output schema"):
        derive_orchestration(validated, nodes, {"init": 1})


# ── P2: durations ────────────────────────────────────────────────────────────


def test_p2_interval_disagreement_is_a_compile_time_error():
    validated = validate_staging([spec("x", "s1"), spec("y", "s1")])
    nodes = {
        "x": node("x", interval=1.0),
        "y": node("y", interval=2.0),
    }
    with pytest.raises(StageValidationError, match="disagree on interval"):
        derive_orchestration(validated, nodes, {"init": 1})


# ── P3: grouping and deterministic order ─────────────────────────────────────


def test_p3_diamond_dag_lexicographic_order_and_grouping():
    validated = validate_staging(
        [spec("d", "d"), spec("b", "b", ["d"]), spec("c", "c", ["d"]), spec("a", "a", ["b", "c"])]
    )
    nodes = {m: node(m) for m in ("a", "b", "c", "d")}
    orch = derive_orchestration(validated, nodes, {"init": 1})
    assert [plan.label for plan in orch.plan] == ["d", "b", "c", "a"]
    assert [plan.mechanisms for plan in orch.plan] == [("d",), ("b",), ("c",), ("a",)]
    assert all(plan.duration == 1.0 for plan in orch.plan)


# ── R4 negative 6: no ordering parameter, validator rejects contradictions ───


def test_negative_6_compile_signature_admits_no_ordering_parameter():
    validated = validate_staging([spec("a", "s1"), spec("b", "s2", ["s1"])])
    nodes = {"a": node("a"), "b": node("b")}
    with pytest.raises(TypeError):
        compile_staging(nodes, [spec("a", "s1"), spec("b", "s2", ["s1"])], {"init": 1},
                        order=["s2", "s1"])  # type: ignore[call-arg]


def test_negative_6_internal_validator_rejects_dag_contradicting_order():
    dag = {"s1": set(), "s2": {"s1"}}
    assert order_is_consistent_with_dag(dag, ["s1", "s2"])
    with pytest.raises(StageValidationError):
        from newlife.adapters.process_bigraph import staging as staging_module

        # the same predicate the compiler's order check is built on
        if not staging_module.order_is_consistent_with_dag(dag, ["s2", "s1"]):
            raise StageValidationError("order contradicts the declared DAG")


# ── R6 reference predicate ───────────────────────────────────────────────────


def test_r6_predicate_accepts_the_frozen_budget_program_order():
    dag = {"allocate": set(), "instruct-a": {"allocate"}, "instruct-b": {"instruct-a"}}
    assert order_is_consistent_with_dag(dag, ["allocate", "instruct-a", "instruct-a", "instruct-b"])


def test_r6_predicate_rejects_the_dedupe_fooling_reappearance():
    dag = {"allocate": set(), "instruct-a": {"allocate"}, "instruct-b": {"instruct-a"}}
    # a deduplicating checker would accept this; the frozen predicate must not
    assert not order_is_consistent_with_dag(dag, ["allocate", "instruct-a", "instruct-b", "instruct-a"])


def test_r6_predicate_rejects_prerequisite_running_after_dependent():
    dag = {"allocate": set(), "instruct-a": {"allocate"}}
    assert not order_is_consistent_with_dag(dag, ["instruct-a", "allocate"])


def test_r6_predicate_rejects_undeclared_stage_labels():
    with pytest.raises(StageValidationError, match="undeclared stages"):
        order_is_consistent_with_dag({"s1": set()}, ["s1", "ghost"])
