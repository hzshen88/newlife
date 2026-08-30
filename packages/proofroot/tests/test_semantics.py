"""D4 bank semantics invariants and D1/D2/D5 negative cases.

These encode the ported semantics themselves (the oracle vectors only cover
the positive seed derivations). The negative spellings here are the *ported*
boundaries: legacy encodings and legacy phase spellings must be rejected —
they stay in ParaLife's EvidenceCore.jl by design (§5.10 discipline 2).
"""

from __future__ import annotations

import pytest

from proofroot import (
    EVIDENCE_TIER_CONFIRMATORY,
    EVIDENCE_TIER_UNKNOWN,
    EVIDENCECORE_RNG_V1,
    RunPhase,
    RngBank,
    RngDerivationError,
    derive_stream_seed,
    parse_phase,
    resolve_evidence_tier,
)


class CountingStream:
    """Minimal stateful stand-in for a host generator: each object owns a
    draw counter that only moves forward."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self.draws = 0

    def advance(self) -> int:
        self.draws += 1
        return self.draws


def make_bank(names, factory=CountingStream, root_seed=42):
    return RngBank(root_seed, names, EVIDENCECORE_RNG_V1, stream_factory=factory)


# ── D4: declaration-time invariants ─────────────────────────────────────────


def test_bank_rejects_empty_names():
    with pytest.raises(RngDerivationError, match="at least one stream"):
        make_bank([])


def test_bank_rejects_duplicate_names():
    with pytest.raises(RngDerivationError, match="unique"):
        make_bank(["mutation", "mutation"])


@pytest.mark.parametrize("name", ["Mutation", "1stream", "_lead", "has space", "", "café"])
def test_bank_rejects_invalid_names(name):
    # Regex is checked on the declared name, before lowercasing — oracle parity.
    with pytest.raises(RngDerivationError, match="invalid RNG stream name"):
        make_bank([name])


def test_bank_rejects_out_of_range_root_seed():
    with pytest.raises(RngDerivationError):
        RngBank(-1, ["a"], EVIDENCECORE_RNG_V1)
    with pytest.raises(RngDerivationError):
        RngBank(1 << 64, ["a"], EVIDENCECORE_RNG_V1)


def test_bank_rejects_unknown_derivation_version():
    with pytest.raises(RngDerivationError, match="unknown rng derivation version"):
        RngBank(1, ["a"], "parcells-rng-v1")  # legacy: not ported


def test_bank_rejects_derived_seed_collision(monkeypatch):
    import proofroot.rng as rng_mod

    monkeypatch.setattr(rng_mod, "derive_stream_seed", lambda *a, **k: 12345)
    with pytest.raises(RngDerivationError, match="seed collision"):
        make_bank(["a", "b"])


# ── D4: lookup + forward-only semantics ─────────────────────────────────────


def test_rng_stream_is_case_insensitive_lookup():
    bank = make_bank(["mutation"])
    assert bank.rng_stream("MUTATION") is bank.rng_stream("mutation")


def test_undeclared_stream_is_an_error_not_a_new_stream():
    bank = make_bank(["mutation"])
    with pytest.raises(RngDerivationError, match="undeclared RNG stream"):
        bank.rng_stream("sampling")


def test_rng_stream_returns_cached_object_forward_only():
    bank = make_bank(["mutation", "sampling"])
    s = bank.rng_stream("mutation")
    assert bank.rng_stream("mutation") is s
    first, second = s.advance(), s.advance()
    assert (first, second) == (1, 2)  # advanced, never re-seeded
    other = bank.rng_stream("sampling")
    assert other is not s and other.advance() == 1


def test_stream_seeds_snapshot_is_a_copy():
    bank = make_bank(["mutation"])
    snap = bank.stream_seeds()
    snap["mutation"] = 0
    assert bank.stream_seeds()["mutation"] != 0


# ── D1: derivation boundaries ───────────────────────────────────────────────


def test_derive_rejects_legacy_versions():
    for legacy in ("parcells-rng-v1", "parreact-rng-v1", "parworlds-rng-v1"):
        with pytest.raises(RngDerivationError):
            derive_stream_seed(legacy, 1, "a")


def test_derive_rejects_out_of_range_root():
    with pytest.raises(RngDerivationError):
        derive_stream_seed(EVIDENCECORE_RNG_V1, -1, "a")


# ── D2: phase parsing boundaries ────────────────────────────────────────────


def test_parse_phase_accepts_titlecase():
    assert parse_phase("Running") is RunPhase.RUNNING
    assert parse_phase("Completed") is RunPhase.COMPLETED


@pytest.mark.parametrize("spelling", ["COMPLETED", "FAILED", "RUNNING", "running", ""])
def test_parse_phase_rejects_legacy_and_unknown_spellings(spelling):
    # Legacy UPPER-CASE spellings are ParaLife-local and deliberately unported.
    with pytest.raises(ValueError, match="unknown run phase"):
        parse_phase(spelling)


# ── D5: evidence tier safety direction ──────────────────────────────────────


def test_missing_tier_degrades_to_unknown_never_confirmatory():
    assert resolve_evidence_tier(None) == EVIDENCE_TIER_UNKNOWN


def test_declared_tier_passes_through():
    assert resolve_evidence_tier("confirmatory") == EVIDENCE_TIER_CONFIRMATORY
    assert resolve_evidence_tier("exploration") == "exploration"


@pytest.mark.parametrize("bad", ["CONFIRMATORY", "confirmatoy", "", "unknown "])
def test_tier_typo_raises_instead_of_failing_silently(bad):
    with pytest.raises(ValueError, match="unknown evidence tier"):
        resolve_evidence_tier(bad)
