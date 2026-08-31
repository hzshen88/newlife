#!/usr/bin/env python3
"""Accept the v0.3 compare reverse-attribution gate.

Runs all 7 calibration units frozen in
`exloop/docs/science-superpowers/preregistrations/2026-08-31-newlife-compare-attribution-declarability-v2.md`
(4 World-1-derived via `mechanisms.resource_foraging.calibration`, 3
synthetic defined inline here — a synthetic unit needs no `ForagingWorld`
and its oracle is definitional, not empirically surprising, but the
preregistration requires it be asserted by execution, not by prose), plus
the two structural checks, and writes a compact verdict bundle. Never
imports `core.compare`'s oracle answers into `core/compare.py` itself —
that module is verified never to reference them (source-scan check below).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from newlife.core.compare import (
    attribute_causality,
    diff_declarations,
    locate_divergence,
)
from newlife.mechanisms.resource_foraging.calibration import (
    CalibrationUnit,
    build_unit1,
    build_unit2,
    build_unit3,
    build_unit4,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPARE_SRC = (
    REPO_ROOT / "packages" / "newlife" / "src" / "newlife" / "core" / "compare.py"
)


# --------------------------------------------------------------- synthetic units


@dataclasses.dataclass(frozen=True)
class TwoField:
    alpha: str
    beta: str


@dataclasses.dataclass(frozen=True)
class ThreeField:
    alpha: str
    beta: str
    gamma: str


def _unit_from(
    name: str,
    config_a: Any,
    config_b: Any,
    runner: Callable[[Any], Sequence[Mapping[str, Any]]],
    *,
    expected_differing_fields: tuple[str, ...],
    expected_locus_tick: int | None,
    expected_per_field: Mapping[str, str],
    expected_aggregate: str,
) -> CalibrationUnit:
    history_a = runner(config_a)
    history_b = runner(config_b)
    return CalibrationUnit(
        name=name,
        registry_a=(),
        registry_b=(),
        config_a=config_a,
        config_b=config_b,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=expected_differing_fields,
        expected_locus_tick=expected_locus_tick,
        expected_per_field=expected_per_field,
        expected_aggregate=expected_aggregate,
    )


def build_unit5_synthetic() -> CalibrationUnit:
    """n=3, one causal two incidental."""
    config_a = ThreeField(alpha="a1", beta="b1", gamma="g1")
    config_b = ThreeField(alpha="a2", beta="b2", gamma="g2")

    def runner(cfg: ThreeField) -> Sequence[Mapping[str, Any]]:
        return [{"tick": 0}, {"tick": 1, "x": f"driven-by-{cfg.alpha}"}]

    return _unit_from(
        "unit5-synthetic-n3",
        config_a,
        config_b,
        runner,
        expected_differing_fields=("alpha", "beta", "gamma"),
        expected_locus_tick=1,
        expected_per_field={
            "alpha": "causal",
            "beta": "incidental",
            "gamma": "incidental",
        },
        expected_aggregate="normal",
    )


def build_unit6a_synthetic() -> CalibrationUnit:
    """Divergence driven by a value outside any declared field."""
    config_a = TwoField(alpha="a1", beta="b1")
    config_b = TwoField(alpha="a2", beta="b2")
    hidden = {"flag": "B"}  # every rerun happens with the hidden flag at "B"

    def runner(_cfg: TwoField) -> Sequence[Mapping[str, Any]]:
        return [{"tick": 0}, {"tick": 1, "x": hidden["flag"]}]

    hidden["flag"] = "A"
    history_a = runner(config_a)
    hidden["flag"] = "B"
    history_b = runner(config_b)
    return CalibrationUnit(
        name="unit6a-synthetic-unattributed-divergence",
        registry_a=(),
        registry_b=(),
        config_a=config_a,
        config_b=config_b,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=("alpha", "beta"),
        expected_locus_tick=1,
        expected_per_field={"alpha": "incidental", "beta": "incidental"},
        expected_aggregate="UNATTRIBUTED_DIVERGENCE",
    )


def build_unit6b_synthetic() -> CalibrationUnit:
    """Two declared fields each independently sufficient."""
    config_a = TwoField(alpha="X", beta="X")
    config_b = TwoField(alpha="Y", beta="Y")

    def runner(cfg: TwoField) -> Sequence[Mapping[str, Any]]:
        diverged = not (cfg.alpha == "X" or cfg.beta == "X")
        return [{"tick": 0}, {"tick": 1, "diverged": diverged}]

    return _unit_from(
        "unit6b-synthetic-multi-causal",
        config_a,
        config_b,
        runner,
        expected_differing_fields=("alpha", "beta"),
        expected_locus_tick=1,
        expected_per_field={"alpha": "causal", "beta": "causal"},
        expected_aggregate="MULTI_CAUSAL_OR_UNRESOLVED",
    )


def build_unit6c_synthetic() -> CalibrationUnit:
    """Precedence regression test: one field unresolved, one incidental —
    both the 'no causal' and 'any unresolved' raw conditions are true."""
    config_a = TwoField(alpha="a1", beta="b1")
    config_b = TwoField(alpha="a2", beta="b2")

    def runner(cfg: TwoField) -> Sequence[Mapping[str, Any]]:
        if cfg.alpha == "a1":
            if cfg.beta == "b1":
                return [{"tick": 0}, {"tick": 1, "x": "A"}]
            return [{"tick": 0}, {"tick": 1, "x": "coupled"}]
        return [{"tick": 0}, {"tick": 1, "x": "B"}]

    return _unit_from(
        "unit6c-synthetic-precedence",
        config_a,
        config_b,
        runner,
        expected_differing_fields=("alpha", "beta"),
        expected_locus_tick=1,
        expected_per_field={"alpha": "unresolved", "beta": "incidental"},
        expected_aggregate="MULTI_CAUSAL_OR_UNRESOLVED",
    )


def build_unit7_synthetic() -> tuple[
    Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]]
]:
    """Length-mismatch locus — not a CalibrationUnit (no declaration diff
    is exercised, only locate_divergence), returned as a raw sequence pair."""
    sequence_a = [{"tick": 0}, {"tick": 1}, {"tick": 2}]
    sequence_b = [{"tick": 0}, {"tick": 1}]
    return sequence_a, sequence_b


# --------------------------------------------------------------- verdict runner


def _assert_unit(unit: CalibrationUnit) -> dict[str, Any]:
    diff = diff_declarations(
        unit.registry_a, unit.registry_b, unit.config_a, unit.config_b
    )
    locus = locate_divergence(unit.history_a, unit.history_b)
    result = attribute_causality(diff, unit.history_a, unit.history_b, unit.runner)

    checks = {
        "registry_equal": diff.registry_equal is unit.expected_registry_equal,
        "differing_fields": diff.differing_fields == unit.expected_differing_fields,
        "locus": (
            (locus is None)
            if unit.expected_locus_tick is None
            else (
                locus is not None
                and locus.kind == "value"
                and locus.tick == unit.expected_locus_tick
            )
        ),
        "per_field": dict(result.per_field) == dict(unit.expected_per_field),
        "aggregate": result.aggregate == unit.expected_aggregate,
    }
    return {
        "name": unit.name,
        "registry_equal": diff.registry_equal,
        "differing_fields": list(diff.differing_fields),
        "locus": None
        if locus is None
        else {"kind": locus.kind, "index": locus.index, "tick": locus.tick},
        "per_field": dict(result.per_field),
        "aggregate": result.aggregate,
        "checks": checks,
        "passed": all(checks.values()),
    }


def _source_scan_passed() -> bool:
    text = COMPARE_SRC.read_text(encoding="utf-8")
    return "condition" not in text and '"name"' not in text and "'name'" not in text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--informative",
        type=Path,
        default=Path("examples/first-world/informative.toml"),
    )
    parser.add_argument(
        "--cue-neutral",
        type=Path,
        default=Path("examples/first-world/cue_neutral.toml"),
    )
    parser.add_argument("--out", type=Path, default=Path("results/v0.3/summary.json"))
    args = parser.parse_args()

    real_units = {
        "unit1": (
            "informative vs cue-neutral, ticks=50, seed=101",
            _assert_unit(build_unit1(args.informative, args.cue_neutral)),
        ),
        "unit2_seed101": (
            "assay true/ablated, seed=101",
            _assert_unit(build_unit2(args.informative, 101)),
        ),
        "unit2_seed202": (
            "assay true/ablated, seed=202",
            _assert_unit(build_unit2(args.informative, 202)),
        ),
        "unit3": (
            "informative + name-only change, seed=101",
            _assert_unit(build_unit3(args.informative)),
        ),
        "unit4": (
            "informative run twice independently, seed=101",
            _assert_unit(build_unit4(args.informative)),
        ),
        "unit5": (
            "synthetic n=3, defined in scripts/accept_v03_compare_gate.py:build_unit5_synthetic",
            _assert_unit(build_unit5_synthetic()),
        ),
        "unit6a": (
            "synthetic unattributed divergence, build_unit6a_synthetic",
            _assert_unit(build_unit6a_synthetic()),
        ),
        "unit6b": (
            "synthetic multi-causal, build_unit6b_synthetic",
            _assert_unit(build_unit6b_synthetic()),
        ),
        "unit6c": (
            "synthetic precedence regression, build_unit6c_synthetic",
            _assert_unit(build_unit6c_synthetic()),
        ),
    }

    sequence_a, sequence_b = build_unit7_synthetic()
    unit7_locus = locate_divergence(sequence_a, sequence_b)
    unit7_passed = unit7_locus is not None and unit7_locus.kind == "length_mismatch"
    real_units["unit7"] = (
        "synthetic length mismatch, build_unit7_synthetic",
        {
            "name": "unit7-synthetic-length-mismatch",
            "locus": None
            if unit7_locus is None
            else {
                "kind": unit7_locus.kind,
                "index": unit7_locus.index,
                "tick": unit7_locus.tick,
            },
            "checks": {"locus_kind_is_length_mismatch": unit7_passed},
            "passed": unit7_passed,
        },
    )

    registry_identity_holds = all(
        real_units[name][1]["checks"]["registry_equal"]
        for name in ("unit1", "unit2_seed101", "unit2_seed202", "unit3", "unit4")
    )
    source_scan_passed = _source_scan_passed()

    all_unit_records = [
        {"regeneration_invocation": invocation, **record}
        for invocation, record in real_units.values()
    ]
    all_passed = all(record["passed"] for record in all_unit_records)

    payload = {
        "schema": "newlife.world1.v0.3-compare-gate.v1",
        "gate": "v0.3-compare-reverse-attribution",
        "units": all_unit_records,
        "structural_checks": {
            "registry_identity_holds": registry_identity_holds,
            "source_scan_passed": source_scan_passed,
        },
        "passed": all_passed and registry_identity_holds and source_scan_passed,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": payload["passed"], "out": str(args.out)}, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
