"""Where is this question? Read the folder and say the stage, the blockers and the next step.

## Why this exists

Resuming after an interruption used to depend on the assistant reading a table of "if this
file exists then that stage" out of a skill. The table was wrong in the one case that
matters most: it took `results/summary.json` as "done", but the scaffolded runner writes its
final verdict to `reproduction.json`, so a run that died between the two looked finished.
Stage detection belongs in code that is tested, not in prose that is inferred from.

## What it reads, in order

1. `prereg.md` — not there: this is not a question folder.
2. `goal.md` against the goal gate — red: stage **goal**.
3. `prereg.md`'s stamp line — `_pending_` means not frozen:
   - no `pilot/ledger.jsonl`: stage **world & pilot**;
   - pilot coverage red: stage **criteria**;
   - green: stage **ready to freeze** (a decision for the person).
4. Frozen:
   - no `results/summary.json`: stage **run**;
   - `summary.json` without `reproduction.json` and without an S0 unit inside it: stage
     **run interrupted** — the self-reproduction never completed, there is no verdict.
     (The scaffolded runner writes the verdict to `reproduction.json`; a runner of the
     person's own may record S0 as a unit in `summary.json` instead, and then the
     verdict is read off the units: S0 false → INVALID, any other false → H0, else H1.)
   - both, results not committed: stage **verdict computed, not committed**;
   - committed: stage **closeout** — `goal.md` §5 and the exploration map.

It runs no scan (the freeze and the run do that) and changes nothing.

    newlife status <question-folder>
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import subprocess
from pathlib import Path

from newlife.gates import goal_ready, pilot_coverage

STAMP_PREFIX = "**Frozen at commit:**"
CLOSEOUT_PLACEHOLDER = (
    "(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)"
)


@dataclasses.dataclass
class Report:
    """One question's position in the loop, in the words the assistant relays."""

    folder: Path
    stage: str
    frozen_at: str | None = None
    done: list[str] = dataclasses.field(default_factory=list)
    blockers: list[str] = dataclasses.field(default_factory=list)
    next: str = ""
    decisions: list[str] = dataclasses.field(default_factory=list)
    verdict: str | None = None
    origin_files: int = 0


def _frozen_at(prereg_text: str) -> str | None:
    """The stamped freeze commit, or None while the registration is still `_pending_`."""
    # silent-degradation: ok -- a registration without a stamp line is reported by the
    # caller as unfrozen; the line's absence is the normal state before the freeze.
    for line in prereg_text.splitlines():
        if line.startswith(STAMP_PREFIX):
            sha = line[len(STAMP_PREFIX) :].strip().strip("`_")
            return sha if sha and sha != "pending" else None
    return None


