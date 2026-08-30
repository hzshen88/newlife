"""D2 RunPhase + terminal-state decision, D5 evidence tier vocabulary.

Port of EvidenceCore.jl's D2/D5. Per §5.10 discipline 2, the legacy UPPER-CASE
phase spellings ("COMPLETED"/"FAILED"/…) are deliberately NOT ported — they
exist to read pre-unification ParaLife run artifacts, whose reason to exist is
not portable. New artifacts serialize TitleCase.
"""

from __future__ import annotations

import enum


class RunPhase(str, enum.Enum):
    """The unified 8-value TitleCase run lifecycle phases (D2).

    Only the enum values and terminality are shared semantics; the transition
    map stays with each host's run lifecycle (Parcells' 6-step and Parworlds'
    8-step lifecycles were deliberately not unified in the first generation).
    """

    PLANNED = "Planned"
    VALIDATED = "Validated"
    INITIALIZING = "Initializing"
    RUNNING = "Running"
    ASSAYING = "Assaying"
    FINALIZING = "Finalizing"
    COMPLETED = "Completed"
    FAILED = "Failed"


def is_terminal(phase: RunPhase) -> bool:
    """A phase is an irreversible terminal state iff it is Completed or Failed."""
    return phase is RunPhase.COMPLETED or phase is RunPhase.FAILED


def parse_phase(name: str) -> RunPhase:
    """Resolve a phase from its serialized (TitleCase) string form.

    Raises on anything else — including the legacy UPPER-CASE spellings, which
    are a ParaLife-local compatibility layer and intentionally not accepted
    here.
    """
    try:
        return RunPhase(name)
    except ValueError:
        raise ValueError(f"unknown run phase {name!r}") from None


# ── D5: evidence tier vocabulary (cross-program governance, ADR-0016) ────────
# exploration and unknown may never be cited as evidence; confirmatory must be
# declared explicitly. The safety direction: a missing field degrades to
# unknown — never to confirmatory — so "forgot to declare" fails closed.

EVIDENCE_TIER_EXPLORATION = "exploration"
EVIDENCE_TIER_CONFIRMATORY = "confirmatory"
EVIDENCE_TIER_UNKNOWN = "unknown"
EVIDENCE_TIERS = frozenset(
    {EVIDENCE_TIER_EXPLORATION, EVIDENCE_TIER_CONFIRMATORY, EVIDENCE_TIER_UNKNOWN}
)


def resolve_evidence_tier(declared: str | None) -> str:
    """Resolve the evidence tier of a run artifact.

    ``None``/missing degrades to ``unknown`` (fail closed). A declared tier
    must be a member of the vocabulary — a typo must raise, not silently pass
    as either citable or uncitable.
    """
    if declared is None:
        return EVIDENCE_TIER_UNKNOWN
    if declared not in EVIDENCE_TIERS:
        raise ValueError(f"unknown evidence tier: {declared!r}")
    return declared
