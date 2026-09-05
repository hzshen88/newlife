"""The newlife command line: one folder per question, from scaffold to audit.

    newlife init <slug>      scaffold and commit it (prereg.md deliberately excluded)
    newlife pilot <folder>   run the runner BEFORE the freeze: outputs land in pilot/<stamp>/,
                             never in results/, and the units it produced are recorded in
                             pilot/ledger.jsonl — everything a pilot produces counts as seen
    newlife freeze <folder>  freeze the criteria — this commit IS the timestamp
                             (refused while goal.md is unfilled, or while a criterion marked
                             `seen` has no pilot run behind it, or nothing is blind)
    newlife run <folder>     compute the verdict
    newlife check <folder>   five gates: goal readiness, pilot coverage, vacuous criteria,
                             silent degradation, registration <-> runner unit alignment
    newlife blocks           list the third-party building blocks in this environment
    newlife skills install   put the question-shaping skills where your AI reads them
    newlife audit <folder>   the criteria were never edited, and the outputs post-date the freeze

**The order is the discipline**: write the criteria, freeze, run, audit. Skip the freeze
and the criteria can be adjusted afterwards to fit whatever came out — that is HARKing,
and after the fact nobody can tell it happened.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from newlife import scaffold
from newlife.gates import (
    goal_ready, pilot_coverage, silent_degradation_scan, unit_alignment,
    vacuous_criterion_scan,
)

SKILLS = Path(__file__).resolve().parent / "skills"


def _blocks() -> int:
    """List the admissible building blocks.

    **After installing the wheel a user has no way to know what is available** —
    this closes that hole.
    """
    from newlife.adapters.process_bigraph import discovery   # lazy: the extras are optional

    count, unimportable = 0, []
    for top, module, names in discovery.blocks():
        if not names:
            print(f"[{top}] {module}")            # import failed — reported, not hidden
            unimportable.append(top)
            continue
        count += len(names)
        print(f"  {module:52s} {', '.join(names)}")
    print(f"\n{count} admissible Process/Step classes. Whether one can actually be "
          f"admitted also depends on the shape its `update` returns — admit() hard-fails "
          f"on that at runtime, and this listing does not pretend to have checked it.")
    # "0 admissible" reads like "there are none" when the cause is "the extras are not
    # installed". The per-package failures above already say which import failed, but the
    # summary has to say what to do about it — **naming a cause without the remedy still
    # leaves the reader stuck**, and this is the first command a new user reaches for.
    if not count and unimportable:
        print("\nNothing could be imported. The simulation backends ship as optional extras:"
              "\n    pip install 'newlife[spatio-flux]'      "
              "# Monod, dFBA (GLPK included), diffusion, particles"
              "\n    pip install 'newlife[process-bigraph]'  # the runtime alone"
              "\n'spatio-flux' pulls in 'process-bigraph' as well, so the first is enough.")
    return 0


def _skills(args) -> int:
    """Copy the skills into the AI's config directory. **Verbatim, with no transformation.**

    The master and the deployed copy are the same file. "two copies drift apart" is a
    shape this project has paid for repeatedly: a skill telling the user to run a command
    the library does not have yet, with no mechanical defence that would notice.
    """
    sources = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())
    if args.action == "path":
        for s in sources:
            print(s / "SKILL.md")
        return 0

    args.dest.mkdir(parents=True, exist_ok=True)
    skipped = []
    for src in sources:
        target = args.dest / src.name / "SKILL.md"
        body = (src / "SKILL.md").read_bytes()
        if target.exists() and target.read_bytes() != body and not args.force:
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        print(f"  installed {target}")
    for t in skipped:
        print(f"  skipped {t} — already present with different content. "
              f"Your edits are not overwritten; pass --force if you meant to.")
    print(f"\nFor another AI: `newlife skills path` prints the masters — paste one in whole.")
    return 1 if skipped else 0


def _pilot(folder: Path) -> int:
    """Run the runner before the freeze, into `pilot/<stamp>/`, and record what it produced.

    Two of the first four real registrations were INVALID because a criterion named a
    quantity nobody had looked at. **This is the looking.** Outputs never touch `results/`;
    the child process gets `NEWLIFE_PILOT=1`, which is the only condition under which
    `provenance.frozen_at` tolerates an unfrozen registration; and the units the run
    produced are appended to `pilot/ledger.jsonl`, which the freeze reads
    (`pilot_coverage`). Everything a pilot produces counts as seen.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = folder / "pilot" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "summary.json"
    proc = subprocess.run([sys.executable, str(folder / "verdict.py"), "--out", str(out)],
                          env={**os.environ, "NEWLIFE_PILOT": "1"})
    if not out.exists():
        print(f"\nThe runner exited {proc.returncode} and wrote nothing to "
              f"{out.relative_to(folder)}. Nothing was recorded. The runner must honour "
              f"--out (the scaffolded one does).")
        return 1
    units = sorted(pilot_coverage.produced(out_dir))
    entry = {"at": stamp, "out": str(out.relative_to(folder)),
             "returncode": proc.returncode, "units": units}
    with (folder / "pilot" / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    print(f"\nPilot recorded in pilot/ledger.jsonl: {' '.join(units) or 'no unit recognised'} "
          f"(runner exit {proc.returncode}; here H0 is information, not failure).\n"
          f"Everything this run produced now counts as seen: mark those rows `seen` in "
          f"prereg.md section 2,\nand keep at least one row you have never run as `blind`.")
    return 0


def _check(folder: Path) -> int:
    """The five gates that apply to **the user's own files**.

    The rest stay in the newlife repository: `verify_doc_claims` needs a
    verification-script ledger and `run_gates` takes a goal/question/ledger triple —
    **they assume a separate document pipeline**. That is attribution, not omission.

    **The goal and pilot gates are reported here but enforced at `newlife freeze`.** They have to be:
    unit alignment reads `results/`, so `check` is not runnable until the work is already
    done — and "this question was never worth asking", delivered after the
    implementation, is information that arrives too late to act on.
    """
    runner = folder / "verdict.py"
    checks = [
        ("goal ready (enforced at freeze)", lambda: goal_ready.main([str(folder)])),
        ("pilot coverage (enforced at freeze)", lambda: pilot_coverage.main([str(folder)])),
        ("vacuous criteria", lambda: vacuous_criterion_scan.main([str(runner)])),
        ("silent degradation", lambda: silent_degradation_scan.main([str(runner)])),
        ("registration <-> runner unit alignment", lambda: unit_alignment.main([str(folder)])),
    ]
    failed = []
    for name, run in checks:
        print(f"-- {name} " + "-" * max(0, 46 - len(name)))
        if run() != 0:
            failed.append(name)
    print()
    if failed:
        print(f"{len(failed)}/{len(checks)} gates red: {', '.join(failed)}")
        return 1
    print(f"All {len(checks)} gates passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="newlife", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="scaffold a question folder")
    p_init.add_argument(
        "slug",
        help="one safe path component, e.g. 2026-09-05-yield-input-or-outcome",
    )
    p_init.add_argument("--no-commit", action="store_true",
                        help="do not commit the scaffold; a later 'git add -A' then makes "
                             "the freeze impossible")
    for name, help_ in (("pilot", "run the runner into pilot/, before the freeze"),
                        ("freeze", "freeze the criteria"), ("run", "compute the verdict"),
                        ("check", "run the gates"), ("audit", "audit the freeze")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("folder", type=Path, help="question folder")
    sub.add_parser("blocks", help="list admissible third-party building blocks")
    p_sk = sub.add_parser("skills", help="install the skills into your AI config directory")
    p_sk.add_argument("action", choices=("install", "path"))
    p_sk.add_argument("--dest", type=Path, default=Path.home() / ".claude/skills",
                      help="where to install (default ~/.claude/skills)")
    p_sk.add_argument("--force", action="store_true",
                      help="only needed when the target exists with different content; "
                           "your edits are not overwritten by default")

    args = ap.parse_args(argv)
    cwd = Path.cwd()

    if args.cmd == "blocks":
        return _blocks()
    if args.cmd == "skills":
        return _skills(args)
    if args.cmd == "init":
        folder = scaffold.init(args.slug, cwd=cwd, commit=not args.no_commit)
        rel = folder.relative_to(scaffold.repo_root(cwd))
        print(f"Created {rel}/ — scaffold "
              f"{'committed' if not args.no_commit else 'NOT committed'}, "
              f"prereg.md deliberately left uncommitted.\n"
              f"Next:\n"
              f"  0. edit {rel}/goal.md — six anchors. **It is red on purpose**: the "
              f"freeze is refused until it is filled in, or the stage waived. "
              f"If this question came out of an exploration, its record goes in {rel}/origin/.\n"
              f"  1. edit {rel}/verdict.py and put your world in it (exploratory for now)\n"
              f"  2. newlife pilot {rel}       <- look at every quantity a criterion will name; "
              f"everything it produces counts as seen\n"
              f"  3. edit {rel}/prereg.md and write the criteria; mark every row "
              f"seen / blind / mechanical. Each one must be able to go red.\n"
              f"  4. newlife freeze {rel}      <- do not commit prereg.md before this "
              f"(never `git add -A` here)\n"
              f"  5. newlife run {rel} && git add {rel}/results && git commit\n"
              f"  6. newlife check {rel} && newlife audit {rel}")
        return 0

    folder = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"{args.folder} is not a directory.")
    if args.cmd == "pilot":
        return _pilot(folder)
    if args.cmd == "freeze":
        return scaffold.freeze(folder, cwd=cwd)
    if args.cmd == "audit":
        return scaffold.audit(folder, cwd=cwd)
    if args.cmd == "check":
        return _check(folder)
    return subprocess.run([sys.executable, str(folder / "verdict.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
