"""World 2 runtime driver (Task 2, plan §7): registers the two-mechanism
registry (R5) and runs one coalescent replicate over the reference kernel —
mirroring World 1's own hand-written tick loop rather than `staging.py`, a
second real-world precedent for bypassing it (R5).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.mechanisms.second_world import mechanisms as mech
from newlife.mechanisms.second_world.rng_mapping import (
    derived_seed_to_ms_triple,
    pack_ms_triple,
)
from proofroot import EVIDENCECORE_RNG_V1, RngBank

TREE_PATH = mech.TREE_PATH


class DevDrawStream:
    """Host-choice generator for non-frozen-grid, non-comparison runs
    (development only — never for the `ms`-comparison grid, which always
    replays a real binary's own logged draws). Mirrors World 1's
    `DevStream` (`resource_foraging/injection.py`)."""

    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def next(self) -> float:
        return self._rng.random()


@dataclass(frozen=True)
class ReplicateOutcome:
    segsites: int
    genotype_rows: list[str]


class CoalescentWorld:
    """One `ms` "gene tree" plus its placed mutations, expressed as a
    two-mechanism registry over the reference kernel (R5). `draws` is
    injected directly — this world has no `RngBank` of its own; see
    `run_from_rng_bank` below for the R2-integrated path."""

    def __init__(
        self, nsam: int, theta: float, draws: Any, *, replicate_index: int = 0
    ) -> None:
        self.nsam = nsam
        self.theta = theta
        self.draws = draws
        self.replicate_index = replicate_index
        self.kernel = ReferenceKernel({"second_world": {"tree": None}})
        for spec in mech.build_mechanism_specs():
            self.kernel.register_mechanism(spec)

    def _run_stage(
        self,
        identity: str,
        step: Callable[[Mapping[tuple[str, ...], Any]], mech.MechanismStep],
    ) -> mech.MechanismStep:
        result = self.kernel.guarded_read_fast(identity, step)
        self.kernel.apply_batch_fast(
            identity, list(result.effects), list(result.records)
        )
        return result

    def run(self) -> ReplicateOutcome:
        self._run_stage(
            "second-world-coalescent",
            lambda view: mech.coalescent_step(view, nsam=self.nsam, draws=self.draws),
        )
        observer_result = self._run_stage(
            "second-world-observer",
            lambda view: mech.observer_step(
                view,
                nsam=self.nsam,
                theta=self.theta,
                draws=self.draws,
                replicate_index=self.replicate_index,
            ),
        )
        payload = observer_result.records[0]["payload"]
        return ReplicateOutcome(
            segsites=payload["segsites"], genotype_rows=list(payload["genotype_rows"])
        )


def run_from_rng_bank(root_seed: int, nsam: int, theta: float) -> ReplicateOutcome:
    """Task 2's separate, non-frozen-grid demonstration (plan §7): integrates
    `RngBank` with R2's mapping end-to-end (`derive_stream_seed` -> R2's
    truncate-and-split -> repack -> a runnable draw stream). Does not need
    to match `ms`'s output — no `ms` run ever uses a derived seed — only to
    run without error and produce a valid tree."""

    def stream_factory(derived_seed: int) -> DevDrawStream:
        triple = derived_seed_to_ms_triple(derived_seed)
        return DevDrawStream(pack_ms_triple(triple))

    bank = RngBank(
        root_seed, ["ms-draws"], EVIDENCECORE_RNG_V1, stream_factory=stream_factory
    )
    draws = bank.rng_stream("ms-draws")
    return CoalescentWorld(nsam, theta, draws).run()
