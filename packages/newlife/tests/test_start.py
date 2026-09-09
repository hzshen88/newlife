"""`newlife start` —— 从 `pip install` 到「现在去跟 AI 说话」只有一条命令。

此前 README 让用户手工做五步：mkdir、git init、配身份、装 skill、init。
这里把前四步包掉，并证明每一步都真的发生了、重复跑无害、缺身份不静默。
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from newlife import cli, scaffold

EXLOOP_PRESENT = importlib.util.find_spec("exloop") is not None
COMPLETE = 0 if EXLOOP_PRESENT else 1
"""`start` 只有在探索 skill 也装上了才算完成；exloop 不在时退出码 1 并说清怎么补。
测试环境两种情况都可能出现（`--with-editable ~/Projects/exloop` 与否），期望值随之而变。"""


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

    assert cli._start(_args(root, dest)) == COMPLETE

    assert (root / ".git").is_dir()
    assert (root / "NEXT.md").exists() and (root / ".gitignore").exists()
    next_text = (root / "NEXT.md").read_text(encoding="utf-8")
    assert "idea-lab" in next_text and "inside the same exploration" in next_text
    assert "An anchor you cannot fill is the signal to drop the question" not in next_text
    sources = cli._skill_sources()
    assert len(sources) >= 2, "包里至少要有 newlife 自己的两个 skill"
    if EXLOOP_PRESENT:
        assert {"exloop", "idea-lab"} <= {
            skill.name for provider, skill in sources if provider == "exloop"
        }
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
    assert cli._start(_args(root, dest)) == COMPLETE
    assert cli._start(_args(root, dest)) == COMPLETE

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


def test_start_does_not_promise_exploration_when_exloop_is_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    """第一次评审抓到的：报成功、顺带说探索 skill 没装、然后让用户去探索。三句话互相矛盾。"""
    _git_identity(tmp_path, monkeypatch, present=True)
    monkeypatch.setattr(cli, "_skill_sources",
                        lambda: [("newlife", p) for p in sorted(cli.SKILLS.iterdir()) if (p / "SKILL.md").is_file()])
    dest = tmp_path / "skills"
    dest.mkdir()
    root = tmp_path / "my-research"

    assert cli._start(_args(root, dest)) == 1
    out = capsys.readouterr().out
    assert "pip install exloop" in out
    assert "Explore this with me" not in out
    assert (dest / "newlife-goal" / "SKILL.md").exists()          # 其余照做


def test_start_refreshes_a_stale_next_md_but_not_a_persons_own(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """升级后 NEXT.md 不刷新就一直教人跑一个已经不存在的命令（实测：check 退役后 my-research 的
    NEXT.md 还写着它）。带模板标记的文件重写；没有标记的是人的笔记，不碰。"""
    _git_identity(tmp_path, monkeypatch, present=True)
    dest = tmp_path / "skills"
    dest.mkdir()
    root = tmp_path / "my-research"
    cli._start(_args(root, dest))
    template = (cli.scaffold.TEMPLATES / "next.md").read_text(encoding="utf-8")
    marker = template.splitlines()[0]
    (root / "NEXT.md").write_text(marker + "\n\nan older version of the guidance\n", encoding="utf-8")
    cli._start(_args(root, dest))
    assert (root / "NEXT.md").read_text(encoding="utf-8") == template
    assert "refreshed" in capsys.readouterr().out
    (root / "NEXT.md").write_text("# my own notes\n", encoding="utf-8")
    cli._start(_args(root, dest))
    assert (root / "NEXT.md").read_text(encoding="utf-8") == "# my own notes\n"
