from __future__ import annotations

import pytest

from newlife.core.contracts import (
    ContractRegistry,
    MechanismSpec,
    Resolver,
    StateClaim,
    effect_tags,
)
from newlife.core.errors import (
    ClaimValidationError,
    ResolverRegistrationError,
    SpecValidationError,
    UnknownEffectKindError,
)


def spec(
    identity: str,
    *,
    plane: str = "biological",
    claims: tuple[StateClaim, ...] = (),
    effects: frozenset[str] = frozenset(),
) -> MechanismSpec:
    return MechanismSpec(
        identity=identity,
        version="1.0.0",
        plane=plane,
        biological_role="test-role",
        ports=("state",),
        claims=claims,
        schedule={"kind": "explicit"},
        rng_streams=(),
        allowed_effects=effects,
        invariants=("declared",),
    )


def test_effect_union_is_exactly_the_five_frozen_tags() -> None:
    assert effect_tags() == (
        "Contribution",
        "Event",
        "StateDelta",
        "StructuralRewrite",
        "Transfer",
    )


def test_sixth_effect_is_rejected_before_registry_mutation() -> None:
    registry = ContractRegistry()
    with pytest.raises(UnknownEffectKindError):
        registry.register_mechanism(spec("bad", effects=frozenset({"Teleport"})))
    assert dict(registry.mechanisms) == {}


@pytest.mark.parametrize("path", [(), ("population", "..", "genome"), ("",)])
def test_state_claim_requires_resolved_absolute_tuple(path: tuple[str, ...]) -> None:
    with pytest.raises(ClaimValidationError):
        StateClaim(path, "read")


def test_state_claim_permission_is_closed() -> None:
    with pytest.raises(ClaimValidationError):
        StateClaim(("population",), "write")


def test_management_plane_cannot_declare_effect_authority() -> None:
    with pytest.raises(SpecValidationError):
        spec("scheduler", plane="management", effects=frozenset({"StateDelta"}))


def test_mechanism_spec_requires_unique_ports_and_rng_streams() -> None:
    with pytest.raises(SpecValidationError):
        MechanismSpec(
            identity="mutation",
            version="1",
            plane="biological",
            biological_role="variation",
            ports=("state", "state"),
            claims=(),
            schedule={},
            rng_streams=("mutation", "mutation"),
            allowed_effects=frozenset(),
            invariants=(),
        )


def test_resolver_requires_exact_committer_and_contributors() -> None:
    target = ("cells", "mother", "position")
    registry = ContractRegistry()
    registry.register_mechanism(
        spec(
            "Adhesion",
            claims=(StateClaim(target, "contribute"),),
            effects=frozenset({"Contribution"}),
        )
    )
    registry.register_mechanism(
        spec(
            "Repulsion",
            claims=(StateClaim(target, "contribute"),),
            effects=frozenset({"Contribution"}),
        )
    )
    registry.register_mechanism(
        spec(
            "MechanicsResolver",
            claims=(StateClaim(target, "commit"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    resolver = Resolver(
        identity="MechanicsResolver",
        target_path=target,
        contributors=frozenset({"Adhesion", "Repulsion"}),
        invariants=("complete-source-set",),
    )
    registry.register_resolver(resolver)
    assert registry.resolvers["MechanicsResolver"] == resolver


def test_resolver_registration_is_atomic_on_contributor_mismatch() -> None:
    target = ("cells", "mother", "position")
    registry = ContractRegistry()
    registry.register_mechanism(
        spec(
            "MechanicsResolver",
            claims=(StateClaim(target, "commit"),),
            effects=frozenset({"StateDelta"}),
        )
    )
    with pytest.raises(ResolverRegistrationError):
        registry.register_resolver(
            Resolver(
                identity="MechanicsResolver",
                target_path=target,
                contributors=frozenset({"Missing"}),
                invariants=(),
            )
        )
    assert dict(registry.resolvers) == {}

