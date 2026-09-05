"""One folder per question: scaffold it, freeze the criteria, audit the freeze.

## Layout

    my-research/                     <- one `git init`, one repository
    |-- .gitignore
    `-- questions/
        |-- 2026-09-05-<slug>/
        |   |-- goal.md              <- is this worth asking? red until its six anchors are filled
        |   |-- origin/              <- where the question came from (an exploration's record)
        |   |-- prereg.md            <- the criteria, frozen here
        |   |-- verdict.py           <- the verdict runner
        |   |-- env.lock             <- what was installed for this run
        |   |-- pilot/               <- `newlife pilot` runs + ledger.jsonl; read by the freeze
        |   `-- results/
        `-- 2026-09-12-<another>/    <- **a sibling, not a child**

**The registration and the outputs must share a repository**: the chronology check proves
"the outputs post-date the freeze" from git ancestry, and **ancestry exists only within
one repository**. This project walked into that itself — registrations in one repository,
artifacts in another, so chronology was **never established for any of 22 registrations**,
while the old script printed "predictions pre-date outputs" after examining zero outputs.

**But not one repository per question**: that would mean N `git init`s, N remotes, and no
way to share helper code. One repository with several question folders shares ancestry
just as well — verified.

## Why `init` commits on your behalf

**The freeze must be `prereg.md`'s first commit.** And the most natural thing a user does
after creating a folder is `git add -A && git commit` — which destroys that ability in one
step, irreversibly (the history is already there). So `init` **commits the scaffold for
the user and leaves exactly `prereg.md` uncommitted**: there is then no reason to run
`git add -A` before freezing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from newlife import provenance
from newlife.gates import goal_ready, pilot_coverage

TEMPLATES = Path(__file__).resolve().parent / "templates"
PREREG_SH = Path(__file__).resolve().parent / "prereg.sh"
SCAFFOLD_FILES = ("goal.md", "verdict.py", "env.lock", "origin/README.md")
"""**`prereg.md` excluded** — see the module docstring; the freeze must be its first commit.

`origin/README.md` says what belongs in `origin/`: the record of the exploration this
question came from. None of the first four real questions recorded that.

