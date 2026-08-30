"""proofroot — language-neutral trust core for reproducible simulation.

Scope (frozen charter, see docs/design/proposal.md §5.10):
- D1 current encoding (`evidencecore-rng-v1`) named RNG stream seed derivation
- D4 bank semantics invariants (declared streams, lowercase normalization,
  name regex, forward-only, seed snapshots as provenance)
- D2 RunPhase + terminal-state decision; D5 evidence tier vocabulary
  (exploration/confirmatory/unknown; missing fields default to unknown,
  never to confirmatory)
- Canonical serialization spec (RFC 8785 structural rules, IEEE754 bit-pattern
  float comparison) + cross-language test vectors

Excluded on purpose: Effect-typed trace schemas, attribution/compare logic,
manifest assembly, and all domain semantics. Legacy ParaLife compatibility
layers (parcells-rng-v1, parreact-rng-v1, parworlds-rng-v1 string encodings,
legacy UPPER-CASE phase spellings) stay in ParaLife's EvidenceCore.jl and are
deliberately NOT ported here.
"""

from .canonical import bits_to_float, canonical_bytes, float_to_bits
from .phase import (
    EVIDENCE_TIER_CONFIRMATORY,
    EVIDENCE_TIER_EXPLORATION,
    EVIDENCE_TIER_UNKNOWN,
    EVIDENCE_TIERS,
    RunPhase,
    is_terminal,
    parse_phase,
    resolve_evidence_tier,
)
from .rng import (
    EVIDENCECORE_RNG_V1,
    RngBank,
    RngDerivationError,
    derive_stream_seed,
)

__all__ = [
    "EVIDENCECORE_RNG_V1",
    "bits_to_float",
    "canonical_bytes",
    "float_to_bits",
    "EVIDENCE_TIER_CONFIRMATORY",
    "EVIDENCE_TIER_EXPLORATION",
    "EVIDENCE_TIER_UNKNOWN",
    "EVIDENCE_TIERS",
    "RunPhase",
    "RngBank",
    "RngDerivationError",
    "derive_stream_seed",
    "is_terminal",
    "parse_phase",
    "resolve_evidence_tier",
]
