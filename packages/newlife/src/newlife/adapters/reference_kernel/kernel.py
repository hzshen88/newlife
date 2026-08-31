"""Small generic kernel implementing only the four frozen contracts."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from collections.abc import Mapping as ABCMapping, Sequence as ABCSequence
from typing import Any, Callable, Iterable, Mapping

from newlife.adapters.reference_kernel.lowering import (
    apply_op,
    apply_op_cow,
    get_path,
    numeric_add,
    set_path,
)
from newlife.core.lowering_contract import lower_effect

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
    DuplicateContributionError,
    IncompleteContributionSetError,
    InterventionScopeError,
    PlaneAuthorityError,
    ReadOnlyStateError,
    SpecValidationError,
    StatePathError,
    StructuralOwnershipConflictError,
    UnknownContributionError,
)
from newlife.conform.contract.canonical_ruler import canonical_bytes


TraceRecord = dict[str, Any]
ResolverPolicy = Callable[[Any, tuple[Contribution, ...]], tuple[Any, Mapping[str, Any]]]


class _ReadOnlyMapping(ABCMapping):
    """Lazy read-only facade over a nested state mapping."""

    __slots__ = ("_value",)

    def __init__(self, value: Mapping[str, Any]) -> None:
        self._value = value

    def __getitem__(self, key: str) -> Any:
        return _read_only(self._value[key])

    def __iter__(self):
        return iter(self._value)

    def __len__(self) -> int:
        return len(self._value)


class _ReadOnlySequence(ABCSequence):
    """Lazy read-only facade over a nested state list."""

    __slots__ = ("_value",)

    def __init__(self, value: list[Any]) -> None:
        self._value = value

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(_read_only(value) for value in self._value[index])
        return _read_only(self._value[index])

    def __len__(self) -> int:
        return len(self._value)


def _read_only(value: Any) -> Any:
    if isinstance(value, dict):
        return _ReadOnlyMapping(value)
    if isinstance(value, list):
        return _ReadOnlySequence(value)
    if isinstance(value, tuple):
        return tuple(_read_only(item) for item in value)
    return value


class _ReadOnlyView(ABCMapping):
    """Lazy path-addressed view used by large declared world stages."""

    __slots__ = ("_state", "_paths")

    def __init__(self, state: Mapping[str, Any], paths: set[tuple[str, ...]]) -> None:
        self._state = state
        self._paths = paths

    def __getitem__(self, path: tuple[str, ...]) -> Any:
        if path not in self._paths:
            raise KeyError(path)
        return _read_only(get_path(self._state, path))

    def __iter__(self):
        return iter(self._paths)

    def __len__(self) -> int:
        return len(self._paths)


@dataclass(frozen=True, slots=True)
class CaseResult:
    fixture: str
    target: str
    final_state: dict[str, Any]
    trace: list[TraceRecord]
    negative_results: list[dict[str, Any]]
    assertions: dict[str, bool]
    metadata: dict[str, Any]


class ReferenceKernel:
    """Effect authorizer and atomic committer with no scenario dispatch."""

    def __init__(self, initial_state: Mapping[str, Any]) -> None:
        self.state: dict[str, Any] = copy.deepcopy(dict(initial_state))
        self.trace: list[TraceRecord] = []
        self.registry = ContractRegistry()
        self._structural_owners: dict[tuple[str, ...], str] = {}
        # (identity → {(path, permission)}) index for O(1) authorization —
        # world-scale mechanisms carry per-cell claims; per-mechanism scope
        # keeps authorization semantics identical. Pure speed.
        self._claim_index: dict[str, set[tuple[tuple[str, ...], str]]] = {}

    def register_mechanism(self, spec: MechanismSpec) -> None:
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
        self._claim_index[spec.identity] = {
            (claim.path, claim.permission) for claim in spec.claims
        }
        for path in structural_paths:
            self._structural_owners[path] = spec.identity

    def register_resolver(self, resolver: Resolver) -> None:
        self.registry.register_resolver(resolver)

    def _spec(self, source_id: str) -> MechanismSpec:
        try:
            return self.registry.mechanisms[source_id]
        except KeyError as error:
            raise SpecValidationError(f"undeclared mechanism: {source_id}") from error

    def _has_claim(self, spec: MechanismSpec, path: tuple[str, ...], *permissions: str) -> bool:
        indexed = self._claim_index.get(spec.identity)
        if indexed is not None:
            return any((path, permission) in indexed for permission in permissions)
        return any(
            claim.path == path and claim.permission in permissions for claim in spec.claims
        )

    def _authorize(self, spec: MechanismSpec, effect: Effect) -> None:
        if spec.plane == "management":
            raise PlaneAuthorityError(f"management component {spec.identity} submitted an Effect")
        if effect.kind not in spec.allowed_effects:
            raise CommitAuthorityError(
                f"{spec.identity} did not declare Effect {effect.kind}"
            )
        if isinstance(effect, StateDelta):
            if not self._has_claim(spec, effect.path, "own", "commit"):
                if spec.plane == "protocol":
                    raise InterventionScopeError(
                        f"intervention {spec.identity} cannot write {effect.path!r}"
                    )
                raise CommitAuthorityError(
                    f"{spec.identity} cannot commit {effect.path!r}"
                )
        elif isinstance(effect, Transfer):
            if not self._has_claim(spec, effect.source_path, "own") or not self._has_claim(
                spec, effect.destination_path, "own"
            ):
                raise CommitAuthorityError(f"{spec.identity} cannot commit both Transfer paths")
        elif isinstance(effect, Contribution):
            if effect.source_id != spec.identity:
                raise CommitAuthorityError(
                    f"Contribution source {effect.source_id} does not match {spec.identity}"
                )
            if not self._has_claim(spec, effect.target_path, "contribute"):
                raise CommitAuthorityError(
                    f"{spec.identity} cannot contribute to {effect.target_path!r}"
                )
        elif isinstance(effect, StructuralRewrite):
            if not self._has_claim(spec, effect.target_path, "own"):
                raise CommitAuthorityError(
                    f"{spec.identity} cannot rewrite {effect.target_path!r}"
                )
        elif isinstance(effect, Event):
            if effect.source_id != spec.identity:
                raise CommitAuthorityError(
                    f"Event source {effect.source_id} does not match {spec.identity}"
                )
        else:
            raise AssertionError(f"unreachable Effect type: {type(effect).__name__}")

    def _apply_to(
        self,
        state: dict[str, Any],
        effect: Effect,
        *,
        provenance: str,
        copied_paths: set[tuple[str, ...]] | None = None,
    ) -> None:
        # Single write path: every state change goes through the IR lowering
        # (core contract) and this adapter's op application. The kernel never
        # branches on Effect types directly.
        op = lower_effect(effect, provenance=provenance)
        if copied_paths is None:
            apply_op(state, op)
        else:
            apply_op_cow(state, op, copied_paths)

    def apply_batch(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[TraceRecord] = (),
    ) -> None:
        """Validate and stage a complete batch before one state/trace swap."""

        spec = self._spec(source_id)
        staged_state = copy.deepcopy(self.state)
        # Existing trace records are immutable from the kernel's point of
        # view: a batch only appends new records.  Copy the list structure,
        # not the entire history, so long-running worlds do not pay an
        # O(history) deep-copy cost at every stage.  New records are still
        # deep-copied at the commit boundary below.
        staged_trace = list(self.trace)
        for effect in tuple(effects):
            self._authorize(spec, effect)
            self._apply_to(staged_state, effect, provenance=spec.identity)
        staged_trace.extend(copy.deepcopy(list(trace_records)))
        self.state = staged_state
        self.trace = staged_trace

    def apply_batch_fast(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[TraceRecord] = (),
    ) -> None:
        """Commit a batch with the same checks using transactional COW.

        This is an execution optimization for large declared worlds. The
        ordinary ``apply_batch`` remains the fully deep-copied reference path
        used by contract fixtures and tamper controls; this path preserves
        atomicity by copying only mappings reached by a write and replacing
        the state root only after the complete batch succeeds.
        """
        spec = self._spec(source_id)
        staged_state = dict(self.state)
        copied_paths: set[tuple[str, ...]] = set()
        for effect in tuple(effects):
            self._authorize(spec, effect)
            self._apply_to(
                staged_state,
                effect,
                provenance=spec.identity,
                copied_paths=copied_paths,
            )
        staged_trace = list(self.trace)
        staged_trace.extend(copy.deepcopy(list(trace_records)))
        self.state = staged_state
        self.trace = staged_trace

    def resolve(
        self,
        resolver_id: str,
        contributions: Iterable[Contribution],
        *,
        time: str,
        policy: ResolverPolicy,
    ) -> None:
        """Validate a complete contribution set and perform its sole atomic commit."""

        resolver = self.registry.resolvers[resolver_id]
        items = tuple(sorted(contributions, key=lambda item: item.source_id))
        sources = [item.source_id for item in items]
        if len(sources) != len(set(sources)):
            raise DuplicateContributionError(f"duplicate contribution source: {sources}")
        unknown = sorted(set(sources) - resolver.contributors)
        if unknown:
            raise UnknownContributionError(f"unknown contribution source: {unknown}")
        missing = sorted(resolver.contributors - set(sources))
        if missing:
            raise IncompleteContributionSetError(f"missing contribution source: {missing}")
        for item in items:
            if item.resolver_id != resolver_id or item.target_path != resolver.target_path:
                raise UnknownContributionError("contribution envelope does not match Resolver")
            self._authorize(self._spec(item.source_id), item)

        staged_state = dict(self.state)
        copied_paths: set[tuple[str, ...]] = set()
        # As in apply_batch, the resolver only appends records.  Keeping the
        # old prefix shared is safe because commit replaces the trace list;
        # copy the newly accepted records before they cross the boundary.
        staged_trace = list(self.trace)
        for item in items:
            if isinstance(item.value, Mapping):
                payload = copy.deepcopy(dict(item.value))
                payload["resolver_id"] = resolver_id
                record = {
                    "kind": "ContributionAccepted",
                    "payload": payload,
                    "source": item.source_id,
                    "time": time,
                }
            else:
                record = {
                    "kind": "ContributionAccepted",
                    "resolver_id": resolver_id,
                    "source": item.source_id,
                    "target_path": list(item.target_path),
                    "time": time,
                    "value": item.value,
                }
            staged_trace.append(record)

        before = copy.deepcopy(get_path(staged_state, resolver.target_path))
        after, details = policy(before, items)
        commit_effect = StateDelta(resolver.target_path, "set", after)
        resolver_spec = self._spec(resolver_id)
        self._authorize(resolver_spec, commit_effect)
        self._apply_to(
            staged_state,
            commit_effect,
            provenance=resolver_id,
            copied_paths=copied_paths,
        )
        commit_record: TraceRecord = {
            "contributors": sources,
            "kind": "ResolverCommit",
            "source": resolver_id,
            "target_path": list(resolver.target_path),
            "time": time,
        }
        commit_record.update(copy.deepcopy(dict(details)))
        staged_trace.append(commit_record)
        self.state = staged_state
        self.trace = staged_trace

    def guarded_read(self, source_id: str, callback: Callable[[dict[str, Any]], Any]) -> Any:
        spec = self._spec(source_id)
        readable = {
            claim.path: copy.deepcopy(get_path(self.state, claim.path))
            for claim in spec.claims
            if claim.permission == "read"
        }
        serializable = lambda: {
            "/".join(path): value for path, value in readable.items()
        }
        before = canonical_bytes(serializable())
        result = callback(readable)
        if canonical_bytes(serializable()) != before:
            raise ReadOnlyStateError(f"{source_id} mutated a guarded read view")
        return result

    def guarded_read_fast(
        self, source_id: str, callback: Callable[[Mapping[tuple[str, ...], Any]], Any]
    ) -> Any:
        """Read through lazy immutable facades for large world stages.

        Unlike the public oracle path above, this avoids copying and
        canonicalizing every declared read path on every stage. Nested dicts
        and lists are exposed only through read-only facades, so a stage cannot
        mutate committed state through its view; the transaction still commits
        through ``apply_batch_fast`` after the callback returns.
        """
        spec = self._spec(source_id)
        paths = {claim.path for claim in spec.claims if claim.permission == "read"}
        return callback(_ReadOnlyView(self.state, paths))
