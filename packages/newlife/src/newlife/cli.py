"""The newlife command line: one folder per question, from scaffold to audit.

    newlife start <dir>      one command from pip install to talking to your AI: git init,
                             NEXT.md, and the skills installed into every AI tool found
    newlife init <slug>      scaffold and commit it (prereg.md deliberately excluded)
    newlife pilot <folder>   run the runner BEFORE the freeze: outputs land in pilot/<stamp>/,
                             never in results/, and the units it produced are recorded in
                             pilot/ledger.jsonl — everything a pilot produces counts as seen
    newlife freeze <folder>  freeze the criteria — this commit IS the timestamp
                             (refused while goal.md is unfilled, or while a criterion marked
                             `seen` has no pilot run behind it, or nothing is blind);
                             --data FILE... pins external inputs by hash, re-checked by audit
    newlife run <folder>     compute the verdict
    newlife status <folder>  where is this question: stage, what is done, what blocks, what is
                             next, what the person has to decide — read from the folder
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
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from newlife import provenance, scaffold, status
from newlife.gates import (
    goal_ready, pilot_coverage, silent_degradation_scan, unit_alignment,
    vacuous_criterion_scan,
)

SKILLS = Path(__file__).resolve().parent / "skills"


EXTRA_FOR = {"process_bigraph": "newlife[process-bigraph]",
             "spatio_flux": "newlife[spatio-flux]"}
"""Which optional extra provides which top-level package. **Only what `pyproject.toml`
actually declares** — `bsp` is scanned by discovery but is not a newlife extra, and
printing an install command that cannot resolve is worse than printing none."""

EXTRA_NOTE = {"newlife[spatio-flux]": "      # Monod, dFBA (GLPK included), diffusion, particles",
              "newlife[process-bigraph]": "  # the runtime alone"}


def _blocks() -> int:
    """List the admissible building blocks.

    **After installing the wheel a user has no way to know what is available** —
    this closes that hole.
    """
    from newlife.adapters.process_bigraph import discovery   # lazy: the extras are optional

    count, missing, broken = 0, [], []
    for top, module, names in discovery.blocks():
        if not names:
            print(f"[{top}] {module}")            # import failed — reported, not hidden
            # **"absent" and "installed but broken" need different advice**, and the only
            # thing separating them is the exception type discovery renders into that line.
            # Telling someone to install what they already have wastes the one command they
            # were going to try.
            (missing if "ModuleNotFoundError" in module else broken).append(top)
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
    # **Reported whenever something is absent, not only when everything is.** A user who
    # has `process-bigraph` and not `spatio-flux` sees a listing that works and never
    # learns the backends exist.
    if extras := sorted({EXTRA_FOR[t] for t in missing if t in EXTRA_FOR}):
        head = ("Nothing could be imported." if not count else
                "Some backends are not installed.")
        print(f"\n{head} They ship as optional extras:")
        for extra in extras:
            print(f"    pip install '{extra}'{EXTRA_NOTE[extra]}")
        if len(extras) > 1:
            print("'spatio-flux' pulls in 'process-bigraph' as well, so the first is enough.")
        print("Install before you freeze: `env.lock` is written from the live environment "
              "at the freeze,\nand S1 compares the run against it.")
    if outside := sorted({t for t in missing if t not in EXTRA_FOR}):
        print(f"\n{', '.join(outside)}: not shipped as a newlife extra. Install it "
              f"yourself if you need it.")
    if broken:
        print(f"\n{', '.join(sorted(set(broken)))}: installed, but the import failed "
              f"(above). **That is the package's own problem, not your configuration** — "
              f"reinstalling it will not help, and nothing here can admit a class it "
              f"cannot import.")
    return 0


KNOWN_SKILL_DIRS = ("~/.claude/skills", "~/.codex/skills", "~/.workbuddy/skills")
"""Where the AI tools this project knows about read skills from. `skills install` with no
`--dest` installs into every one of these that exists on the machine."""
SKIP_PARTS = frozenset({"__pycache__", ".ruff_cache", ".pytest_cache"})


def _skill_sources() -> list[tuple[str, Path]]:
    """Every skill this install can offer: newlife's own, plus exloop's.

    exloop is the exploration stage upstream of newlife and a separate package on purpose —
    one master, in its own repository — and a declared dependency, so it is normally present;
    the ImportError branch is a broken or partial install. newlife never imports its code; it only finds its
    files, and the interface between the two stays files (`handoff` writes into a question's
    `origin/`).
    """
    found = [("newlife", p) for p in sorted(SKILLS.iterdir()) if (p / "SKILL.md").is_file()]
    try:
        import exloop  # a dependency; missing only in a broken install
    except ImportError:
        return found
    found += [("exloop", p) for p in sorted(exloop.skills_dir().iterdir())
              if (p / "SKILL.md").is_file()]
    return found


def _skill_files(skill: Path) -> list[Path]:
    """Every file of one skill: SKILL.md, references, scripts — caches excluded."""
    return sorted(p for p in skill.rglob("*")
                  if p.is_file() and not (SKIP_PARTS & set(p.relative_to(skill).parts)))


def _skills(args) -> int:
    """Copy the skills into the AI's config directories. **Verbatim, with no transformation.**

    The master and the deployed copy are the same bytes. "two copies drift apart" is a
    shape this project has paid for repeatedly: a skill telling the user to run a command
    the library does not have yet, with no mechanical defence that would notice. Whole
    directories are copied, not just `SKILL.md` — the exploration skill carries references
    and a helper script, and the first version of this command could not install it.
    """
    sources = _skill_sources()
    has_exloop = any(provider == "exloop" for provider, _ in sources)
    if args.action == "path":
        for provider, skill in sources:
            print(f"{skill / 'SKILL.md'}  [{provider}]")
        if not has_exloop:
            print("(the exploration skill is not listed: the exloop package is not installed)",
                  file=sys.stderr)
        return 0

    dests = [Path(d).expanduser() for d in (args.dest or [])]
    if not dests:
        dests = [d for d in (Path(s).expanduser() for s in KNOWN_SKILL_DIRS) if d.is_dir()]
    if not dests:
        print("No AI skills directory found (looked for " + ", ".join(KNOWN_SKILL_DIRS) + ").\n"
              "Pass --dest <dir>, or run `newlife skills path` and paste a master into your AI "
              "by hand.")
        return 1

    skipped: list[Path] = []
    for dest in dests:
        for _provider, skill in sources:
            for src in _skill_files(skill):
                target = dest / skill.name / src.relative_to(skill)
                body = src.read_bytes()
                if target.exists():
                    if target.read_bytes() == body:
                        continue
                    if not args.force:
                        skipped.append(target)
                        continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                print(f"  installed {target}")
    for t in skipped:
        print(f"  skipped {t} — already present with different content. "
              f"Your edits are not overwritten; pass --force if you meant to.")
    if not has_exloop:
        print("\nThe exploration skill was not installed: the exloop package is not present "
              "(pip install exloop). newlife's own two skills were.")
    print("\nFor another AI: `newlife skills path` prints the masters — paste one in whole.")
    return 1 if skipped else 0


def _start(args) -> int:
    """From `pip install` to "now talk to your AI" in one command.

    Creates the research repository (git is required: the freeze commit is the timestamp),
    checks that git has an identity to sign with, writes `NEXT.md` (what happens from here
    and the one sentence to say to the AI) and a `.gitignore`, and installs the skills into
    every AI configuration directory found on this machine. Running it again is harmless.
    The only thing it will not do is invent a git identity — that is a signature.
    """
    root = Path(args.dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        print(f"  git init      {root}")
    missing = [key for key in ("user.name", "user.email")
               if subprocess.run(["git", "-C", str(root), "config", "--get", key],
                                 capture_output=True, text=True).returncode != 0]
    for name, template in ((".gitignore", "gitignore"), ("NEXT.md", "next.md")):
        target = root / name
        if not target.exists():
            shutil.copyfile(scaffold.TEMPLATES / template, target)
            print(f"  wrote         {target}")
    rc = _skills(argparse.Namespace(action="install", dest=args.skills_dest, force=args.force))
    has_exloop = any(provider == "exloop" for provider, _ in _skill_sources())
    if has_exloop:
        print(f"\nOpen {root} in your AI tool (Claude Code, Codex, ...) and say:\n"
              f'    "Explore this with me: <your curiosity>"\n'
              f"The rest is conversation. NEXT.md in the repository says what happens from here.")
    else:
        # **Do not promise the exploration stage when it is not there.** The first review of
        # this command found it reporting success, noting the skill was missing, and then
        # telling the person to start exploring anyway.
        print(f"\nThe exploration stage is not available on this machine: the `exloop` package "
              f"is not installed (it is a dependency of newlife, so this install is incomplete); "
              f"only newlife's own skills were installed.\n"
              f"    pip install exloop        # then run `newlife start .` again\n"
              f"Until then, open {root} in your AI tool and frame a question directly with the "
              f"`newlife-goal` skill; NEXT.md says what happens from there.")
    if missing:
        print("\nBefore anything can be committed, git needs an identity — it is a signature, "
              "so it is not guessed:\n"
              + "".join(f'    git -C {root} config {key} "..."\n' for key in missing))
        return 1
    return 1 if not has_exloop else rc


def _pilot(folder: Path) -> int:
    """Run the runner before the freeze, into `pilot/<stamp>/`, and record what it produced.

    Two of the first four real registrations were INVALID because a criterion named a
    quantity nobody had looked at. **This is the looking.** Outputs never touch `results/`;
    the child process gets `NEWLIFE_PILOT=1`, which is the only condition under which
    `provenance.frozen_at` tolerates an unfrozen registration; and the units the run
    produced are appended to `pilot/ledger.jsonl`, which the freeze reads
    (`pilot_coverage`). Everything a pilot produces counts as seen.
    """
    # **The earliest place this can be caught.** Without the stamp placeholder the runner
    # dies inside `provenance.frozen_at` with "it is not a registration", the pilot records
    # nothing, and the freeze then refuses for the *wrong* reason ("no pilot") — three
    # messages, none of which names the missing line.
    if scaffold.ensure_stamp_placeholder(folder / "prereg.md"):
        print(f"  {scaffold.STAMP_PLACEHOLDER!r} was missing from prereg.md and has been restored")

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
    # **Which environment this pilot ran in.** Without it the pilot proves only that the
    # runner ran *somewhere*: install a package afterwards and the freeze records the new
    # environment, S1 goes green against it, and nothing ever executed the runner there.
    # `pilot_coverage` compares this with the live environment at the freeze.
    # **What was being bet on when this pilot ran.** Rule one sends the pilot to look at
    # every quantity a criterion names, so it can hand you the answer to the main criterion
    # before anything is frozen — and rewriting the bet afterwards leaves no trace in any
    # file. `pilot_coverage` compares this digest at the freeze. Four anchors only, not the
    # whole file: goal.md section 5 is written after the run and section 1's prose grows.
    goal_md = folder / "goal.md"
    goal_sha = (pilot_coverage.goal_commitments(goal_md.read_text(encoding="utf-8"))
                if goal_md.exists() else None)
    entry = {"at": stamp, "out": str(out.relative_to(folder)),
             "returncode": proc.returncode, "units": units,
             "env_sha256": provenance.env_digest(), "goal_sha256": goal_sha}
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
    ap.add_argument("--version", action="version",
                    version=f"newlife {importlib.metadata.version('newlife')}")
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
                        ("status", "where is this question: stage, blockers, next step"),
                        ("check", "run the gates"), ("audit", "audit the freeze")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("folder", type=Path, help="question folder")
        if name == "freeze":
            p.add_argument("--data", nargs="+", type=Path, default=(), metavar="FILE",
                           help="external input files the verdict reads (downloaded data, "
                                "reference tables); their hashes are frozen with the criteria "
                                "and re-checked by audit")
    sub.add_parser("blocks", help="list admissible third-party building blocks")
    p_sk = sub.add_parser("skills", help="install the skills into your AI config directories")
    p_sk.add_argument("action", choices=("install", "path"))
    p_sk.add_argument("--dest", action="append", type=Path, default=None,
                      help="where to install (repeatable); default: every AI skills "
                           "directory found on this machine")
    p_sk.add_argument("--force", action="store_true",
                      help="only needed when the target exists with different content; "
                           "your edits are not overwritten by default")
    p_start = sub.add_parser("start", help="create a research repository and install the "
                                           "skills: one command from pip install to talking "
                                           "to your AI")
    p_start.add_argument("dir", type=Path, help="the research repository to create or reuse")
    p_start.add_argument("--skills-dest", action="append", type=Path, default=None,
                         help="where to install the skills (repeatable); default: every AI "
                              "skills directory found on this machine")
    p_start.add_argument("--force", action="store_true",
                         help="overwrite installed skills that differ from the masters")

    args = ap.parse_args(argv)
    cwd = Path.cwd()

    if args.cmd == "blocks":
        return _blocks()
    if args.cmd == "skills":
        return _skills(args)
    if args.cmd == "start":
        return _start(args)
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
        return scaffold.freeze(folder, cwd=cwd, data=tuple(args.data))
    if args.cmd == "audit":
        return scaffold.audit(folder, cwd=cwd)
    if args.cmd == "status":
        return status.main([str(folder)])
    if args.cmd == "check":
        return _check(folder)
    return subprocess.run([sys.executable, str(folder / "verdict.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
