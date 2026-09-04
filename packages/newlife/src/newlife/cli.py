"""The `newlife` command line. **One folder per question, from scaffold to audit.**

    newlife init <slug>      scaffold and commit it (prereg.md deliberately excluded)
    newlife freeze <folder>  freeze the criteria — this commit IS the timestamp
    newlife run <folder>     compute the verdict
    newlife check <folder>   three gates: vacuous criteria, silent degradation, unit alignment
    newlife blocks           list the third-party building blocks in this environment
    newlife skills install   put the question-shaping skills where your AI reads them
    newlife audit <folder>   the criteria were never edited, and the outputs post-date the freeze

**The order is the discipline**: write the criteria, freeze, run, audit. Skip the freeze
and the criteria can be adjusted afterwards to fit whatever came out — that is HARKing,
and after the fact nobody can tell it happened.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from newlife import scaffold
from newlife.gates import (
    silent_degradation_scan, unit_alignment, vacuous_criterion_scan,
)

SKILLS = Path(__file__).resolve().parent / "skills"


def _blocks() -> int:
    """List the admissible building blocks.

    **After installing the wheel a user has no way to know what is available** —
    this closes that hole.
    """
    from newlife.adapters.process_bigraph import discovery   # lazy: the extras are optional

    count = 0
    for top, module, names in discovery.blocks():
        if not names:
            print(f"[{top}] {module}")            # import failed — reported, not hidden
            continue
        count += len(names)
        print(f"  {module:52s} {', '.join(names)}")
    print(f"\n{count} admissible Process/Step classes. **Whether one can actually be "
          f"admitted also depends on the shape its `update` returns** — admit() hard-fails "
          f"on that at runtime, and this listing does not pretend to have checked it.")
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
              f"**Your edits are not overwritten**; pass --force if you meant to.")
    print(f"\nFor another AI: `newlife skills path` prints the masters — paste one in whole.")
    return 1 if skipped else 0


def _check(folder: Path) -> int:
    """The three gates that apply to **the user's own files**.

    The rest stay in the newlife repository: `check_goal_ready` reads a different goal
    anchor format, `verify_doc_claims` needs a verification-script ledger, and `run_gates`
    takes a goal/question/ledger triple — **they assume a separate document pipeline**.
    That is attribution, not omission.
    """
    runner = folder / "verdict.py"
    checks = [
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
    p_init.add_argument("slug", help="e.g. 2026-09-05-yield-input-or-outcome")
    p_init.add_argument("--no-commit", action="store_true",
                        help="do not commit the scaffold. **Careful: a later `git add -A` "
                             "then makes the freeze impossible**")
    for name, help_ in (("freeze", "freeze the criteria"), ("run", "compute the verdict"),
                        ("check", "run the gates"), ("audit", "audit the freeze")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("folder", type=Path, help="question folder")
    sub.add_parser("blocks", help="list admissible third-party building blocks")
    p_sk = sub.add_parser("skills", help="install the skills into your AI config directory")
    p_sk.add_argument("action", choices=("install", "path"))
    p_sk.add_argument("--dest", type=Path, default=Path.home() / ".claude/skills",
                      help="where to install (default ~/.claude/skills)")
    p_sk.add_argument("--force", action="store_true",
                      help="only needed when the target exists with different content — "
                           "**your edits are not overwritten by default**")

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
              f"**prereg.md deliberately left uncommitted**.\n"
              f"Next:\n"
              f"  1. edit {rel}/prereg.md and write the criteria. "
              f"**Each one must be able to go red.**\n"
              f"  2. newlife freeze {rel}      <- do not commit it before this\n"
              f"  3. edit {rel}/verdict.py and put your world in it\n"
              f"  4. newlife run {rel} && git add {rel}/results && git commit\n"
              f"  5. newlife check {rel} && newlife audit {rel}")
        return 0

    folder = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"{args.folder} is not a directory.")
    if args.cmd == "freeze":
        return scaffold.freeze(folder, cwd=cwd)
    if args.cmd == "audit":
        return scaffold.audit(folder, cwd=cwd)
    if args.cmd == "check":
        return _check(folder)
    return subprocess.run([sys.executable, str(folder / "verdict.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
