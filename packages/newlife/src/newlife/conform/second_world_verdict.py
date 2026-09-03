"""Second-world verdict runner (Task 3, plan §7/§8; frozen prereg §
Primary analysis / Decision rules).

Two-tier conjunction, computed mechanically, never hand-entered: the
second-world verdict is ``ms_minimal_coalescent_reproducible`` only if, for
every one of the 30 frozen-grid replicates (§ Fixed units and fixed
sample), (1) segsites and (2) the genotype matrix match at **both** tiers
(tier a: the standalone port vs. a freshly-built, freshly-run real `ms`
binary; tier b: the mechanism registry vs. tier a's own output), tier a
additionally satisfies (3) exact draw consumption (zero leftover, no early
exhaustion), and both (4) the R2 mapping-correctness check and (5) the
frozen grid's `segsites==0` coverage hold. A pass at tier a alone, with
tier b failing or not attempted, is reported as ``verdict_withheld`` — not
partial H1 (this is the prereg's own explicit ruling, not a runner
convenience).

Every replicate and tier is attempted even after an earlier failure (the
prereg's "Stopping rule and multiplicity": no stopping for significance,
unattempted replicates/tiers are failures, not exclusions).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from newlife.mechanisms.second_world.ms_binary import build_ms, parse_ms_stdout, run_ms
from newlife.mechanisms.second_world.ms_coalescent import (
    DrawExhausted,
    RecordedDrawStream,
    UnsupportedGasdevBranch,
    run_replicate,
)
from newlife.mechanisms.second_world.rng_mapping import (
    derived_seed_to_ms_triple,
    pack_ms_triple,
)
from newlife.mechanisms.second_world.world import CoalescentWorld
from proofroot import EVIDENCECORE_RNG_V1, derive_stream_seed

VENDOR_ROOT = Path(__file__).resolve().parents[5] / "vendor" / "ms"

NSAM = 4
THETA = 2.0
HOWMANY = 10
SEED_TRIPLES = {
    "seedA": (3579, 27011, 59243),
    "seedB": (12345, 6789, 999),
    "seedC": (101, 202, 303),
}

from newlife.core.verdict_seam import (  # noqa: E402
    H0, H1, RenderSpec, decide, emit, exit_code,
)

VERDICT_PASS = "ms_minimal_coalescent_reproducible"
VERDICT_WITHHELD = "verdict_withheld"

_U48_MASK = (1 << 48) - 1


def _genotype_hash(rows: list[str]) -> str:
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _check_tier_a(
    index: int, expected: tuple[int, list[str]], draws: RecordedDrawStream
) -> dict[str, Any]:
    expected_segsites, expected_rows = expected
    try:
        result = run_replicate(NSAM, THETA, draws)
    except (DrawExhausted, UnsupportedGasdevBranch) as error:
        return {"index": index, "passed": False, "error": str(error)}
    segsites_ok = result.segsites == expected_segsites
    rows_ok = result.genotype_rows == expected_rows
    return {
        "index": index,
        "segsites": result.segsites,
        "genotype_hash": _genotype_hash(result.genotype_rows),
        "segsites_matches_ms": segsites_ok,
        "genotype_matches_ms": rows_ok,
        "passed": segsites_ok and rows_ok,
    }


def _check_tier_b(
    index: int, tier_a: dict[str, Any], draws: RecordedDrawStream
) -> dict[str, Any]:
    try:
        outcome = CoalescentWorld(NSAM, THETA, draws, replicate_index=index).run()
    except (DrawExhausted, UnsupportedGasdevBranch) as error:
        return {"index": index, "passed": False, "error": str(error)}
    segsites_ok = tier_a.get("passed") and outcome.segsites == tier_a.get("segsites")
    genotype_ok = tier_a.get("passed") and _genotype_hash(
        outcome.genotype_rows
    ) == tier_a.get("genotype_hash")
    return {
        "index": index,
        "segsites": outcome.segsites,
        "genotype_hash": _genotype_hash(outcome.genotype_rows),
        "matches_tier_a": bool(segsites_ok and genotype_ok),
        "passed": bool(segsites_ok and genotype_ok),
    }


def _run_seed_grid(
    ms_binary: Path, seed_name: str, seeds: tuple[int, int, int], workdir: Path
) -> dict[str, Any]:
    draw_log = workdir / f"{seed_name}.draws"
    stdout = run_ms(ms_binary, NSAM, HOWMANY, THETA, seeds, draw_log)
    real_replicates = parse_ms_stdout(stdout, NSAM, HOWMANY)

    tier_a_draws = RecordedDrawStream.from_log_file(draw_log)
    tier_b_draws = RecordedDrawStream.from_log_file(draw_log)

    tier_a_records = []
    tier_b_records = []
    for index, expected in enumerate(real_replicates):
        tier_a = _check_tier_a(index, expected, tier_a_draws)
        tier_a_records.append(tier_a)
        tier_b_records.append(_check_tier_b(index, tier_a, tier_b_draws))

    return {
        "seed": seed_name,
        "seeds": list(seeds),
        "tier_a": tier_a_records,
        "tier_b": tier_b_records,
        "tier_a_draws_logged": tier_a_draws.consumed + tier_a_draws.leftover,
        "tier_a_draws_consumed": tier_a_draws.consumed,
        "tier_a_leftover": tier_a_draws.leftover,
        "tier_b_draws_consumed": tier_b_draws.consumed,
        "tier_b_leftover": tier_b_draws.leftover,
        "segsites_zero_count": sum(1 for r in tier_a_records if r.get("segsites") == 0),
    }


def _check_r2_mapping() -> dict[str, Any]:
    """Primary analysis (4): the R2 mapping-correctness check, isolated
    from the ms-comparison grid — same assertions as
    tests/second_world/test_rng_mapping.py, collected as booleans instead
    of raised."""
    inputs = [
        (EVIDENCECORE_RNG_V1, 1, "second-world-coalescent"),
        (EVIDENCECORE_RNG_V1, 2, "second-world-coalescent"),
        (EVIDENCECORE_RNG_V1, 1, "second-world-mutation"),
    ]
    round_trip_ok = True
    range_ok = True
    for version, root_seed, name in inputs:
        seed = derive_stream_seed(version, root_seed, name)
        triple = derived_seed_to_ms_triple(seed)
        range_ok = range_ok and all(0 <= word <= 0xFFFF for word in triple)
        round_trip_ok = round_trip_ok and pack_ms_triple(triple) == (seed & _U48_MASK)

    base_seed = derive_stream_seed(*inputs[0])
    low_48 = base_seed & _U48_MASK
    seed_a = low_48 | (0x0001 << 48)
    seed_b = low_48 | (0xFFFE << 48)
    lossy_ok = derived_seed_to_ms_triple(seed_a) == derived_seed_to_ms_triple(seed_b)

    return {
        "range_valid": range_ok,
        "round_trip_matches": round_trip_ok,
        "truncation_observably_lossy": lossy_ok,
        "passed": range_ok and round_trip_ok and lossy_ok,
    }


def compute_verdict(
    seed_results: dict[str, dict[str, Any]], r2_check: dict[str, Any]
) -> str:
    tier_a_all_pass = all(
        record["passed"]
        for result in seed_results.values()
        for record in result["tier_a"]
    )
    tier_a_no_leftover = all(
        result["tier_a_leftover"] == 0 for result in seed_results.values()
    )
    tier_b_all_pass = all(
        record["passed"]
        for result in seed_results.values()
        for record in result["tier_b"]
    )
    segsites_zero_covered = (
        sum(result["segsites_zero_count"] for result in seed_results.values()) > 0
    )

    if (
        tier_a_all_pass
        and tier_a_no_leftover
        and tier_b_all_pass
        and r2_check["passed"]
        and segsites_zero_covered
    ):
        return VERDICT_PASS
    return VERDICT_WITHHELD


def execute(output_dir: Path, workdir: Path) -> dict[str, Any]:
    ms_binary = build_ms(VENDOR_ROOT, workdir / "ms")

    seed_results = {
        seed_name: _run_seed_grid(ms_binary, seed_name, seeds, workdir)
        for seed_name, seeds in SEED_TRIPLES.items()
    }
    r2_check = _check_r2_mapping()
    verdict = compute_verdict(seed_results, r2_check)

    total_segsites = sum(
        record["segsites"]
        for result in seed_results.values()
        for record in result["tier_a"]
        if "segsites" in record
    )
    watterson_expected = THETA * sum(1.0 / i for i in range(1, NSAM))

    # 第一代表示：`verdict` 键装的是**假设名**（标签），三值判定落在 `passed`。
    # Definition 判三值，声明式映射给标签——runner 里不留 if/else（预注册 `a517d29`）。
    decision = decide(h1=verdict == VERDICT_PASS, h0=verdict != VERDICT_PASS)
    summary = {
        "schema": "newlife.second-world.gate.v1",
        "verdict": None,
        "passed": None,
        "replicate_count": HOWMANY * len(SEED_TRIPLES),
        "structural_checks": {
            "r2_mapping_correctness": r2_check,
            "segsites_zero_coverage": {
                "counts": {
                    name: r["segsites_zero_count"] for name, r in seed_results.items()
                },
                "total": sum(r["segsites_zero_count"] for r in seed_results.values()),
                "passed": sum(r["segsites_zero_count"] for r in seed_results.values())
                > 0,
            },
        },
        "tiers": {
            "tier_a": {
                name: {
                    "all_passed": all(rec["passed"] for rec in r["tier_a"]),
                    "draws_logged": r["tier_a_draws_logged"],
                    "draws_consumed": r["tier_a_draws_consumed"],
                    "leftover": r["tier_a_leftover"],
                }
                for name, r in seed_results.items()
            },
            "tier_b": {
                name: {
                    "all_passed": all(rec["passed"] for rec in r["tier_b"]),
                    "draws_consumed": r["tier_b_draws_consumed"],
                    "leftover": r["tier_b_leftover"],
                }
                for name, r in seed_results.items()
            },
        },
        "informational": {
            "watterson_expected_mean_segsites": watterson_expected,
            "observed_mean_segsites": total_segsites / (HOWMANY * len(SEED_TRIPLES)),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    replicates_dir = output_dir / "replicates"
    replicates_dir.mkdir(exist_ok=True)
    for seed_name, result in seed_results.items():
        for tier_a, tier_b in zip(result["tier_a"], result["tier_b"]):
            record = {
                "seed": seed_name,
                "seeds": result["seeds"],
                "nsam": NSAM,
                "theta": THETA,
                "replicate_index": tier_a["index"],
                "tier_a": tier_a,
                "tier_b": tier_b,
            }
            # plan §6 artifact layout: replicates/{seedA,seedB,seedC}-{01..10}.json
            path = replicates_dir / f"{seed_name}-{tier_a['index'] + 1:02d}.json"
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

    summary, _text = emit(
        decision, summary,
        RenderSpec(
            verdict_key=None, passed_key="passed", label_key="verdict",
            labels={H1: VERDICT_PASS, H0: VERDICT_WITHHELD,
                    "INVALID": VERDICT_WITHHELD},
            sort_keys=True, ensure_ascii=True,
        ),
        output_dir / "summary.json",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/second-world"),
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=None,
        help="scratch dir for the ms build + draw logs (default: a temp dir)",
    )
    args = parser.parse_args()

    if args.workdir is not None:
        args.workdir.mkdir(parents=True, exist_ok=True)
        summary = execute(args.output, args.workdir)
    else:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            summary = execute(args.output, Path(tmp))

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
