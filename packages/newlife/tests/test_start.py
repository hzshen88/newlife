"""`newlife start` —— 从 `pip install` 到「现在去跟 AI 说话」只有一条命令。

此前 README 让用户手工做五步：mkdir、git init、配身份、装 skill、init。
这里把前四步包掉，并证明每一步都真的发生了、重复跑无害、缺身份不静默。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from newlife import cli, scaffold


def _git_identity(tmp_path: Path, monkeypatch, present: bool) -> None:
    """用一份临时全局 gitconfig 控制「有没有身份」，不碰机器上真正的配置。"""
    cfg = tmp_path / "gitconfig"
    cfg.write_text(
        "[user]\n\tname = t\n\temail = t@t\n" if present else "", encoding="utf-8"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(cfg))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _args(root: Path, dest: Path | None, force: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        dir=root, skills_dest=[dest] if dest else None, force=force
    )


def test_start_creates_the_repo_next_md_and_installs_every_skill(
    tmp_path: Path, monkeypatch
) -> None:
    _git_identity(tmp_path, monkeypatch, present=True)
    dest = tmp_path / "skills"
    dest.mkdir()
    root = tmp_path / "my-research"

    assert cli._start(_args(root, dest)) == 0

    assert (root / ".git").is_dir()
    assert (root / "NEXT.md").exists() and (root / ".gitignore").exists()
    sources = cli._skill_sources()
    assert len(sources) >= 2, "包里至少要有 newlife 自己的两个 skill"
    for _provider, skill in sources:
        for src in cli._skill_files(skill):
            assert (
                dest / skill.name / src.relative_to(skill)
            ).read_bytes() == src.read_bytes()


def test_start_is_idempotent_and_init_works_inside(tmp_path: Path, monkeypatch) -> None:
    """第二次跑不报错、不重复 init；接着 `newlife init` 能在里面正常建问题。"""
    _git_identity(tmp_path, monkeypatch, present=True)
    dest = tmp_path / "skills"
    dest.mkdir()
    root = tmp_path / "my-research"
    assert cli._start(_args(root, dest)) == 0
    assert cli._start(_args(root, dest)) == 0

    folder = scaffold.init("2026-09-05-first", cwd=root)
    assert (folder / "goal.md").exists() and (folder / "origin" / "README.md").exists()


def test_start_reports_a_missing_git_identity_but_still_does_the_rest(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """身份是签名，不能猜。**报出来、给命令、退出码非零**，但别的活照做——
    用户配完身份不需要再跑一次 start。"""
    _git_identity(tmp_path, monkeypatch, present=False)
    dest = tmp_path / "skills"
    dest.mkdir()
    root = tmp_path / "my-research"

    assert cli._start(_args(root, dest)) == 1
    out = capsys.readouterr().out
    assert "config user.name" in out and "config user.email" in out
    assert (root / ".git").is_dir() and (root / "NEXT.md").exists()
    assert (dest / "newlife-goal" / "SKILL.md").exists()


def test_start_with_no_ai_skills_dir_on_the_machine_says_so(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """一个 AI 配置目录都找不到不是静默成功：说清楚，给出 `skills path` 的手贴出路。"""
    _git_identity(tmp_path, monkeypatch, present=True)
    monkeypatch.setattr(cli, "KNOWN_SKILL_DIRS", (str(tmp_path / "no-such-ai"),))
    root = tmp_path / "my-research"

    assert cli._start(_args(root, None)) == 1
    assert "No AI skills directory found" in capsys.readouterr().out
