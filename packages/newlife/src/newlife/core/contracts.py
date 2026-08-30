"""Closed contracts under test; no fixture-specific behavior lives here."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, Mapping, TypeAlias

from newlife.core.errors import (
    ClaimValidationError,
    ResolverRegistrationError,
    SpecValidationError,
    UnknownEffectKindError,
)


Path = tuple[str, ...]
Permission = Literal["read", "own", "contribute", "commit"]
Plane = Literal["biological", "protocol", "evidence", "management"]
Operation = Literal["add", "set"]

PERMISSIONS = frozenset({"read", "own", "contribute", "commit"})
PLANES = frozenset({"biological", "protocol", "evidence", "management"})
OPERATIONS = frozenset({"add", "set"})
EFFECT_TAGS = (
    "Contribution",
    "Event",
    "StateDelta",
    "StructuralRewrite",
    "Transfer",
)


def _validate_path(path: Path) -> None:
    if not isinstance(path, tuple) or not path:
        raise ClaimValidationError("state path must be a non-empty absolute tuple")
    if any(not isinstance(part, str) or not part or part in {".", ".."} for part in path):
        raise ClaimValidationError(f"invalid absolute state path: {path!r}")


@dataclass(frozen=True, slots=True)
class StateClaim:
    path: Path
    permission: Permission

    def __post_init__(self) -> None:
        _validate_path(self.path)
        if self.permission not in PERMISSIONS:
            raise ClaimValidationError(f"unknown permission: {self.permission!r}")


@dataclass(frozen=True, slots=True)
class StateDelta:
    path: Path
    operation: Operation
    value: Any
    kind: str = field(default="StateDelta", init=False)

    def __post_init__(self) -> None:
        _validate_path(self.path)
        if self.operation not in OPERATIONS:
            raise SpecValidationError(f"unknown StateDelta operation: {self.operation!r}")


@dataclass(frozen=True, slots=True)
class Transfer:
    source_path: Path
    destination_path: Path
    amount: Any
    kind: str = field(default="Transfer", init=False)

    def __post_init__(self) -> None:
        _validate_path(self.source_path)
        _validate_path(self.destination_path)
        if self.source_path == self.destination_path:
            raise SpecValidationError("Transfer paths must be distinct")


@dataclass(frozen=True, slots=True)
class Contribution:
    resolver_id: str
    target_path: Path
    source_id: str
    value: Any
    kind: str = field(default="Contribution", init=False)

    def __post_init__(self) -> None:
        _validate_path(self.target_path)
        if not self.resolver_id or not self.source_id:
            raise SpecValidationError("Contribution identities must be non-empty")


@dataclass(frozen=True, slots=True)
class StructuralRewrite:
    target_path: Path
    before: Any
    after: Any
    kind: str = field(default="StructuralRewrite", init=False)

    def __post_init__(self) -> None:
        _validate_path(self.target_path)


@dataclass(frozen=True, slots=True)
class Event:
    event_type: str
    source_id: str
    payload: Mapping[str, Any]
    kind: str = field(default="Event", init=False)

    def __post_init__(self) -> None:
        if not self.event_type or not self.source_id:
            raise SpecValidationError("Event identities must be non-empty")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


Effect: TypeAlias = StateDelta | Transfer | Contribution | StructuralRewrite | Event


@dataclass(frozen=True, slots=True)
class MechanismSpec:
    identity: str
    version: str
    plane: Plane
    biological_role: str
    ports: tuple[str, ...]
    claims: tuple[StateClaim, ...]
    schedule: Mapping[str, Any]
    rng_streams: tuple[str, ...]
    allowed_effects: frozenset[str]
    invariants: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.identity or not self.version or not self.biological_role:
            raise SpecValidationError("identity, version, and role are required")
        if self.plane not in PLANES:
            raise SpecValidationError(f"unknown plane: {self.plane!r}")
        if len(set(self.ports)) != len(self.ports):
            raise SpecValidationError("ports must be unique")
        if len(set(self.rng_streams)) != len(self.rng_streams):
            raise SpecValidationError("RNG stream names must be unique")
        unknown = sorted(self.allowed_effects - set(EFFECT_TAGS))
        if unknown:
            raise UnknownEffectKindError(f"unknown Effect kinds: {unknown}")
        if self.plane == "management" and self.allowed_effects:
            raise SpecValidationError("management components cannot submit Effects")
        object.__setattr__(self, "schedule", MappingProxyType(dict(self.schedule)))


@dataclass(frozen=True, slots=True)
class Resolver:
    identity: str
    target_path: Path
    contributors: frozenset[str]
    invariants: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.identity:
            raise ResolverRegistrationError("resolver identity is required")
        _validate_path(self.target_path)
        if not self.contributors:
            raise ResolverRegistrationError("resolver needs a declared contributor set")


class ContractRegistry:
    """Atomic registry for mechanism and Resolver declarations."""

    def __init__(self) -> None:
        self._mechanisms: dict[str, MechanismSpec] = {}
        self._resolvers: dict[str, Resolver] = {}
        self._resolver_by_path: dict[Path, str] = {}

    @property
    def mechanisms(self) -> Mapping[str, MechanismSpec]:
        return MappingProxyType(self._mechanisms)

    @property
    def resolvers(self) -> Mapping[str, Resolver]:
        return MappingProxyType(self._resolvers)

    def register_mechanism(self, spec: MechanismSpec) -> None:
        if spec.identity in self._mechanisms:
            raise SpecValidationError(f"duplicate mechanism: {spec.identity}")
        self._mechanisms[spec.identity] = spec

    def register_resolver(self, resolver: Resolver) -> None:
        if resolver.identity in self._resolvers:
            raise ResolverRegistrationError(f"duplicate resolver: {resolver.identity}")
        if resolver.target_path in self._resolver_by_path:
            raise ResolverRegistrationError(
                f"target already has a resolver: {resolver.target_path!r}"
            )
        resolver_spec = self._mechanisms.get(resolver.identity)
        if resolver_spec is None:
            raise ResolverRegistrationError("resolver has no MechanismSpec")
        commit_claims = {
            claim.path
            for claim in resolver_spec.claims
            if claim.permission == "commit"
        }
        if commit_claims != {resolver.target_path}:
            raise ResolverRegistrationError("resolver commit claim is not exact")
        for contributor_id in sorted(resolver.contributors):
            contributor = self._mechanisms.get(contributor_id)
            if contributor is None:
                raise ResolverRegistrationError(
                    f"undeclared contributor: {contributor_id}"
                )
            claims = {
                claim.path
                for claim in contributor.claims
                if claim.permission == "contribute"
            }
            if resolver.target_path not in claims:
                raise ResolverRegistrationError(
                    f"contributor claim mismatch: {contributor_id}"
                )
        self._resolvers[resolver.identity] = resolver
        self._resolver_by_path[resolver.target_path] = resolver.identity


def effect_tags() -> tuple[str, ...]:
    return EFFECT_TAGS

