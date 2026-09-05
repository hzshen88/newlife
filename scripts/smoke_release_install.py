"""Install the built wheels into a fresh environment and exercise the external user-repository flow.

Both built wheels are installed by path, so the test cannot pick up an older release of
either from PyPI. Their one third-party dependency, `exloop`, is resolved from PyPI —
which is why the install is no longer `--no-index`: the release must prove that
`pip install newlife` brings the exploration skill along. Before an exloop release is on
PyPI, pass `--find-links <dir holding its wheel>` to run this locally.
"""

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
    parser.add_argument(
        "--find-links",
        action="append",
        default=[],
        type=pathlib.Path,
        help="extra wheel directory, for running this before a dependency reaches PyPI",
    )
    args = parser.parse_args()
    dist = args.dist.resolve()
    wheels = []
    for package in ("proofroot", "newlife"):
        matches = sorted(dist.glob(f"{package}-*.whl"))
        if len(matches) != 1:
            raise SystemExit(f"expected exactly one {package} wheel in {dist}, found {matches}")
        wheels.append(matches[0])
    find_links = [dist, *(p.resolve() for p in args.find_links)]
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
            *(arg for directory in find_links for arg in ("--find-links", directory)),
            *wheels,
        )
        _run(
            python,
            "-c",
            "import importlib.resources as r, random, newlife, proofroot, exloop; "
            "assert r.files('proofroot').joinpath('vectors/evidencecore_rng_v1.json').is_file(); "
            "assert r.files('newlife').joinpath('scaffold/prereg.sh').is_file(); "
            "assert exloop.skills_dir().joinpath('exloop/SKILL.md').is_file(); "
            "bank=proofroot.RngBank(42, ['mutation', 'selection'], "
            "stream_factory=random.Random); "
            "assert bank.rng_stream('mutation') is bank.rng_stream('MUTATION'); "
            "assert isinstance(proofroot.canonical_bytes({'answer': 42}), bytes)",
        )

        listed = _run(newlife, "skills", "path")
        if "[exloop]" not in listed or "[newlife]" not in listed:
            raise SystemExit(f"`newlife skills path` does not list both providers:\n{listed}")

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
            str(question / "origin" / "README.md"),
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

        # **Second gate, same proof.** With the goal waived the freeze must still be
        # refused: the scaffolded criteria table leaves S2's `Piloted?` cell empty and has
        # no blind row. Then walk the real path — `newlife pilot` records a run into
        # pilot/ledger.jsonl, S2 is marked seen, the missing blind row is waived on the
        # record — and the freeze goes through. A pilot that wrote into results/ would
        # break the chronology audit below, so that is asserted too.
        _run(newlife, "freeze", question, cwd=repo, expected=1)
        _run(newlife, "pilot", question, cwd=repo)
        if any((repo / question / "results").iterdir()):
            raise SystemExit("pilot wrote into results/; it must only write pilot/")
        prereg = repo / question / "prereg.md"
        row = "| **S2** | (your positive control) | | |"
        text = prereg.read_text(encoding="utf-8")
        if row not in text:
            raise SystemExit("the scaffolded prereg.md no longer has the empty S2 row this smoke test edits")
        prereg.write_text(
            text.replace(row, "| **S2** | (your positive control) | increases | seen |")
            + "\n<!--@pilot_gate: no_blind_waived ... release smoke test, no claim about the world ...-->\n",
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
