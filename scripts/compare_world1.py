#!/usr/bin/env python3
"""Bit-exact L2 comparison for one frozen World 1 treatment.

The Julia recorder is the sequence oracle. This script injects those typed
draws into the newlife world, compares the initial/interval/final snapshots
and the causal assay, and requires every recorded stream entry to be consumed.
Floating observables are projected to proofroot IEEE754 binary64 bit strings
before canonical comparison; a decimal tolerance is deliberately not used.

Usage:
  uv run --package newlife python scripts/compare_world1.py \
    --config <informative.toml> --recorded <recording-dir> --out <report.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.mechanisms.resource_foraging.assay import run_assay
from newlife.mechanisms.resource_foraging.injection import load_recorded_bank
from newlife.mechanisms.resource_foraging.model import load_config
from newlife.mechanisms.resource_foraging.world import ForagingWorld
from proofroot import float_to_bits


INT_FIELDS = (
    "tick",
    "population",
    "births",
    "deaths",
    "movement_attempts",
    "successful_moves",
    "decisions",
    "aligned_actions",
    "true_cue_counts",
    "perceived_cue_counts",
)
FLOAT_FIELDS = (
    "total_resource",
    "total_organism_energy",
    "external_input",
    "overflow_loss",
    "harvested_resource",
    "conversion_loss",
    "maintenance_loss",
    "movement_loss",
    "reproduction_loss",
    "death_loss",
    "balance_error",
)
ASSAY_INT_FIELDS = ("sampled_genomes", "paired_episodes")
ASSAY_FLOAT_FIELDS = (
    "mean_true_harvest",
    "mean_ablated_harvest",
    "harvest_contribution",
    "true_alignment_rate",
    "ablated_alignment_rate",
)


def _comparison_tree(value: Any) -> Any:
    """Encode every float as an IEEE754 bit string for proofroot JCS bytes."""
    if isinstance(value, float):
        return float_to_bits(value)
    if isinstance(value, list):
        return [_comparison_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: _comparison_tree(item) for key, item in value.items()}
    return value


def _project(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: row[field] for field in fields}


def _exact_failures(
    recorded: dict[str, Any],
    observed: dict[str, Any],
    int_fields: tuple[str, ...],
    float_fields: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    for field in int_fields:
        if recorded[field] != observed[field]:
            failures.append(
                f"{field}: recorded {recorded[field]!r} != observed {observed[field]!r}"
            )
    recorded_projected = _project(recorded, float_fields)
    observed_projected = _project(observed, float_fields)
    if canonical_bytes(_comparison_tree(recorded_projected)) != canonical_bytes(
        _comparison_tree(observed_projected)
    ):
        for field in float_fields:
            recorded_bits = float_to_bits(float(recorded[field]))
            observed_bits = float_to_bits(float(observed[field]))
            if recorded_bits != observed_bits:
                failures.append(
                    f"{field}: recorded {recorded[field]!r} ({recorded_bits}) "
                    f"!= observed {observed[field]!r} ({observed_bits})"
                )
    return failures


def compare_row_sets(
    recorded_history: list[dict[str, Any]], observed_history: list[dict[str, Any]]
) -> tuple[bool, list[str]]:
    if len(recorded_history) != len(observed_history):
        return False, [
            f"history row count: recorded {len(recorded_history)} != observed {len(observed_history)}"
        ]
    failures: list[str] = []
    for index, (recorded, observed) in enumerate(
        zip(recorded_history, observed_history)
    ):
        row_failures = _exact_failures(
            recorded, observed, INT_FIELDS, FLOAT_FIELDS
        )
        if row_failures:
            failures.append(
                f"history row {index} (tick {recorded['tick']}): "
                + "; ".join(row_failures)
            )
    return not failures, failures


def _episode_index(scope: str) -> int:
    return int(scope.split("episode-")[1].split("-")[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument(
        "--recorded", required=True, help="recording dir from record_foraging_draws.jl"
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    recorded_dir = Path(args.recorded)
    recorded = json.loads(
        (recorded_dir / "recorded_observables.json").read_text(encoding="utf-8")
    )

    main_bank = load_recorded_bank(args.seed, recorded_dir / "main")
    world = ForagingWorld(config, args.seed, bank=main_bank)
    result = world.run()

    episode_banks = {}
    for scope, episode in recorded["episodes"].items():
        episode_index = _episode_index(scope)
        branch = episode["condition"]
        episode_seed = int(episode["seed_hex"], 16)
        episode_banks[(episode_index, branch)] = load_recorded_bank(
            episode_seed, recorded_dir / scope
        )
    assay = run_assay(world, recorded_banks=episode_banks)
    main_bank.assert_exhausted()
    for bank in episode_banks.values():
        bank.assert_exhausted()

    ok_history, history_failures = compare_row_sets(
        recorded["history"], result.history
    )
    final_failures = _exact_failures(
        recorded["final"], result.final_snapshot, INT_FIELDS, FLOAT_FIELDS
    )

    observed_assay = {
        "sampled_genomes": assay.sampled_genomes,
        "paired_episodes": assay.paired_episodes,
        "mean_true_harvest": assay.mean_true_harvest,
        "mean_ablated_harvest": assay.mean_ablated_harvest,
        "harvest_contribution": assay.harvest_contribution,
        "true_alignment_rate": assay.true_alignment_rate,
        "ablated_alignment_rate": assay.ablated_alignment_rate,
    }
    assay_failures = _exact_failures(
        recorded["assay"], observed_assay, ASSAY_INT_FIELDS, ASSAY_FLOAT_FIELDS
    )

    report = {
        "schema": "newlife.world1.l2-comparison.v1",
        "comparison": "proofroot-ieee754-bitwise",
        "config": str(args.config),
        "seed": args.seed,
        "condition": config.condition,
        "history_rows": len(result.history),
        "history_exact": ok_history,
        "history_failures": history_failures,
        "final_exact": not final_failures,
        "final_failures": final_failures,
        "assay_exact": not assay_failures,
        "assay_failures": assay_failures,
        "observed_assay": observed_assay,
        "recorded_assay": recorded["assay"],
        "main_remaining": main_bank.remaining(),
        "episode_remaining": {
            scope: episode_banks[(_episode_index(scope), episode["condition"])].remaining()
            for scope, episode in recorded["episodes"].items()
        },
        "verdict": (
            "reproduced"
            if ok_history and not final_failures and not assay_failures
            else "mismatch"
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("history_exact", "final_exact", "assay_exact", "verdict")
            },
            indent=2,
        )
    )
    for failure in history_failures[:5] + final_failures[:5] + assay_failures[:5]:
        print(failure)
    return 0 if report["verdict"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
