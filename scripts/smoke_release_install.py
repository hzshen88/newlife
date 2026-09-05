"""Install built wheels offline and exercise the external user-repository flow."""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import tempfile


def _run(
    *args: str | pathlib.Path, cwd: pathlib.Path | None = None, expected: int = 0
) -> str:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("VIRTUAL_ENV", None)
    process = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != expected:
        raise SystemExit(
            f"command returned {process.returncode}, expected {expected}: {' '.join(map(str, args))}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return process.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=pathlib.Path)
    args = parser.parse_args()
    dist = args.dist.resolve()
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required for the release installation smoke test")

    with tempfile.TemporaryDirectory(prefix="newlife-release-smoke-") as raw:
        root = pathlib.Path(raw)
        venv = root / ".venv"
        _run(uv, "venv", venv, "--python", "3.12")
        python = venv / "bin" / "python"
        newlife = venv / "bin" / "newlife"
        _run(
            uv,
            "pip",
            "install",
            "--python",
            python,
            "--no-index",
            "--find-links",
            dist,
            "newlife",
        )
        _run(
            python,
            "-c",
            "import importlib.resources as r, random, newlife, proofroot; "
            "assert r.files('proofroot').joinpath('vectors/evidencecore_rng_v1.json').is_file(); "
            "assert r.files('newlife').joinpath('scaffold/prereg.sh').is_file(); "
            "bank=proofroot.RngBank(42, ['mutation', 'selection'], "
            "stream_factory=random.Random); "
            "assert bank.rng_stream('mutation') is bank.rng_stream('MUTATION'); "
            "assert isinstance(proofroot.canonical_bytes({'answer': 42}), bytes)",
        )

        repo = root / "user-repository"
        repo.mkdir()
        _run("git", "init", "-q", repo)
        _run("git", "config", "user.name", "Release Smoke", cwd=repo)
        _run("git", "config", "user.email", "release-smoke@example.invalid", cwd=repo)
        (repo / ".gitignore").write_text("base\n", encoding="utf-8")
        (repo / "baseline.txt").write_text("base\n", encoding="utf-8")
        _run("git", "add", ".gitignore", "baseline.txt", cwd=repo)
        _run("git", "commit", "-qm", "baseline", cwd=repo)

        (repo / ".gitignore").write_text("base\nuser-change\n", encoding="utf-8")
        (repo / "staged.txt").write_text("preserve me\n", encoding="utf-8")
        _run("git", "add", "staged.txt", cwd=repo)

        slug = "2026-09-05-release-smoke"
        question = pathlib.Path("questions") / slug
        _run(newlife, "init", slug, cwd=repo)
        committed = set(
            _run(
                "git",
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                "HEAD",
                cwd=repo,
            ).splitlines()
        )
        expected_commit = {
            str(question / "env.lock"),
            str(question / "goal.md"),
            str(question / "verdict.py"),
        }
        if committed != expected_commit:
            raise SystemExit(f"init committed unexpected paths: {committed}")
        if _run("git", "diff", "--cached", "--name-only", cwd=repo).splitlines() != [
            "staged.txt"
        ]:
            raise SystemExit("init did not preserve unrelated staged work")

        # **The freeze must be refused while goal.md is untouched.** Asserting this from
        # a freshly installed wheel is the only place that proves the gate ships and
        # bites — a gate that is green in the source tree and absent from the wheel is
        # the exact shape this release check exists to catch.
        _run(newlife, "freeze", question, cwd=repo, expected=1)
        (repo / question / "goal.md").write_text(
            "<!--@goal_gate: not_applicable ... release smoke test, not a question ...-->\n",
            encoding="utf-8")

        _run(newlife, "freeze", question, cwd=repo)
        _run(newlife, "audit", question, cwd=repo, expected=3)
        _run(newlife, "run", question, cwd=repo)
        _run(newlife, "check", question, cwd=repo)
        _run("git", "add", question / "results", cwd=repo)
        _run(
            "git",
            "commit",
            "-qm",
            "record verdict",
            "--",
            question / "results",
            cwd=repo,
        )
        _run(newlife, "audit", question, cwd=repo)

    print("fresh-wheel external-repository smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
