"""Answer two questions from the record: where are we, and what happens next?

`newlife status` inspects the whole research repository. `newlife status <folder>`
inspects one question. Both are read-only, and both derive their answer from the same
code: git history first, then the current workflow files. This order matters for legacy
questions whose valid freeze predates today's `goal.md` template.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from newlife import scaffold
from newlife.gates import goal_ready, pilot_coverage

STAMP_PREFIX = "**Frozen at commit:**"
CLOSEOUT_PLACEHOLDER = (
    "(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)"
)
DISPOSITION_RE = re.compile(
    r"<!--@disposition:\s*([a-z_]+)(?:\s+[—-]\s*([^>]*?))?\s*-->"
)
DISPOSITIONS = frozenset({"exploratory_closed", "abandoned", "superseded"})

DECISION = "decision"
PROGRESS = "progress"
REPAIR = "repair"
DONE = "done"


@dataclasses.dataclass
class Report:
    """One question's user-facing position and its supporting facts."""

    folder: Path
    stage: str
    category: str = PROGRESS
    trust: str = "no confirmatory conclusion"
    frozen_at: str | None = None
    done: list[str] = dataclasses.field(default_factory=list)
    blockers: list[str] = dataclasses.field(default_factory=list)
    next: str = ""
    decisions: list[str] = dataclasses.field(default_factory=list)
    verdict: str | None = None
    audit: str | None = None
    origin_files: int = 0


def _frozen_at(prereg_text: str) -> str | None:
    """The stamped freeze commit, or None while the registration is pending."""
    for line in prereg_text.splitlines():
        if line.startswith(STAMP_PREFIX):
            sha = line[len(STAMP_PREFIX) :].strip().strip("`_")
            return sha if sha and sha != "pending" else None
    return None


