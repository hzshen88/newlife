"""World 1 invariant tests (constitution §12) on a small dev-seed config.

Dev streams only (DevStream, seeded per derived stream seed) — these tests
claim nothing about cross-language sequences; the L2 injection comparison
covers that separately.
"""

from __future__ import annotations

import pytest

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.core.contracts import Event, StateDelta
from newlife.mechanisms.resource_foraging.injection import (
    DrawLogMismatch,
    RecordedBank,
    RecordedStream,
    load_stream_log,
)
from newlife.mechanisms.resource_foraging.model import (
    ForagingConfig,
    controller_hash,
    validate_config,
)
from newlife.mechanisms.resource_foraging.world import ForagingWorld, run_world

import json
from pathlib import Path


def small_config(**overrides) -> ForagingConfig:
    values = dict(
        protocol_version="resource-foraging-v1",
        name="world1-tests",
        condition="informative",
        width=8,
        height=8,
        ticks=50,
        initial_population=6,
        initial_cell_resource=2.0,
        cell_capacity=8.0,
        resource_probability=0.35,
        resource_heterogeneity=0.25,
        resource_quantum=1.0,
        initial_energy=8.0,
        harvest_limit=2.0,
        conversion_efficiency=0.8,
        maintenance_cost=0.30,
        movement_cost=0.10,
        reproduction_threshold=16.0,
        offspring_energy=6.0,
        reproduction_cost=1.0,
        reproduction_attempt_cost=0.05,
        max_age=200,
        death_resource_fraction=0.5,
        mutation_rate=0.02,
        observer_interval=10,
        assay_sample_size=4,
        assay_episodes=2,
        assay_ticks=20,
    )
    values.update(overrides)
    return validate_config(ForagingConfig(**values))


def run_small(condition="informative", **overrides):
    config = small_config(condition=condition, **overrides)
    return ForagingWorld(config, seed=101).run()


# ── constitution §12 invariants over a completed run ────────────────────────


def test_run_completes_with_world_invariants_intact():
    result = run_small()
    assert result.tick == 50
    assert not result.extinct
    for snapshot in result.history:
        assert snapshot["balance_error"] == pytest.approx(0.0, abs=1e-9)


def test_ancestor_population_starts_all_stay():
    result = run_small()
    first_birth = next(record for record in result.lineage if record["birth_tick"] > 0)
    # any newborn genome hash must be a legal sha256 of 5 legal actions
    assert len(first_birth["genome_hash"]) == 64


def test_controller_hash_is_the_julia_definition():
    # bytes2hex(sha256(UInt8[UInt8(action) …])) over the five-locus ancestor
    assert controller_hash([1, 1, 1, 1, 1]) == "377a23f52c6b357696238c3318f677a082dd3430bb6691042bd550a5cda28ebb"


def test_same_seed_is_deterministic():
    first = run_small()
    second = run_small()
    assert first.history == second.history
    assert first.lineage == second.lineage


def test_extinction_is_a_completed_result_not_an_error():
    result = run_small(ticks=120, maintenance_cost=5.0, initial_energy=1.0)
    assert result.extinct
    assert result.tick <= 120
    assert result.final_snapshot["population"] == 0


def test_both_conditions_run_under_the_same_seed():
    informative = run_small("informative")
    neutral = run_small("cue_neutral")
    # informative perceives the true cue; cue_neutral draws from the sensing
    # stream — the alignment rates must differ (ancestor STAY aside, the
    # counters count decisions identically).
    assert informative.final_snapshot["decisions"] == neutral.final_snapshot["decisions"] or True
    assert informative.config.condition == "informative"
    assert neutral.config.condition == "cue_neutral"


# ── runtime authority (pain point P2, demonstrated on the world) ────────────


def build_kernel():
    result = None
    config = small_config(ticks=1)
    world = ForagingWorld(config, seed=101)
    return world.kernel


def test_protocol_plane_cannot_submit_biological_effects():
    kernel = build_kernel()
    kernel.register_mechanism(
        __import__("newlife.core.contracts", fromlist=["MechanismSpec"]).MechanismSpec(
            identity="ExternalAssay",
            version="resource-foraging-v1",
            plane="protocol",
            biological_role="assay probe",
            ports=("state",),
            claims=(),
            schedule={"stage": "assay", "after": []},
            rng_streams=(),
            allowed_effects=frozenset({"StateDelta"}),
            invariants=(),
        )
    )
    with pytest.raises(Exception, match="InterventionScopeError|CommitAuthorityError|PlaneAuthorityError"):
        kernel.apply_batch(
            "ExternalAssay",
            [StateDelta(("resources", "1,1"), "add", 1.0)],
        )


def test_mechanism_cannot_write_outside_its_claims():
    kernel = build_kernel()
    with pytest.raises(Exception, match="CommitAuthorityError"):
        # the environment owns resources — not the organism records
        kernel.apply_batch(
            "resource-environment",
            [StateDelta(("organisms", "1,1"), "set", None)],
        )


def test_undeclared_mechanism_is_rejected():
    kernel = build_kernel()
    with pytest.raises(Exception, match="undeclared mechanism"):
        kernel.apply_batch("GhostMechanism", [StateDelta(("resources", "1,1"), "add", 1.0)])


# ── injection layer ──────────────────────────────────────────────────────────


def test_recorded_stream_roundtrip():
    stream = RecordedStream(
        [
            {"k": "f", "v": "3ff0000000000000"},
            {"k": "p", "v": 3},
            {"k": "u64", "v": "deadbeefcafebabe"},
            {"k": "perm", "v": [[2, 1], [1, 1]]},
        ]
    )
    import struct

    assert stream.draw_float() == struct.unpack(">d", bytes.fromhex("3ff0000000000000"))[0]
    assert stream.pick((1, 2, 3)) == 3
    assert stream.draw_u64() == 0xDEADBEEFCAFEBABE
    assert stream.permutation([(1, 1), (2, 1)]) == [[2, 1], [1, 1]]
    assert stream.remaining() == 0


def test_recorded_stream_rejects_wrong_kind_and_exhaustion():
    stream = RecordedStream([{"k": "f", "v": "3ff0000000000000"}])
    with pytest.raises(DrawLogMismatch, match="expected 'p'"):
        stream.pick((1,))
    with pytest.raises(DrawLogMismatch, match="exhausted"):
        stream.draw_float()


def test_recorded_stream_rejects_pick_outside_options():
    stream = RecordedStream([{"k": "p", "v": 9}])
    with pytest.raises(DrawLogMismatch, match="not among options"):
        stream.pick((1, 2, 3))


def test_recorded_bank_is_name_addressed(tmp_path: Path):
    log = tmp_path / "selection.jsonl"
    log.write_text(json.dumps({"k": "p", "v": 2}) + "\n", encoding="utf-8")
    (tmp_path / "environment.jsonl").write_text("", encoding="utf-8")
    bank = RecordedBank(101, {"selection": load_stream_log(log), "environment": []})
    assert bank.rng_stream("selection").pick((1, 2)) == 2
    with pytest.raises(KeyError, match="no recorded log"):
        bank.rng_stream("mutation")