`goal.md` is committed with the rest: it is not frozen, and it precedes the registration.
**It is written deliberately red** — `newlife freeze` refuses until its six anchors are
filled in. A scaffold that satisfied its own gate would make that gate true by
construction, and it would never once ask the user a question.
"""
SAFE_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=check)


def repo_root(start: Path) -> Path:
    """The enclosing git repository root.

    **Hard-fails outside a repository** — without git there is no timestamp.
    """
    try:
        out = _git(start, "rev-parse", "--show-toplevel")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            f"{start} is not inside a git repository. Every bit of credibility a verdict\n"
            f"has comes from git history (the freeze commit IS the timestamp), so there is\n"
            f"no fallback here: run `git init` first.\nUnderlying error: {exc}"
        ) from exc
    # Git preserves the spelling used to enter a worktree.  On macOS, for
    # example, a repository reached through /tmp may be reported under /tmp
    # even though Path.resolve() spells the same directory /private/tmp.
    # Canonicalise once so every later relative-path calculation uses the
    # same namespace.
    return Path(out.stdout.strip()).resolve()


def init(slug: str, *, cwd: Path, commit: bool = True) -> Path:
    """Create a question folder and commit the scaffold (all but `prereg.md`)."""
    if not SAFE_SLUG.fullmatch(slug):
        raise SystemExit(
            "slug must be one safe path component: start with an ASCII letter or digit, "
            "then use only letters, digits, '.', '_', or '-'."
        )
    root = repo_root(cwd)
    folder = root / "questions" / slug
    if folder.exists():
        raise SystemExit(f"{folder} already exists — pick another slug rather than\n"
                         f"overwriting an existing question.")
    (folder / "results").mkdir(parents=True)

    title = slug.split("-", 3)[-1].replace("-", " ") or slug
    (folder / "goal.md").write_text(
        (TEMPLATES / "goal.md").read_text().replace("{title}", title), encoding="utf-8")
    (folder / "prereg.md").write_text(
        (TEMPLATES / "prereg.md").read_text().format(title=title), encoding="utf-8")
    (folder / "verdict.py").write_text(
        (TEMPLATES / "verdict.py.template").read_text()
        .replace("{title}", title).replace("{slug}", slug), encoding="utf-8")
    (folder / "env.lock").write_text(
        "\n".join(provenance.env_lock_lines()) + "\n", encoding="utf-8")
    (folder / "origin").mkdir()
    shutil.copyfile(TEMPLATES / "origin-README.md", folder / "origin" / "README.md")

    gitignore = root / ".gitignore"
    created_gitignore = not gitignore.exists()
    if created_gitignore:
        shutil.copyfile(TEMPLATES / "gitignore", gitignore)

    rel = folder.relative_to(root)
    if commit:
        paths = [str(rel / name) for name in SCAFFOLD_FILES]
        if created_gitignore:
            paths.append(".gitignore")
        _git(root, "add", *paths)
        # Limit the commit as well as the preceding add.  A plain `git commit`
        # would also consume unrelated changes the user had already staged.
        _git(root, "commit", "-m",
             f"question({slug}): scaffold (prereg.md left uncommitted, awaiting freeze)",
             "--", *paths)
    return folder


def freeze(folder: Path, *, cwd: Path, data: tuple[Path, ...] = ()) -> int:
    """Freeze this question's criteria. **The freeze must be `prereg.md`'s first commit.**

    `env.lock` is rewritten from the live environment and pinned together with the
    criteria. From here on "the environment" means that file: the runner's S1 compares the
    packages installed at run time against it, and `audit` proves it never changed after
    the freeze. Before this, the scaffolded S1 compared the file's digest with a digest of
    the same file taken a moment earlier — true by construction — and it shipped in every
    early question.

    `data` names external input files the question reads but did not generate — a
    downloaded expression compendium, a reference network. Their git blob hashes are
    written into the registration under "## Frozen data checksums" before the freeze
    commit, and `newlife audit` fails if any of them changes afterwards. The first four
    real questions read only simulated data; the first one to download a dataset had no
    way to pin it — this is that way. The files themselves need not be tracked by git
    (they usually are not): `git hash-object` hashes what is on disk.

    **A red `goal.md` blocks the freeze.** This is the last moment at which the answer
    still costs nothing: after it comes the implementation, and a question nobody would
    bet against is otherwise something you find out about only when the verdict turns out
    to carry no information. `newlife check` reports the same gate but cannot stand in
    for this one — it also runs unit alignment, which reads `results/`, so it is not
    runnable until the work is already done.
    """
    root = repo_root(cwd)
    prereg = (folder / "prereg.md").resolve()
    rel = prereg.relative_to(root)
    history = _git(root, "log", "--format=%h", "--", str(rel), check=False).stdout.strip()
    if history:
        raise SystemExit(
            f"{rel} already has git history, and the freeze must be its first commit —\n"
            f"otherwise that commit cannot prove the criteria predate the results.\n"
            f"Recovery: start a new question folder — `newlife init {folder.name}-v2` — move\n"
            f"your criteria into its prereg.md and freeze there. Leave this folder as it is:\n"
            f"it is the record of this very mistake. Renaming the file does not work (every\n"
            f"command reads prereg.md), and re-freezing is never allowed."
        )
    # **After the history check, not before.** That one reports an already-irreversible
    # state and its recovery must not be masked by a gate about a file you can still edit.
    ready = goal_ready.main([str(folder)])
    # **Flush before anything else writes.** The gate prints to stdout; SystemExit goes to
    # stderr and `prereg.sh` writes from a subprocess. Piped, stdout is block-buffered, so
    # without this the gate's output lands after the text that refers to it.
    sys.stdout.flush()
    if ready != 0:
        raise SystemExit(
            "The goal is not ready (above), so the freeze is refused.\n"
            "Fill in the six anchors in goal.md — or, if this question genuinely has no\n"
            "goal stage, record that instead of leaving the file half-filled:\n"
            "    <!--@goal_gate: not_applicable ... your reason ...-->")
    # **Second gate, same moment.** Two of the first four real registrations were INVALID
    # because a criterion named a quantity nobody had looked at; the rule lived in a skill's
    # prose and stopped nothing. `newlife pilot` records the looking, this reads the record.
    covered = pilot_coverage.main([str(folder)])
    sys.stdout.flush()
    if covered != 0:
        raise SystemExit(
            "The criteria are not covered by a pilot (above), so the freeze is refused.\n"
            "Run `newlife pilot` on the folder and mark every row of prereg.md section 2\n"
            "seen / blind / mechanical — or waive on the record, inside prereg.md:\n"
            "    <!--@pilot_gate: no_blind_waived ... why nothing is blind ...-->\n"
            "    <!--@pilot_gate: not_applicable ... why the stage does not apply ...-->")
    # env.lock: rewrite from the live environment, commit if that changed anything, and pin
    # it first — the runner's S1 and the audit's DATA arm both hang off this file.
    env_lock = folder / "env.lock"
    live = "\n".join(provenance.env_lock_lines()) + "\n"
    if not env_lock.exists() or env_lock.read_text(encoding="utf-8") != live:
        env_lock.write_text(live, encoding="utf-8")
    env_rel = str(env_lock.resolve().relative_to(root))
    if _git(root, "status", "--porcelain", "--", env_rel).stdout.strip():
        _git(root, "add", "--", env_rel)
        _git(root, "commit", "-q", "-m",
             f"question({folder.name}): env.lock refreshed at the freeze", "--", env_rel)
        print("  env.lock rewritten from the live environment and committed")
    pinned = [env_rel]
    for path in data:
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise SystemExit(f"--data {path}: no such file. Pin only files that exist now — "
                             f"the freeze records what the verdict will read.")
        try:
            pinned.append(str(resolved.relative_to(root)))
        except ValueError as exc:
            raise SystemExit(f"--data {path} is outside the repository {root}; the audit "
                             f"can only re-hash files it can find from the repository root.") from exc
    return _run_prereg(root, "freeze", str(rel), *pinned)


def audit(folder: Path, *, cwd: Path) -> int:
    """Audit: the criteria were never edited, and the outputs post-date the freeze.

    **The scope is narrowed to this question automatically.**
    """
    root = repo_root(cwd)
    rel = (folder / "prereg.md").resolve().relative_to(root)
    return _run_prereg(root, "audit", "--results", str(rel.parent / "results"), str(rel))


def _run_prereg(root: Path, *args: str) -> int:
    proc = subprocess.run(["sh", str(PREREG_SH), *args], cwd=root)
    return proc.returncode
