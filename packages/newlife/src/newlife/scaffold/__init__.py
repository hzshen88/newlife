"""One folder per question: scaffold it, freeze the criteria, audit the freeze.

## Layout

    my-research/                     <- one `git init`, one repository
    |-- .gitignore
    `-- questions/
        |-- 2026-09-05-<slug>/
        |   |-- prereg.md            <- the criteria, frozen here
        |   |-- verdict.py           <- the verdict runner
        |   |-- env.lock             <- what was installed for this run
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
from pathlib import Path

from newlife import provenance

TEMPLATES = Path(__file__).resolve().parent / "templates"
PREREG_SH = Path(__file__).resolve().parent / "prereg.sh"
SCAFFOLD_FILES = ("verdict.py", "env.lock")     # **prereg.md excluded** — see module docstring
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
    (folder / "prereg.md").write_text(
        (TEMPLATES / "prereg.md").read_text().format(title=title), encoding="utf-8")
    (folder / "verdict.py").write_text(
        (TEMPLATES / "verdict.py.template").read_text()
        .replace("{title}", title).replace("{slug}", slug), encoding="utf-8")
    (folder / "env.lock").write_text(
        "\n".join(provenance.env_lock_lines()) + "\n", encoding="utf-8")

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


def freeze(folder: Path, *, cwd: Path) -> int:
    """Freeze this question's criteria. **The freeze must be `prereg.md`'s first commit.**"""
    root = repo_root(cwd)
    prereg = (folder / "prereg.md").resolve()
    rel = prereg.relative_to(root)
    history = _git(root, "log", "--format=%h", "--", str(rel), check=False).stdout.strip()
    if history:
        raise SystemExit(
            f"{rel} already has git history, and the freeze must be its first commit —\n"
            f"otherwise that commit cannot prove the criteria predate the results.\n"
            f"Recovery: `git mv {rel} {rel.with_name('prereg-v2.md')}`, then freeze the\n"
            f"new file. Leave the old one in history — it is the record of this very change."
        )
    return _run_prereg(root, "freeze", str(rel))


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
