"""R4 negatives 9 & 10 for the reference adapter: tampered-lowering control
and payload side-channel.

Tamper control (R4.9): a deliberately wrong lowering (set/add op swap) must
be *detected* by the frozen byte comparisons. Fixture A's budget store starts
at zero, where set→add is numerically invisible — the control therefore flips
add→set (executed counts 2→1, detected via final state) and runs fixture C
(hook_authority, rate 0.1 + 0.2 = 0.3 ≠ 0.2, detected via final state) for
the set→add direction. The trace comparison's teeth are proven separately by
the anti-masking probes (test_ruler.py). A tampered lowering that goes
undetected would void every positive result (decision matrix).
"""

from __future__ import annotations

from newlife.adapters.reference_kernel.cases import (
    REFERENCE_CASES,
    run_transfer_microfixture,
)
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.conform.fixtures import load_fixture
from newlife.core.lowering_contract import OP_ADD, OP_SET


def _run_with_tampered_ops(case_name: str, mode: str):
    """Deliberately wrong lowering: swap one op direction. Ops are only
    swapped where the flip is type-coherent (a set of a map payload turned
    into an add would crash on Decimal conversion — itself a detection, but
    an uninteresting one)."""
    import newlife.adapters.reference_kernel.kernel as kernel_module

    original = kernel_module.apply_op

    def tampered(state, op):
        if mode == "add_becomes_set" and op.op == OP_ADD:
            return original(state, type(op)(op.path, OP_SET, op.payload, op.provenance))
        if mode == "set_becomes_add" and op.op == OP_SET:
            return original(state, type(op)(op.path, OP_ADD, op.payload, op.provenance))
        return original(state, op)

    kernel_module.apply_op = tampered
    try:
        return REFERENCE_CASES[case_name](include_negatives=False)
    finally:
        kernel_module.apply_op = original


def test_tampered_lowering_fixture_a_is_detected_by_byte_comparison(monkeypatch):
    honest = REFERENCE_CASES["execution_budget"](include_negatives=False)
    expected = load_fixture("execution_budget.json")
    assert honest.trace == expected["expected_trace"]
    assert honest.final_state == expected["expected_final_state"]

    tampered = _run_with_tampered_ops("execution_budget", "add_becomes_set")
    assert canonical_bytes(tampered.final_state) != canonical_bytes(expected["expected_final_state"])
    assert not tampered.assertions["exact_final_state"]
    assert not all(tampered.assertions.values())


def test_tampered_lowering_set_to_add_flip_is_detected_on_fixture_c(monkeypatch):
    tampered = _run_with_tampered_ops("hook_authority", "set_becomes_add")
    expected = load_fixture("hook_authority.json")
    assert canonical_bytes(tampered.final_state) != canonical_bytes(expected["expected_final_state"])
    assert not all(tampered.assertions.values())


def test_tampered_transfer_is_detected_on_microfixture():
    import newlife.adapters.reference_kernel.kernel as kernel_module

    original = kernel_module.apply_op

    def skimming(state, op):
        # Skim half the transfer amount — conservation must catch it.
        if op.op == "transfer_pair":
            payload = dict(op.payload)
            payload["amount"] = "0.125"
            op = type(op)(op.path, op.op, payload, op.provenance)
        return original(state, op)

    kernel_module.apply_op = skimming
    try:
        result = run_transfer_microfixture()
    finally:
        kernel_module.apply_op = original
    expected = load_fixture("effect_algebra_transfer.json")
    assert canonical_bytes(result.final_state) != canonical_bytes(expected["expected_final_state"])
    assert not result.assertions["exact_final_state"]


def test_payload_side_channel_does_not_alter_committed_state():
    # R4 negative 10: mutable container mutated after validation must not
    # alias into committed state (deep-copy boundary at the write path).
    from newlife.adapters.reference_kernel.kernel import ReferenceKernel
    from newlife.core.contracts import MechanismSpec, StateClaim, StateDelta

    kernel = ReferenceKernel({"box": {"items": []}})
    kernel.register_mechanism(
        MechanismSpec(
            identity="Owner",
            version="1",
            plane="biological",
            biological_role="side-channel probe",
            ports=("state",),
            claims=(StateClaim(("box", "items"), "own"),),
            schedule={},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        )
    )
    payload = [1, 2]
    kernel.apply_batch(
        "Owner",
        [StateDelta(("box", "items"), "set", payload)],
        [{"kind": "ItemsSet", "time": "0.0", "source": "Owner"}],
    )
    payload.append(3)  # mutation after validation/commit
    assert kernel.state["box"]["items"] == [1, 2]
    assert [record["kind"] for record in kernel.trace] == ["ItemsSet"]
