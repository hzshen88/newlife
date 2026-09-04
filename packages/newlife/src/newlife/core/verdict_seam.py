"""Shared three-valued verdict calculation and artifact rendering.

The verdict domain is fixed to H1, H0, and INVALID. Individual worlds declare
only how that verdict and any hypothesis label are rendered in their artifact.
Exit status is derived mechanically from the verdict.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Any, Mapping

H1 = "H1"
H0 = "H0"
INVALID = "INVALID"
DOMAIN = (H1, H0, INVALID)


def decide(*, h1: bool, h0: bool, invalid: bool = False) -> str:
    """Return a three-valued verdict; exactly one of ``h1`` and ``h0`` must hold.

    ``invalid`` takes precedence because an invalid run must not produce H0 or H1.
    """
    if invalid:
        return INVALID
    if h1 == h0:
        raise ValueError(
            f"verdict predicates are not exclusive: h1={h1} h0={h0}; "
            "a conjunctive criterion must land on exactly one side"
        )
    return H1 if h1 else H0


def exit_code(verdict: str) -> int:
    """Derive the process exit code mechanically from a verdict."""
    if verdict not in DOMAIN:
        raise ValueError(f"{verdict!r} is outside the fixed verdict domain {DOMAIN}")
    return 0 if verdict == H1 else 1


@dataclasses.dataclass(frozen=True, slots=True)
class RenderSpec:
    """Pure-data declaration of how a world renders a verdict artifact.

    ``verdict_key`` stores the three-valued verdict, ``passed_key`` optionally
    stores a boolean, and ``label_key`` plus ``labels`` render a hypothesis name.
    ``sort_keys`` selects the world's serialization convention.
    """

    verdict_key: str | None = "verdict"
    passed_key: str | None = None
    label_key: str | None = None
    labels: Mapping[str, str] | None = None
    sort_keys: bool = False
    ensure_ascii: bool = False


def render(verdict: str, body: Mapping[str, Any], spec: RenderSpec) -> dict[str, Any]:
    """Render a verdict according to a world's declaration."""
    if verdict not in DOMAIN:
        raise ValueError(f"{verdict!r} is outside the verdict domain {DOMAIN}")
    out = dict(body)
    if spec.verdict_key is not None:
        out[spec.verdict_key] = verdict
    if spec.passed_key is not None:
        out[spec.passed_key] = verdict == H1
    if spec.label_key is not None and spec.labels is not None:
        if verdict not in spec.labels:
            raise ValueError(
                f"label mapping does not cover {verdict!r}; it must cover the full domain"
            )
        out[spec.label_key] = spec.labels[verdict]
    return out


def emit(
    verdict: str, body: Mapping[str, Any], spec: RenderSpec,
    out: pathlib.Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Render, serialize, and optionally write an artifact; return object and text."""
    summary = render(verdict, body, spec)
    text = json.dumps(
        summary, indent=2, sort_keys=spec.sort_keys, ensure_ascii=spec.ensure_ascii
    ) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    return summary, text
