#!/usr/bin/env python3
"""L2 comparison runner: the newlife world driven by recorded Julia draws vs
the recorded Julia run's observables (World 1, seed 101, frozen config).

Comparison protocol (docs/worlds/001-resource-foraging.md §4):
- integer observables must match exactly;
- float observables must match within 1e-9 (Julia sums organism energies in
  Dict iteration order, which is not reproducible in Python; the divergence
  is confined to last-bit rounding of aggregates — per-organism scalar
  arithmetic is bit-identical, so the trajectory itself matches).

Usage:
  uv run --package newlife python scripts/compare_world1.py \
    --config <informative.toml> --recorded <recording-dir> --out <report.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from newlife.mechanisms.resource_foraging.assay import run_assay
from newlife.mechanisms.resource_foraging.injection import load_recorded_bank
from newlife.mechanisms.resource_foraging.model import load_config
from newlife.mechanisms.resource_foraging.world import ForagingWorld

FLOAT_TOLERANCE = 1e-9
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


def compare_values(recorded: dict, observed: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for field in INT_FIELDS:
        if recorded[field] != observed[field]:
            failures.append(f"{field}: recorded {recorded[field]} != observed {observed[field]}")
    for field in FLOAT_FIELDS:
        delta = abs(recorded[field] - observed[field])
        if delta > FLOAT_TOLERANCE:
            failures.append(
                f"{field}: |recorded {recorded[field]} - observed {observed[field]}| = {delta} > {FLOAT_TOLERANCE}"
            )
    return not failures, failures


def compare_row_sets(recorded_history: list[dict], observed_history: list[dict]):
    failures = []
    if len(recorded_history) != len(observed_history):
        return False, [
            f"history row count: recorded {len(recorded_history)} != observed {len(observed_history)}"
        ]
    ok_all = True
    for index, (recorded, observed) in enumerate(zip(recorded_history, observed_history)):
        ok, row_failures = compare_values(recorded, observed)
        if not ok:
            ok_all = False
            failures.append(f"history row {index} (tick {recorded['tick']}): " + "; ".join(row_failures))
    return ok_all, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--recorded", required=True, help="recording dir from record_foraging_draws.jl")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    recorded_dir = Path(args.recorded)
    recorded = json.loads((recorded_dir / "recorded_observables.json").read_text(encoding="utf-8"))

    # L2: the main world runs on recorded banks (strict draw replay)
    main_bank = load_recorded_bank(args.seed, recorded_dir / "main")
    world = ForagingWorld(config, args.seed, bank=main_bank)
    result = world.run()

    # the assay consumes the main bank's assay stream (permutation + episode
    # seeds) and runs episode worlds on their own recorded banks
    episode_banks = {}
    for scope, episode in recorded["episodes"].items():
        episode_index = int(scope.split("episode-")[1].split("-")[0])
        branch = episode["condition"]
        seed = int(episode["seed_hex"], 16)
        episode_banks[(episode_index, branch)] = load_recorded_bank(
            seed, recorded_dir / scope
        )
    assay = run_assay(world, recorded_banks=episode_banks)

    ok_history, history_failures = compare_row_sets(recorded["history"], result.history)
    recorded_assay = recorded["assay"]
    observed_assay = {
        "sampled_genomes": assay.sampled_genomes,
        "paired_episodes": assay.paired_episodes,
        "mean_true_harvest": assay.mean_true_harvest,
        "mean_ablated_harvest": assay.mean_ablated_harvest,
        "harvest_contribution": assay.harvest_contribution,
        "true_alignment_rate": assay.true_alignment_rate,
        "ablated_alignment_rate": assay.ablated_alignment_rate,
    }
    # assay comparison: ints exact, floats within tolerance
    assay_failures = []
    if recorded_assay["sampled_genomes"] != assay.sampled_genomes:
        assay_failures.append("sampled_genomes mismatch")
    if recorded_assay["paired_episodes"] != assay.paired_episodes:
        assay_failures.append("paired_episodes mismatch")
    for field in ("mean_true_harvest", "mean_ablated_harvest", "harvest_contribution",
                  "true_alignment_rate", "ablated_alignment_rate"):
        delta = abs(recorded_assay[field] - observed_assay[field])
        if delta > FLOAT_TOLERANCE:
            assay_failures.append(f"{field}: |delta| = {delta} > {FLOAT_TOLERANCE}")
    ok_assay = not assay_failures

    report = {
        "config": str(args.config),
        "seed": args.seed,
        "condition": config.condition,
        "history_rows": len(result.history),
        "history_exact": ok_history,
        "history_failures": history_failures,
        "assay_exact": ok_assay,
        "assay_failures": assay_failures,
        "observed_assay": observed_assay,
        "recorded_assay": recorded_assay,
        "verdict": "reproduced" if ok_history and ok_assay else "mismatch",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("history_exact", "assay_exact", "verdict")}, indent=2))
    if history_failures:
        print("\n".join(history_failures[:5]))
    return 0 if report["verdict"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
