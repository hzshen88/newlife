"""Versioned scientific profile over Process-Bigraph's public extension surface.

v0.1a single-write-path port: `Proposal` carries Effects and trace records
only — the free hand-written update channel is deleted. `update()` derives
its output solely from the validated Effects via this adapter's lowering
dispatch (R4).
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Mapping

from bigraph_schema.methods import apply, reconcile
from bigraph_schema.schema import Float
from process_bigraph import Composite, Process, Step, allocate_core

from newlife.core.contracts import (
    ContractRegistry,
    Contribution,
    Effect,
    Event,
    MechanismSpec,
    Resolver,
    StateDelta,
    StructuralRewrite,
    Transfer,
)
from newlife.core.errors import (
    CommitAuthorityError,
    InterventionScopeError,
    PlaneAuthorityError,
    ReadOnlyStateError,
    SpecValidationError,
    StructuralOwnershipConflictError,
)
from newlife.conform.contract.canonical_ruler import canonical_bytes


PROFILE_VERSION = "2.1.0"  # 2.1.0: staging schema v1 on the schedule field (v0.1b)
_ACTIVE_PROFILE: ContextVar[BiologicalProfile | None] = ContextVar(
    "biosim_pressure_profile", default=None
)


@dataclass(frozen=True, slots=True)
class Proposal:
    effects: tuple[Effect, ...]
    trace_records: tuple[dict[str, Any], ...] = ()


def _lower_update(
    wrapper: GuardedProcess | GuardedStep,
    effects: tuple[Effect, ...],
    state_view: dict[str, Any],
    interval: float,
) -> dict[str, Any]:
    """Derive the engine update mechanically from validated Effects only
    (the former free-form hand-written channel no longer exists)."""
    from newlife.adapters.process_bigraph.lowering import lower_update

    return lower_update(
        wrapper.config["mechanism_id"],
        getattr(type(wrapper), "lowering_table", {}),
        effects,
        state_view,
        interval,
    )


class BiologicalProfile:
    """Generic path-authority and trace boundary missing from the bare engine."""

    version = PROFILE_VERSION

    def __init__(self) -> None:
        self.registry = ContractRegistry()
        self.pending_trace: list[dict[str, Any]] = []
        self.runtime_audit: list[dict[str, Any]] = []
        self.runtime_nodes: dict[str, str] = {}
        self._structural_owners: dict[tuple[str, ...], str] = {}

    def register_mechanism(self, spec: MechanismSpec, runtime_node: str | None = None) -> None:
        structural_paths = {
            claim.path
            for claim in spec.claims
            if claim.permission == "own" and "StructuralRewrite" in spec.allowed_effects
        }
        for path in structural_paths:
            owner = self._structural_owners.get(path)
            if owner is not None:
                raise StructuralOwnershipConflictError(
                    f"structural path {path!r} already owned by {owner}"
                )
        self.registry.register_mechanism(spec)
        if runtime_node is not None:
            if runtime_node in self.runtime_nodes:
                raise SpecValidationError(f"duplicate runtime node: {runtime_node}")
            self.runtime_nodes[runtime_node] = spec.identity
        for path in structural_paths:
            self._structural_owners[path] = spec.identity

    def register_resolver(self, resolver: Resolver) -> None:
        self.registry.register_resolver(resolver)

    def _has_claim(self, spec: MechanismSpec, path: tuple[str, ...], *permissions: str) -> bool:
        return any(
            claim.path == path and claim.permission in permissions for claim in spec.claims
        )

    def validate(self, mechanism_id: str, effects: Iterable[Effect]) -> None:
        try:
            spec = self.registry.mechanisms[mechanism_id]
        except KeyError as error:
            raise SpecValidationError(f"undeclared mechanism: {mechanism_id}") from error
        for effect in effects:
            if spec.plane == "management":
                raise PlaneAuthorityError(
                    f"management component {mechanism_id} submitted an Effect"
                )
            if effect.kind not in spec.allowed_effects:
                raise CommitAuthorityError(
                    f"{mechanism_id} did not declare Effect {effect.kind}"
                )
            if isinstance(effect, StateDelta):
                if not self._has_claim(spec, effect.path, "own", "commit"):
                    if spec.plane == "protocol":
                        raise InterventionScopeError(
                            f"intervention {mechanism_id} cannot write {effect.path!r}"
                        )
                    raise CommitAuthorityError(
                        f"{mechanism_id} cannot commit {effect.path!r}"
                    )
            elif isinstance(effect, Transfer):
                if not self._has_claim(spec, effect.source_path, "own") or not self._has_claim(
                    spec, effect.destination_path, "own"
                ):
                    raise CommitAuthorityError(
                        f"{mechanism_id} cannot commit both Transfer paths"
                    )
            elif isinstance(effect, Contribution):
                if effect.source_id != mechanism_id or not self._has_claim(
                    spec, effect.target_path, "contribute"
                ):
                    raise CommitAuthorityError(
                        f"{mechanism_id} has invalid Contribution authority"
                    )
            elif isinstance(effect, StructuralRewrite):
                if not self._has_claim(spec, effect.target_path, "own"):
                    raise CommitAuthorityError(
                        f"{mechanism_id} cannot rewrite {effect.target_path!r}"
                    )
            elif isinstance(effect, Event):
                if effect.source_id != mechanism_id:
                    raise CommitAuthorityError(
                        f"Event source {effect.source_id} does not match {mechanism_id}"
                    )
            else:
                raise AssertionError(type(effect).__name__)

    def stage(self, mechanism_id: str, proposal: Proposal) -> tuple[Effect, ...]:
        self.validate(mechanism_id, proposal.effects)
        self.pending_trace.extend(copy.deepcopy(list(proposal.trace_records)))
        # Effects are passed through, not copied: Event payloads are frozen
        # into an immutable mapping view at construction, and the write
        # boundary (`update`'s deep-copied return) provides the alias
        # isolation the side-channel negative requires.
        return tuple(proposal.effects)

    def take_trace(self) -> list[dict[str, Any]]:
        trace = copy.deepcopy(self.pending_trace)
        self.pending_trace.clear()
        return trace

    def assert_one_mechanism_per_node(self) -> bool:
        return len(self.runtime_nodes) == len(set(self.runtime_nodes.values()))


def active_profile() -> BiologicalProfile:
    profile = _ACTIVE_PROFILE.get()
    if profile is None:
        raise RuntimeError("no active BiologicalProfile")
    return profile


@contextmanager
def activate_profile(profile: BiologicalProfile) -> Iterator[None]:
    token = _ACTIVE_PROFILE.set(profile)
    try:
        yield
    finally:
        _ACTIVE_PROFILE.reset(token)


class GuardedProcess(Process):
    """One generic wrapper instance authorizes exactly one named mechanism."""

    config_schema = {"mechanism_id": "string"}

    def propose(self, state: dict[str, Any], interval: float) -> Proposal:
        raise NotImplementedError

    def update(self, state, interval=-1.0):
        working = copy.deepcopy(state)
        before = canonical_bytes(working)
        proposal = self.propose(working, interval)
        if canonical_bytes(working) != before:
            raise ReadOnlyStateError(
                f"{self.config['mechanism_id']} mutated its input view"
            )
        staged_effects = active_profile().stage(self.config["mechanism_id"], proposal)
        return copy.deepcopy(_lower_update(self, staged_effects, working, interval))


class GuardedStep(Step):
    """Step counterpart of GuardedProcess with the same contract boundary."""

    config_schema = {"mechanism_id": "string"}

    def propose(self, state: dict[str, Any], interval: float) -> Proposal:
        raise NotImplementedError

    def update(self, state, interval=-1.0):
        working = copy.deepcopy(state)
        before = canonical_bytes(working)
        proposal = self.propose(working, interval)
        if canonical_bytes(working) != before:
            raise ReadOnlyStateError(
                f"{self.config['mechanism_id']} mutated its input view"
            )
        staged_effects = active_profile().stage(self.config["mechanism_id"], proposal)
        return copy.deepcopy(_lower_update(self, staged_effects, working, interval))


def run_composite(composite: Composite, duration: float, profile: BiologicalProfile) -> None:
    trace_length = len(profile.pending_trace)
    audit_length = len(profile.runtime_audit)
    try:
        with activate_profile(profile):
            composite.run(duration)
    except Exception:
        del profile.pending_trace[trace_length:]
        del profile.runtime_audit[audit_length:]
        raise


@dataclass(kw_only=True)
class ResolvedPosition(Float):
    """Numeric state whose updates retain named contribution provenance."""


@reconcile.dispatch
def reconcile_resolved_position(
    schema: ResolvedPosition, updates: list
) -> dict[str, Any] | None:
    del schema
    present = [update for update in updates if update is not None]
    if not present:
        return None
    sources = [str(update["source"]) for update in present]
    if len(sources) != len(set(sources)):
        raise ValueError(f"duplicate contribution source: {sources}")
    resolver_ids = {str(update["resolver_id"]) for update in present}
    if len(resolver_ids) != 1:
        raise ValueError(f"inconsistent resolver identities: {sorted(resolver_ids)}")
    profile = active_profile()
    resolver_id = next(iter(resolver_ids))
    if resolver_id in profile.registry.resolvers:
        declared = profile.registry.resolvers[resolver_id].contributors
        if set(sources) != declared:
            raise ValueError(
                f"incomplete contribution set for {resolver_id}: {sorted(sources)}"
            )
    resolved = {
        "sources": sorted(sources),
        "delta": sum(float(update["delta"]) for update in present),
        "resolver_id": resolver_id,
        "time": str(present[0]["time"]),
    }
    profile.runtime_audit.append({"stage": "reconcile", **copy.deepcopy(resolved)})
    return resolved


@apply.dispatch
def apply_resolved_position(schema: ResolvedPosition, state, update, path):
    del schema
    if update is None:
        return state, []
    after = float(state or 0.0) + float(update["delta"])
    sources = (
        list(update["sources"])
        if "sources" in update
        else [str(update["source"])]
    )
    profile = active_profile()
    profile.runtime_audit.append(
        {
            "stage": "apply",
            "before": float(state or 0.0),
            "after": after,
            "sources": sources,
        }
    )
    if "resolver_id" in update:
        profile.pending_trace.append(
            {
                "after": str(after),
                "before": str(state),
                "contributors": sources,
                "kind": "ResolverCommit",
                "resolved_delta": str(update["delta"]),
                "source": str(update["resolver_id"]),
                "target_path": list(path),
                "time": str(update["time"]),
            }
        )
    return after, []


def allocate_profile_core(*process_types: tuple[str, type[Process]]):
    core = allocate_core()
    core.register_type("biosim_resolved_position_v1", ResolvedPosition)
    for address, process_type in process_types:
        core.register_link(address, process_type)
    return core


def process_node(
    address: str,
    mechanism_id: str,
    *,
    inputs: dict[str, list[str]],
    outputs: dict[str, list[str]],
    interval: float,
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    node_config = {"mechanism_id": mechanism_id}
    if config:
        node_config.update(copy.deepcopy(dict(config)))
    return {
        "_type": "process",
        "address": f"local:{address}",
        "config": node_config,
        "inputs": copy.deepcopy(inputs),
        "outputs": copy.deepcopy(outputs),
        "interval": interval,
    }


def step_node(
    address: str,
    mechanism_id: str,
    *,
    inputs: dict[str, list[str]],
    outputs: dict[str, list[str]],
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    node = process_node(
        address,
        mechanism_id,
        inputs=inputs,
        outputs=outputs,
        interval=1.0,
        config=config,
    )
    node["_type"] = "step"
    node.pop("interval")
    return node
