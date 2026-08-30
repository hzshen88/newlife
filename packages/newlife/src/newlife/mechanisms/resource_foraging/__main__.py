"""Single-world CLI (the run_foraging_world.jl analogue): config + seed →
world run + causal assay, artifacts as JSON. The application layer stays
data-only — this entry point lives in the library, not in the example."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from newlife.mechanisms.resource_foraging.world import run_world_with_assay


def main() -> int:
    parser = argparse.ArgumentParser(prog="resource-foraging")
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run_world_with_assay(args.config, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"world: {args.config} | seed: {args.seed} | tick: {report['tick']} "
        f"| population: {report['population']} | extinct: {report['extinct']}"
    )
    if "assay" in report:
        print("assay harvest_contribution: ", report["assay"]["harvest_contribution"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
