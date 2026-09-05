"""`newlife freeze --data` —— 外部输入文件随判据一起钉住，audit 复核。

前四个真实问题读的都是自己模拟出来的数据，第五个（GRN，2026-09-05）第一次下载了外部数据集
（PRECISE-1K，127 MB，gitignore 掉了），当时 `newlife freeze` 没有任何办法把它钉住；
`prereg.sh freeze <file> [raw-data ...]` 本来就支持，只是 newlife 没把参数透传过去。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newlife import scaffold


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "baseline.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-qm", "baseline"], check=True
    )
    return tmp_path


def _ready(folder: Path) -> None:
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测的是数据钉住，不是选题-->\n",
        encoding="utf-8",
    )
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 同上-->\n")


def _commit_results(repo: Path, folder: Path) -> None:
    (folder / "results" / "summary.json").write_text("{}\n")
    rel = folder.relative_to(repo) / "results"
    subprocess.run(["git", "-C", str(repo), "add", str(rel)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "result"], check=True)


def test_data_hashes_are_frozen_into_the_registration_and_audited(
    tmp_path: Path,
) -> None:
    """数据文件**不在 git 里**（gitignore 掉的大文件正是常态），哈希照样进预注册、照样被审计。"""
    repo = _repo(tmp_path)
    (repo / ".gitignore").write_text("questions/*/data/\n")
    folder = scaffold.init("2026-09-05-with-data", cwd=repo)
    _ready(folder)
    data = folder / "data" / "compendium.csv"
    data.parent.mkdir()
    data.write_text("gene,s1,s2\na,1,2\n")

    assert scaffold.freeze(folder, cwd=repo, data=(data,)) == 0

    prereg = (folder / "prereg.md").read_text(encoding="utf-8")
    assert "## Frozen data checksums" in prereg
    assert "questions/2026-09-05-with-data/data/compendium.csv" in prereg

    _commit_results(repo, folder)
    assert scaffold.audit(folder, cwd=repo) == 0

    data.write_text("gene,s1,s2\na,1,3\n")  # 冻结后数据变了
    assert scaffold.audit(folder, cwd=repo) != 0


def test_freeze_refuses_a_data_file_that_does_not_exist(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-missing", cwd=repo)
    _ready(folder)
    with pytest.raises(SystemExit, match="no such file"):
        scaffold.freeze(folder, cwd=repo, data=(folder / "data" / "nope.csv",))
    assert "Frozen data checksums" not in (folder / "prereg.md").read_text(
        encoding="utf-8"
    )


def test_freeze_refuses_a_data_file_outside_the_repository(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    outside = tmp_path / "elsewhere.csv"
    outside.write_text("x\n")
    folder = scaffold.init("2026-09-05-outside", cwd=repo)
    _ready(folder)
    with pytest.raises(SystemExit, match="outside the repository"):
        scaffold.freeze(folder, cwd=repo, data=(outside,))