def _results_committed(folder: Path) -> bool:
    """True when nothing under this question's results/ is untracked or modified."""
    context = scaffold.question_context(folder)
    rel = context.relative_folder / "results"
    proc = subprocess.run(
        ["git", "-C", str(context.repo_root), "status", "--porcelain", "--", str(rel)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git could not read {folder}: {proc.stderr.strip()}")
    return proc.stdout.strip() == ""


def _prereg_has_history(folder: Path) -> bool:
    context = scaffold.question_context(folder)
    rel = context.relative_folder / "prereg.md"
    proc = subprocess.run(
        ["git", "-C", str(context.repo_root), "log", "--format=%H", "--", str(rel)],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(proc.stdout.strip())


def _verdict(summary: Path, reproduction: Path) -> str | None:
    """The verdict on record, or None when the run never got to S0."""
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
    if not all(
        isinstance(u, dict) and isinstance(u.get("passed"), bool)
        for u in units.values()
    ):
        return (
            "on record in results/summary.json "
            "(a unit has no `passed` field, so not derived here)"
        )
    if not all(u["passed"] for u in s0):
        return "INVALID"
    return "H1" if all(u["passed"] for u in units.values()) else "H0"


def _closeout_filled(goal_text: str) -> bool:
    """Whether goal.md section 5 contains an actual closeout rather than the template."""
    match = re.search(
        r"^##[ \t]+5\.[ \t]+Closeout judgement(?:[ \t]+.*)?[ \t]*$",
        goal_text,
        re.MULTILINE,
    )
    if not match:
        return False
    tail = goal_text[match.end() :]
    next_section = re.search(r"^##\s+", tail, re.MULTILINE)
    body = tail[: next_section.start()] if next_section else tail
    return bool(body.strip()) and CLOSEOUT_PLACEHOLDER not in body


def _disposition(goal_text: str) -> tuple[str | None, str | None]:
    match = DISPOSITION_RE.search(goal_text)
    if not match:
        return None, None
    return match.group(1), (match.group(2) or "").strip() or None


def _audit_summary(folder: Path) -> tuple[str, str]:
    """Return (PASS|PARTIAL|FAIL, shortest useful explanation)."""
    proc = scaffold.audit_capture(folder)
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if proc.returncode == 0:
        return "PASS", "freeze and committed-result chronology verified"
    prefix = "WARN" if proc.returncode == 3 else "FAIL"
    reason = next((line for line in lines if line.startswith(prefix)), "")
    if not reason:
        reason = next((line for line in lines if line.startswith("RESULT:")), "")
    return ("PARTIAL" if proc.returncode == 3 else "FAIL"), reason or "audit did not pass"


def _pilot_runs(ledger: Path) -> list[dict]:
    if not ledger.is_file():
        return []
    return [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _seen_units(run: dict) -> list[str]:
    units = run.get("seen_units", run.get("units", []))
    return units if isinstance(units, list) else []


def inspect(folder: Path) -> Report:
    """Inspect one question without changing files or git state."""
    folder = folder.resolve()
    prereg = folder / "prereg.md"
    if not prereg.is_file():
        return Report(
            folder,
            "not a question folder",
            category=REPAIR,
            trust="not inspected",
            blockers=[f"{folder} has no prereg.md; `newlife init <slug>` creates one"],
        )

    report = Report(folder, "")
    report.done.append("scaffold")
    origin = folder / "origin"
    if origin.is_dir():
        report.origin_files = sum(
            1 for path in origin.iterdir() if path.is_file() and path.name != "README.md"
        )

    prereg_text = prereg.read_text(encoding="utf-8")
    report.frozen_at = _frozen_at(prereg_text)
    goal = folder / "goal.md"
    goal_text = goal.read_text(encoding="utf-8") if goal.is_file() else ""
    disposition, disposition_reason = _disposition(goal_text)

    if disposition and disposition not in DISPOSITIONS:
        report.stage = "invalid disposition"
        report.category = REPAIR
        report.blockers.append(
            f"unknown @disposition {disposition!r}; use exploratory_closed, abandoned, or superseded"
        )
        report.next = "correct the @disposition marker in goal.md"
        return report

    # A completed pre-freeze closeout is a terminal exploratory record. Check it before
    # prereg history: intentionally committing the draft is how two real questions made
    # their decision not to freeze permanent.
    if report.frozen_at is None and (disposition or _closeout_filled(goal_text)):
        value = disposition or "exploratory_closed"
        report.stage = value.replace("_", " ")
        report.category = DONE
        report.trust = "exploratory record; no confirmatory conclusion"
        report.done.append("closed before freeze")
        if disposition_reason:
            report.done.append(disposition_reason)
        return report

    if report.frozen_at is None:
        if _prereg_has_history(folder):
            report.stage = "preregistration cannot be frozen"
            report.category = REPAIR
            report.blockers.append(
                "prereg.md already has git history, so a later commit cannot prove that "
                "the criteria predated the results"
            )
            report.next = (
                f"leave this record intact and create `{folder.name}-v2` for a formal round"
            )
            return report

        if not goal.is_file():
            report.stage = "goal"
            report.category = DECISION
            report.blockers.append(
                "goal.md is missing; decide whether this question needs a goal stage"
            )
            report.next = "record the decision in goal.md before designing the run"
            report.decisions.append("does the goal stage apply to this question?")
            return report

        goal_problems = goal_ready.check(goal_text)
        if goal_problems:
            report.stage = "goal"
            report.category = DECISION
            report.blockers.extend(goal_problems)
            report.next = "answer the next unresolved goal question with the newlife-goal skill"
            report.decisions.append("resolve the first missing goal anchor")
            return report
        report.done.append("goal ready")

        ledger = folder / "pilot" / "ledger.jsonl"
        try:
            runs = _pilot_runs(ledger)
        except (json.JSONDecodeError, OSError) as exc:
            report.stage = "pilot record is unreadable"
            report.category = REPAIR
            report.blockers.append(str(exc))
            report.next = "repair pilot/ledger.jsonl without inventing a run"
            return report
        if not runs:
            report.stage = "world & pilot"
            report.category = PROGRESS
            report.next = "put the world into verdict.py and run `newlife pilot`"
            return report
        units = sorted({unit for run in runs for unit in _seen_units(run)})
        report.done.append(
            f"{len(runs)} pilot run(s), last {runs[-1].get('at', '?')}, "
            f"seen {' '.join(units) or '(none recognised)'}"
        )
        try:
            covered = pilot_coverage.ledger_units(ledger)
        except (json.JSONDecodeError, SystemExit) as exc:
            report.stage = "pilot record is invalid"
            report.category = REPAIR
            report.blockers.append(str(exc))
            report.next = "repair the invalid pilot ledger entry"
            return report
        problems = pilot_coverage.check(
            pilot_coverage.piloted(prereg_text), covered, pilot_coverage.waiver(prereg_text)
        )
        if problems:
            report.stage = "criteria"
            report.category = PROGRESS
            report.blockers.extend(problems)
            report.next = "finish the seen / blind / mechanical criteria with newlife-prereg"
            return report
        report.done.append("criteria covered by the pilot ledger")
        report.stage = "ready to freeze"
        report.category = DECISION
        report.next = "review the frozen question, then run `newlife freeze` if you agree"
        report.decisions.append("freeze now? this is the irreversible step")
        return report

    # From here on the historical freeze is authoritative. Current goal templates must
    # not send a valid legacy question backwards in the lifecycle.
    report.done.append(f"frozen at {report.frozen_at[:12]}")
    report.trust = "registration frozen; no verdict yet"
    summary = folder / "results" / "summary.json"
    reproduction = folder / "results" / "reproduction.json"
    if not summary.is_file():
        report.stage = "run"
        report.category = PROGRESS
        report.next = "`newlife run`"
        return report
    try:
        verdict = _verdict(summary, reproduction)
    except (json.JSONDecodeError, OSError) as exc:
        report.stage = "result artifact is unreadable"
        report.category = REPAIR
        report.blockers.append(str(exc))
        report.next = "repair or reproduce the result artifact; do not commit it as a verdict"
        return report
    if verdict is None:
        report.stage = "run interrupted"
        report.category = PROGRESS
        report.blockers.append(
            "results/summary.json exists, but results/reproduction.json and a completed "
            "S0 record are both missing"
        )
        report.next = "run `newlife run` again; do not commit the partial results"
        return report
    report.verdict = verdict
    report.done.append(f"verdict computed: {verdict}")
    if not _results_committed(folder):
        report.stage = "verdict computed, not committed"
        report.category = DECISION
        report.trust = "verdict exists but is not yet a committed record"
        report.next = "review and commit only this question's results, then audit"
        report.decisions.append("keep these results as the formal record?")
        return report

    report.done.append("results committed")
    audit_state, audit_reason = _audit_summary(folder)
    report.audit = audit_state
    if audit_state == "FAIL":
        report.stage = "audit failed"
        report.category = REPAIR
        report.trust = "audit FAIL — the confirmatory claim is not defensible"
        report.blockers.append(audit_reason)
        report.next = "run `newlife audit` for the complete diagnosis; preserve the record"
        return report
    if audit_state == "PARTIAL":
        report.stage = "audit partial"
        report.category = REPAIR
        report.trust = "audit PARTIAL — some chronology evidence is missing"
        report.blockers.append(audit_reason)
        report.next = "run `newlife audit` and complete the missing evidence if still possible"
        return report

    report.trust = "audit PASS — freeze and result chronology verified"
    if not goal.is_file():
        report.stage = "complete (legacy)"
        report.category = DONE
        return report
    if not _closeout_filled(goal_text):
        report.stage = "closeout"
        report.category = DECISION
        report.blockers.append("goal.md section 5 has no closeout judgement")
        report.next = "record whether the goal was achieved, independently of the verdict"
        report.decisions.append("did this result achieve the stated goal?")
        return report
    report.stage = "complete"
    report.category = DONE
    return report


def render(report: Report) -> str:
    """Render the small answer a person needs; keep mechanical detail in the report."""
    lines = [str(report.folder), f"  state      {report.stage}", f"  trust      {report.trust}"]
    if report.verdict:
        lines.append(f"  verdict    {report.verdict}")
    if report.blockers:
        lines.append(f"  reason     {report.blockers[0]}")
    if report.next:
        lines.append(f"  next       {report.next}")
    if report.decisions:
        lines.append(f"  decide     {report.decisions[0]}")
    return "\n".join(lines) + "\n"


def inspect_workspace(start: Path) -> tuple[Path, list[Report]]:
    root = scaffold.repo_root(start.resolve())
    questions = root / "questions"
    if not questions.is_dir():
        return root, []
    folders = sorted(
        path for path in questions.iterdir() if path.is_dir() and (path / "prereg.md").is_file()
    )
    if not folders:
        return root, []
    with ThreadPoolExecutor(max_workers=min(4, len(folders))) as pool:
        reports = list(pool.map(inspect, folders))
    return root, reports


def render_workspace(root: Path, reports: list[Report]) -> str:
    if not reports:
        return (
            f"{root}\n\nNo formal questions yet.\n"
            'Start with: "Explore this with me: <your curiosity>"\n'
        )
    titles = {
        DECISION: "YOUR DECISION",
        PROGRESS: "IN PROGRESS",
        REPAIR: "NEEDS REPAIR",
    }
    lines = [str(root)]
    for category in (DECISION, PROGRESS, REPAIR):
        items = [report for report in reports if report.category == category]
        if not items:
            continue
        lines.extend(["", titles[category]])
        for report in items:
            lines.append(f"  {report.folder.name} — {report.stage}")
            if report.blockers and category == REPAIR:
                lines.append(f"    why: {report.blockers[0]}")
            if report.next:
                lines.append(f"    next: {report.next}")
    completed = [report for report in reports if report.category == DONE]
    if completed:
        counts: dict[str, int] = {}
        for report in completed:
            counts[report.stage] = counts.get(report.stage, 0) + 1
        summary = " · ".join(f"{count} {stage}" for stage, count in sorted(counts.items()))
        lines.extend(["", f"DONE  {len(completed)} — {summary}"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", nargs="?", type=Path, help="question folder")
    args = ap.parse_args(argv)
    if args.folder is None:
        root, reports = inspect_workspace(Path.cwd())
        print(render_workspace(root, reports), end="")
        return 0
    report = inspect(args.folder)
    print(render(report), end="")
    return 1 if report.stage == "not a question folder" else 0


if __name__ == "__main__":
    raise SystemExit(main())
