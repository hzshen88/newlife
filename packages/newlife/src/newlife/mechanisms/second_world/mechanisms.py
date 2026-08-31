"""World 2 mechanism registry (Task 2, plan §7/R5): the coalescent
mechanism (`biological` plane) and the observer mechanism (`evidence`
plane) — the two-mechanism minimal shape R5 requires, bypassing
`staging.py` exactly as World 1 does (`world.py`'s step function contains
the entire `while(nchrom>1)` loop internally).

Both mechanisms call straight into `ms_coalescent.py`'s algorithm
functions rather than re-deriving them: what tier (b) tests (plan §8) is
whether `MechanismSpec`/`StructuralRewrite`/`Event`/`ReferenceKernel`
correctly carry this algorithm's state through the contract layer, not a
second, independently-drifting reimplementation of the algorithm itself
(already verified against real `ms` in Task 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from newlife.core.contracts import Event, MechanismSpec, StateClaim, StructuralRewrite
from newlife.mechanisms.second_world.ms_coalescent import (
    RecordedDrawStream,
    _build_coalescent_tree,
    _place_mutations,
    _poisso,
    _ttime,
)

PROTOCOL_VERSION = "second-world-v1"
TREE_PATH: tuple[str, ...] = ("second_world", "tree")


@dataclass(frozen=True)
class MechanismStep:
    effects: tuple[Any, ...]
    records: tuple[dict[str, Any], ...]


def build_mechanism_specs() -> list[MechanismSpec]:
    """The two registry entries (R5): the coalescent builder owns `TREE_PATH`
    and commits it exclusively via `StructuralRewrite`; the observer only
    reads it and emits its measurement as an `Event`."""
    return [
        MechanismSpec(
            identity="second-world-coalescent",
            version=PROTOCOL_VERSION,
            plane="biological",
            biological_role="coalescent tree construction (ms minimal model, R3)",
            ports=("state",),
            claims=(StateClaim(TREE_PATH, "own"),),
            schedule={"stage": "coalesce"},
            rng_streams=("ms-draws",),
            allowed_effects=frozenset({"StructuralRewrite"}),
            invariants=("second-world-ms-coalescent-v1",),
        ),
        MechanismSpec(
            identity="second-world-observer",
            version=PROTOCOL_VERSION,
            plane="evidence",
            biological_role="segsites/genotype observation over the committed tree",
            ports=("state",),
            claims=(StateClaim(TREE_PATH, "read"),),
            schedule={"stage": "observe", "after": ["coalesce"]},
            rng_streams=("ms-draws",),
            allowed_effects=frozenset({"Event"}),
            invariants=("second-world-ms-coalescent-v1",),
        ),
    ]


def coalescent_step(
    view: Mapping[tuple[str, ...], Any], *, nsam: int, draws: RecordedDrawStream
) -> MechanismStep:
    """R5: the entire coalescent loop runs inside this one step; each merge
    event becomes one `StructuralRewrite` (plan §7 Task 2), all applied as a
    single atomic batch by the reference kernel. `view` is unused — this
    mechanism computes the tree from local state and the draw stream, never
    from committed kernel state."""
    effects: list[StructuralRewrite] = []
    previous: dict | None = None  # TREE_PATH's initial kernel-state value

    def on_merge(after: dict) -> None:
        nonlocal previous
        effects.append(StructuralRewrite(TREE_PATH, previous, after))
        previous = after

    _build_coalescent_tree(nsam, draws, on_merge=on_merge)
    return MechanismStep(tuple(effects), ())


def observer_step(
    view: Mapping[tuple[str, ...], Any],
    *,
    nsam: int,
    theta: float,
    draws: RecordedDrawStream,
    replicate_index: int = 0,
) -> MechanismStep:
    """R5: reads the committed tree, places mutations, and emits the
    segsites count + genotype matrix as a real `Event` Effect (matching the
    `Event(event_type, source_id, payload)` + paired trace-record idiom
    already exercised by the contract-layer fixtures, e.g.
    `adapters/reference_kernel/cases.py`)."""
    tree = view[TREE_PATH]
    time = list(tree["time"])
    abv = list(tree["abv"])
    tt = _ttime(time, nsam)
    segsit = _poisso(theta * tt, draws)
    genotype_rows = _place_mutations(nsam, time, abv, tt, segsit, draws)

    payload = {"segsites": segsit, "genotype_rows": genotype_rows}
    event = Event("SegsitesObserved", "second-world-observer", payload)
    record = {
        "kind": "Event",
        "type": "SegsitesObserved",
        "payload": payload,
        "source": "second-world-observer",
        "time": str(replicate_index),
    }
    return MechanismStep((event,), (record,))
