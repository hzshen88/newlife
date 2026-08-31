#!/usr/bin/env python3
"""Run the frozen World 1 L2 gate for both treatments.

The output directory is intentionally a fresh run directory because the Julia
recorder appends JSONL entries. Use ``--reuse-recordings`` only when the two
recording directories are already complete and should be compared again.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


CONDITIONS = ("informative", "cue_neutral")


def _run(command: list[str], *, cwd: Path) -> int:
    return subprocess.run(command, cwd=cwd, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parworlds", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument(
        "--reuse-recordings",
        action="store_true",
        help="skip Julia recording and reuse out/recordings/<condition>",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    recorder = repo_root / "tools" / "julia" / "record_foraging_draws.jl"
    compare = repo_root / "scripts" / "compare_world1.py"
    config_root = args.parworlds / "experiments" / "001-resource-foraging" / "configs"
    if not args.parworlds.is_dir():
        parser.error(f"Parworlds root does not exist: {args.parworlds}")
    if not recorder.is_file() or not compare.is_file():
        parser.error("newlife recorder/comparator is missing")

    if args.out.exists() and any(args.out.iterdir()) and not args.reuse_recordings:
        parser.error(
            f"output directory is non-empty: {args.out}; use a fresh path or --reuse-recordings"
        )
    args.out.mkdir(parents=True, exist_ok=True)
    recordings = args.out / "recordings"
    reports = args.out / "reports"
    recordings.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)

    statuses: dict[str, int] = {}
    for condition in CONDITIONS:
        config = config_root / f"{condition}.toml"
        recording = recordings / condition
        report = reports / f"{condition}.json"
        if not config.is_file():
            parser.error(f"missing frozen config: {config}")
        if not args.reuse_recordings:
            recording.mkdir(parents=True, exist_ok=False)
            statuses[f"record:{condition}"] = _run(
                [
                    "julia",
                    f"--project={args.parworlds}",
                    str(recorder),
                    "--config",
                    str(config),
                    "--seed",
                    str(args.seed),
                    "--out",
                    str(recording),
                ],
                cwd=repo_root,
            )
            if statuses[f"record:{condition}"] != 0:
                break
        statuses[f"compare:{condition}"] = _run(
            [
                sys.executable,
                str(compare),
                "--config",
                str(config),
                "--seed",
                str(args.seed),
                "--recorded",
                str(recording),
                "--out",
                str(report),
            ],
            cwd=repo_root,
        )

    report_payload = {
        "schema": "newlife.world1.l2-run.v1",
        "seed": args.seed,
        "conditions": list(CONDITIONS),
        "recordings": {
            condition: str(recordings / condition) for condition in CONDITIONS
        },
        "reports": {
            condition: str(reports / f"{condition}.json") for condition in CONDITIONS
        },
        "statuses": statuses,
        "verdict": "reproduced"
        if all(statuses.get(f"compare:{condition}") == 0 for condition in CONDITIONS)
        else "mismatch",
    }
    summary = args.out / "l2-run.json"
    summary.write_text(
        json.dumps(report_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": report_payload["verdict"], "summary": str(summary)}, indent=2))
    return 0 if report_payload["verdict"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
