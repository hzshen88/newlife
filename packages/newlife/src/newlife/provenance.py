"""Where a verdict artifact came from: **what exactly was this run made on.**

## Why the version string is not enough

`newlife`'s version is pinned in `pyproject.toml` and comes out as `0.1.0` on every
build — **it identifies nothing**. The first real user run hit this immediately: the
artifact wanted to record which build of newlife produced it, and technically could not.

`uv pip freeze` does not help either: it records
`newlife @ file:///.../newlife-0.1.0-py3-none-any.whl` — **a local path**, neither
reproducible nor checkable on another machine.

So what is recorded here is a **content digest of the installed package**: every stable
file under the package directory (Python, shell, templates, and skills), hashed in sorted
relative-path order with platform-neutral path spelling. Interpreter caches are excluded.
The digest is identical wherever the same wheel is installed and changes if any shipped
content byte changes.

**This is not a field for humans to read. It is what answers "does it still match".**
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import site
import sys
from pathlib import Path
from typing import Any


def package_digest(package: Any) -> str:
    """Content digest of every stable file shipped inside an installed package.

    **A version string can lie about what is installed. This cannot.**
    """
    root = Path(package.__file__).resolve().parent
    digest = hashlib.sha256()
    paths = sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    )
    for path in paths:
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts:
            continue
        # POSIX spelling makes the digest identical for the same wheel on
        # Windows and Unix instead of hashing platform-native separators.
        digest.update(relative.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    """sha256 of one file. Used to pin `env.lock`."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(**extra: Any) -> dict[str, Any]:
    """The provenance block written into the artifact.

    Put question-specific facts in `extra` — the freeze commit, the solver identity, the
    random seed. **A rule established earlier: the solver identity belongs inside the
    conjunction**, because byte-identical reproduction buys "the same solver made the same
    choice", not "the same mathematical answer". This is where that rule has a home.
    """
    import newlife

    location = Path(newlife.__file__).resolve().parent
    try:
        version = importlib.metadata.version("newlife")
    except importlib.metadata.PackageNotFoundError:
        # Running straight from a source tree (not installed as a distribution).
        # **Do not paper over this with "unknown"** — that reads like a version string.
        # Write a sentence nobody could mistake for one.
        version = "UNAVAILABLE: newlife is not installed as a distribution"
    return {
        "newlife_version": version,
        "newlife_source_sha256": package_digest(newlife),
        "newlife_location": str(location),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        **extra,
    }


def frozen_at(prereg: Path) -> str:
    """Read the freeze commit from the registration's own stamp line.

    **The runner must not hand-write this SHA.** Hand-written, it drifts — and it is the
    entire evidence that the artifact post-dates the freeze: a SHA cannot be written down
    before the commit it names exists. **Naming it is dating yourself after it.**
    """
    for line in Path(prereg).read_text().splitlines():
        if line.startswith("**Frozen at commit:**"):
            sha = line.split(":**", 1)[1].strip().strip("`_")
            if sha and sha != "pending":
                return sha
            if os.environ.get("NEWLIFE_PILOT"):
                # `newlife pilot` runs the runner **before** the freeze on purpose — that is
                # what a pilot is. The artifact must say so in words nobody could mistake
                # for a commit, and only `newlife pilot` sets this variable.
                return "UNFROZEN: pilot run before the freeze, carries no evidential weight"
            raise SystemExit(f"{prereg} is not frozen yet — run `newlife freeze` first.")
    raise SystemExit(f"{prereg} has no `**Frozen at commit:**` line; it is not a registration.")


def env_lock_lines() -> list[str]:
    """What is installed in the current environment. **stdlib only** — no pip, no uv.

    A `uv venv` **has no pip**, so `pip freeze` — the most natural way a user would record
    their environment — simply does not exist under this toolchain. And `uv pip freeze`
    records a local wheel as `name @ file:///…`, **a path that means nothing on another
    machine**. This sidesteps both.

    Distributions are read from the interpreter's site-packages directories, **not from
    `sys.path` as it stands** at the moment of the call. Libraries such as `ray` insert a
    vendored `thirdparty_files/` directory into `sys.path` when imported, and a lock that
    changed with import order would make S1 depend on what the runner happened to import
    before it looked: found 2026-09-06, when a process that had imported spatio-flux (and
    through it ray) recorded `colorama` and the runner subprocess, which had not, did not.
    """
    paths = list(site.getsitepackages())
    if site.ENABLE_USER_SITE:
        paths.append(site.getusersitepackages())
    seen = {}
    for dist in importlib.metadata.distributions(path=paths):
        name = dist.metadata["Name"]
        if name:
            seen[name.lower()] = f"{name}=={dist.version}"
    return [seen[k] for k in sorted(seen)]
