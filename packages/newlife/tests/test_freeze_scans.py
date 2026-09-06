"""`check` 退役：两道扫描进 freeze，unit alignment 进 run。

恒真判据或静默退化一旦冻结就是丢一轮，所以在不可逆那一步之前拒绝；对齐要等产物，所以跟着 run。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from newlife import cli, scaffold


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "baseline"], check=True)
    return tmp_path


def _ready(folder: Path) -> None:
    (folder / "goal.md").write_text("<!--@goal_gate: not_applicable — 测扫描-->\n", encoding="utf-8")
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 同上-->\n")


def test_freeze_refuses_a_criterion_true_by_construction(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-vacuous", cwd=repo)
    _ready(folder)
    with (folder / "verdict.py").open("a", encoding="utf-8") as fh:
        fh.write("\nREPEATED = [model(1.0) for _ in SWEEP]  # the sweep is named, the loop variable discarded\n")
    with pytest.raises(SystemExit) as exc:
        scaffold.freeze(folder, cwd=repo)
    assert "vacuous criteria" in str(exc.value)
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline", "--", str(folder / "prereg.md")],
                         capture_output=True, text=True, check=False).stdout
    assert log.strip() == ""


def test_run_reports_unit_alignment(tmp_path: Path, capsys, monkeypatch) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-aligned", cwd=repo)
    _ready(folder)
    assert scaffold.freeze(folder, cwd=repo) == 0
    monkeypatch.chdir(repo)
    assert cli.main(["run", str(folder)]) == 0
    assert "units aligned" in capsys.readouterr().out