def _results_committed(folder: Path) -> bool:
    """True when nothing under results/ is untracked or modified in git."""
    proc = subprocess.run(
        ["git", "-C", str(folder), "status", "--porcelain", "--", "results"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git could not read {folder}: {proc.stderr.strip()}")
    return proc.stdout.strip() == ""


def _verdict(summary: Path, reproduction: Path) -> str | None:
    """The verdict on record, or None when the run never got to S0.

    The scaffolded runner writes it to `reproduction.json`. A runner the person wrote
    themselves may fold S0 into the units of `summary.json` (found 2026-09-06 on a real
    question, which this function used to report as interrupted). When every unit carries a
    boolean `passed`, the verdict is the conjunction the registration defines: S0 false →
    INVALID, any other unit false → H0. When a unit is shaped differently the run still
    counts as finished, but the verdict is left to the runner's own record, not guessed.
    """
    if reproduction.is_file():
        data = json.loads(reproduction.read_text(encoding="utf-8"))
        return str(data.get("verdict", "?"))
    data = json.loads(summary.read_text(encoding="utf-8"))
    if isinstance(data.get("verdict"), str):
        return data["verdict"]
    units = data.get("units")
    if not isinstance(units, dict):
        return None
    s0 = [u for name, u in units.items() if name.upper().startswith("S0")]
    if not s0:
        return None
    if not all(isinstance(u, dict) and isinstance(u.get("passed"), bool) for u in units.values()):
        # A unit shaped differently (a real runner recorded S0 as per-predicate booleans with
        # no `passed`) is not guessed at: the run finished, the verdict is the runner's to state.
        return "on record in results/summary.json (a unit has no `passed` field, so not derived here)"
    if not all(u["passed"] for u in s0):
        return "INVALID"
    return "H1" if all(u["passed"] for u in units.values()) else "H0"


def inspect(folder: Path) -> Report:
    """Read the folder and place it in the loop. Never edits anything."""
    folder = folder.resolve()
    prereg = folder / "prereg.md"
    if not prereg.is_file():
        return Report(
            folder,
            "not a question folder",
            blockers=[f"{folder} has no prereg.md; `newlife init <slug>` creates one"],
        )
    report = Report(folder, "")
    report.done.append("scaffold")
    origin = folder / "origin"
    if origin.is_dir():
        report.origin_files = sum(
            1 for p in origin.iterdir() if p.is_file() and p.name != "README.md"
        )

    goal = folder / "goal.md"
    if not goal.is_file():
        report.stage = "goal"
        report.blockers.append(
            "goal.md is missing (this folder predates the goal gate); record "
            "<!--@goal_gate: not_applicable ... reason ...--> rather than "
            "writing anchors after the fact"
        )
        report.next = "decide, on the record, whether the goal stage applies"
        return report
    goal_problems = goal_ready.check(goal.read_text(encoding="utf-8"))
    if goal_problems:
        report.stage = "goal"
        report.blockers.extend(goal_problems)
        report.next = (
            "fill the six anchors in goal.md with the newlife-goal skill — or waive "
            "the stage on the record"
        )
        report.decisions.append("who would bet the other way, and on what grounds")
        report.decisions.append("does the answer depend on the design or on running it")
        report.decisions.append("who changes which decision because of the answer")
        return report
    report.done.append("goal ready")

    text = prereg.read_text(encoding="utf-8")
    report.frozen_at = _frozen_at(text)
    if report.frozen_at is None:
        ledger = folder / "pilot" / "ledger.jsonl"
        runs = (
            [
                json.loads(line)
                for line in ledger.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if ledger.is_file()
            else []
        )
        if not runs:
            report.stage = "world & pilot"
            report.next = (
                "put the world into verdict.py and run `newlife pilot` — every "
                "quantity a criterion will name has to be looked at first"
            )
            return report
        units = sorted({u for run in runs for u in run.get("units", [])})
        report.done.append(
            f"{len(runs)} pilot run(s), last {runs[-1].get('at', '?')}, "
            f"units {' '.join(units) or '(none recognised)'}"
        )
        problems = pilot_coverage.check(
            pilot_coverage.piloted(text),
            pilot_coverage.ledger_units(ledger),
            pilot_coverage.waiver(text),
        )
        if problems:
            report.stage = "criteria"
            report.blockers.extend(problems)
            report.next = (
                "write the criteria with the newlife-prereg skill: every row of "
                "prereg.md section 2 marked seen / blind / mechanical"
            )
            report.decisions.append("which unit stays blind (a value never run)")
            return report
        report.done.append("criteria covered by the pilot ledger")
        report.stage = "ready to freeze"
        report.next = (
            "the person says yes, then `newlife freeze` — the one irreversible step"
        )
        report.decisions.append("freeze now? after this the criteria cannot change")
        return report

    report.done.append(f"frozen at {report.frozen_at[:12]}")
    summary = folder / "results" / "summary.json"
    reproduction = folder / "results" / "reproduction.json"
    if not summary.is_file():
        report.stage = "run"
        report.next = "`newlife run`"
        return report
    verdict = _verdict(summary, reproduction)
    if verdict is None:
        report.stage = "run interrupted"
        report.blockers.append(
            "results/summary.json exists but results/reproduction.json does "
            "not, and summary.json records no S0 unit: the self-reproduction "
            "never completed, so there is no verdict yet"
        )
        report.next = "`newlife run` again; do not commit results/ as they stand"
        return report
    report.verdict = verdict
    report.done.append(f"verdict computed: {report.verdict}")
    if not _results_committed(folder):
        report.stage = "verdict computed, not committed"
        report.next = "commit results/ (only results/), then `newlife audit`"
        report.decisions.append("commit these results as the record of this question")
        return report
    report.done.append("results committed")
    report.stage = "closeout"
    pending = (
        ["goal.md section 5 still holds the placeholder"]
        if CLOSEOUT_PLACEHOLDER in goal.read_text(encoding="utf-8")
        else []
    )
    report.blockers.extend(pending)
    report.next = (
        "`newlife audit`; then the closeout judgement in goal.md section 5 "
        "(achieved / not_achieved / regressed / not_applicable) and a mark on the "
        "exploration map"
    )
    report.decisions.append("was the goal achieved, regardless of the verdict")
    return report


def render(report: Report) -> str:
    """Plain lines the assistant can relay as they are."""
    lines = [
        f"{report.folder}",
        f"  stage      {report.stage}"
        + (
            f"  (frozen at {report.frozen_at[:12]})"
            if report.frozen_at
            else "  (not frozen)"
        ),
    ]
    if report.verdict:
        lines.append(f"  verdict    {report.verdict}")
    if report.done:
        lines.append("  done       " + " · ".join(report.done))
    for i, b in enumerate(report.blockers):
        lines.append(("  blocked    " if i == 0 else "             ") + b)
    if report.next:
        lines.append(f"  next       {report.next}")
    for i, d in enumerate(report.decisions):
        lines.append(("  decide     " if i == 0 else "             ") + d)
    if report.stage != "not a question folder":
        lines.append(
            "  origin     "
            + (
                f"{report.origin_files} file(s) from the exploration"
                if report.origin_files
                else "empty — where did this question come from?"
            )
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", type=Path, help="question folder")
    args = ap.parse_args(argv)
    report = inspect(args.folder)
    print(render(report), end="")
    return 1 if report.stage == "not a question folder" else 0


if __name__ == "__main__":
    raise SystemExit(main())
