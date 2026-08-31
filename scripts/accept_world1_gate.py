#!/usr/bin/env python3
"""Accept the World 1 v0.2 gate from completed L2 reports and measurements."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from newlife.mechanisms.resource_foraging.mechanisms import build_mechanism_specs
from newlife.mechanisms.resource_foraging.model import load_config


EXPECTED_MECHANISMS = (
    "resource-environment",
    "forager-movement",
    "forager-harvest-metabolism",
    "forager-reproduction",
    "forager-aging",
    "world-observer",
)
REFERENCE_FILES = (
    "Model.jl",
    "Dynamics.jl",
    "EvidenceAdapter.jl",
    "Assays.jl",
)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--l2-root", required=True, type=Path)
    parser.add_argument("--parworlds", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    config = load_config(
        args.parworlds
        / "experiments"
        / "001-resource-foraging"
        / "configs"
        / "informative.toml"
    )
    mechanism_ids = [spec.identity for spec in build_mechanism_specs(config)]
    examples_python = sorted(
        str(path.relative_to(repo_root))
        for path in (repo_root / "examples").rglob("*.py")
    )
    import_lint = subprocess.run(
        ["python", str(repo_root / "scripts" / "check_imports.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    report_paths = {
        condition: args.l2_root / "reports" / f"{condition}.json"
        for condition in ("informative", "cue_neutral")
    }
    l2_reports = {}
    for condition, path in report_paths.items():
        if path.is_file():
            l2_reports[condition] = json.loads(path.read_text(encoding="utf-8"))
        else:
            l2_reports[condition] = {"verdict": "missing", "path": str(path)}

    reference_root = args.parworlds / "src" / "worlds" / "ResourceForaging"
    reference_counts = {
        name: _line_count(reference_root / name)
        for name in REFERENCE_FILES
        if (reference_root / name).is_file()
    }
    mechanism_root = repo_root / "packages" / "newlife" / "src" / "newlife" / "mechanisms" / "resource_foraging"
    newlife_counts = {
        path.name: _line_count(path)
        for path in sorted(mechanism_root.glob("*.py"))
    }

    checks = {
        "l2_informative_reproduced": l2_reports["informative"].get("verdict") == "reproduced",
        "l2_cue_neutral_reproduced": l2_reports["cue_neutral"].get("verdict") == "reproduced",
        "l2_uses_ieee754_canonical": all(
            report.get("comparison") == "proofroot-ieee754-bitwise"
            for report in l2_reports.values()
        ),
        "l2_all_draws_consumed": all(
            report.get("main_remaining") == {name: 0 for name in report.get("main_remaining", {})}
            and all(count == 0 for counts in report.get("episode_remaining", {}).values() for count in counts.values())
            for report in l2_reports.values()
        ),
        "mechanism_registry_complete": tuple(mechanism_ids) == EXPECTED_MECHANISMS,
        "examples_zero_runtime_code": not examples_python,
        "import_lint_passed": import_lint.returncode == 0,
        "frozen_scale": (
            config.width,
            config.height,
            config.ticks,
            config.initial_population,
        ) == (32, 32, 5000, 128),
    }
    payload = {
        "schema": "newlife.world1.v0.2-gate.v1",
        "gate": "v0.2-world1-resource-foraging",
        "checks": checks,
        "passed": all(checks.values()),
        "mechanism_registry": mechanism_ids,
        "examples_python_files": examples_python,
        "import_lint_stdout": import_lint.stdout.strip(),
        "l2_reports": {
            condition: str(path) for condition, path in report_paths.items()
        },
        "pain_point_measurements": {
            "P1_mechanisms_registered": len(mechanism_ids),
            "P2_runtime_import_lint": import_lint.returncode == 0,
            "P2_l2_reports_bitwise": checks["l2_uses_ieee754_canonical"],
            "P3_newlife_mechanism_files": len(newlife_counts),
            "P3_newlife_mechanism_lines": sum(newlife_counts.values()),
            "P3_parworlds_reference_files": len(reference_counts),
            "P3_parworlds_reference_lines": sum(reference_counts.values()),
        },
        "line_counts": {
            "newlife_mechanisms": newlife_counts,
            "parworlds_reference": reference_counts,
        },
        "l2_results": l2_reports,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": payload["passed"], "out": str(args.out)}, indent=2))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
