"""`newlife skills` 与 `newlife blocks` —— 两个补「用户拿不到东西」的子命令。

装完 wheel 之后，用户**既拿不到 skill、也无从知道手上有哪些积木**。
这两条都是第一次真实使用时实测出来的洞（wheel 里 skill 文件 0 个；
`newlife --help` 里没有任何发现机制）。
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from newlife import cli

SKILL_DIRS = sorted(p.name for p in cli.SKILLS.iterdir() if (p / "SKILL.md").is_file())


def _args(dest: Path, action: str = "install", force: bool = False):
    return argparse.Namespace(action=action, dest=[dest], force=force)


def test_every_skill_declares_a_name_that_matches_its_directory() -> None:
    """**母本与部署副本是同一份文件**，所以 frontmatter 必须写在包里这一份上。

    从前母本在 `docs/` 而部署副本另加一段 frontmatter——**两份会漂移**，
    正是这个项目反复付过学费的形状。
    """
    assert SKILL_DIRS, "包里一个 skill 都没有"
    for name in SKILL_DIRS:
        text = (cli.SKILLS / name / "SKILL.md").read_text()
        assert text.startswith("---\n"), f"{name} 缺 frontmatter"
        head = text.split("---", 2)[1]
        assert f"name: {name}" in head, f"{name} 的 frontmatter 名字对不上目录"
        assert "description:" in head, f"{name} 缺 description"


def test_newlife_owns_one_complete_four_skill_flow() -> None:
    assert SKILL_DIRS == ["newlife", "newlife-execute", "newlife-goal", "newlife-prereg"]
    router = (cli.SKILLS / "newlife" / "SKILL.md").read_text()
    execute = (cli.SKILLS / "newlife-execute" / "SKILL.md").read_text()
    prereg = (cli.SKILLS / "newlife-prereg" / "SKILL.md").read_text()
    normalized_router = " ".join(router.split())
    normalized_execute = " ".join(execute.split())
    assert "ask before freezing" in normalized_router
    assert "ask before committing `results/`" in normalized_router
    assert "No reply is not approval" in normalized_execute
    assert "Ask the person before running it" in prereg
    assert "newlife check" not in normalized_execute
    assert "science-superpowers:" not in "\n".join(
        p.read_text(encoding="utf-8") for p in cli.SKILLS.rglob("*.md")
    )


def test_local_markdown_references_resolve_after_install(tmp_path: Path) -> None:
    assert cli._skills(_args(tmp_path)) == 0
    missing: list[str] = []
    for document in tmp_path.rglob("*.md"):
        for target in re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]*)?\)", document.read_text()):
            if "://" in target:
                continue
            if not (document.parent / target).resolve().exists():
                missing.append(f"{document.relative_to(tmp_path)} -> {target}")
    assert missing == []


def test_install_is_verbatim_and_idempotent(tmp_path: Path) -> None:
    """**整个目录，不只 SKILL.md。** 第一版只拷一个文件，装不了带 references/ 与 scripts/
    的探索 skill；这里按 `_skill_sources()` 逐文件比对，exloop 装了就一并覆盖到。"""
    assert cli._skills(_args(tmp_path)) == 0
    sources = cli._skill_sources()
    assert {name for _, p in sources for name in [p.name]} >= set(SKILL_DIRS)
    for _provider, skill in sources:
        files = cli._skill_files(skill)
        assert files, f"{skill.name} 一个文件都没有"
        for src in files:
            assert (tmp_path / skill.name / src.relative_to(skill)).read_bytes() == src.read_bytes()
    assert cli._skills(_args(tmp_path)) == 0          # 再装一次仍然干净


def test_install_refuses_to_clobber_an_edited_skill(tmp_path: Path) -> None:
    """**不覆盖用户改过的东西。** 静默覆盖等于把他的修改吃掉而无人知晓。"""
    cli._skills(_args(tmp_path))
    edited = tmp_path / SKILL_DIRS[0] / "SKILL.md"
    edited.write_text(edited.read_text() + "\n# 我自己改的\n")
    assert cli._skills(_args(tmp_path)) == 1          # 非零退出：有东西没装上
    assert "我自己改的" in edited.read_text()
    assert cli._skills(_args(tmp_path, force=True)) == 0
    assert "我自己改的" not in edited.read_text()


def test_ordinary_install_does_not_retire_unrelated_or_stale_entries(tmp_path: Path) -> None:
    stale = tmp_path / "surveying-prior-work" / "SKILL.md"
    stale.parent.mkdir()
    stale.write_text("stale entry remains until an explicit migration\n")
    assert cli._skills(_args(tmp_path)) == 0
    assert stale.read_text() == "stale entry remains until an explicit migration\n"


def test_path_prints_masters_without_touching_anything(tmp_path: Path, capsys) -> None:
    assert cli._skills(_args(tmp_path, action="path")) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == len(cli._skill_sources())
    assert all("SKILL.md" in line and line.rstrip().endswith("]") for line in printed)
    assert not list(tmp_path.iterdir())               # path 不写任何东西


def test_install_with_no_dest_and_no_ai_dir_is_not_a_silent_success(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "KNOWN_SKILL_DIRS", (str(tmp_path / "no-such-ai"),))
    assert cli._skills(argparse.Namespace(action="install", dest=None, force=False)) == 1
    assert "No AI skills directory found" in capsys.readouterr().out


def test_blocks_reports_a_broken_package_instead_of_hiding_it() -> None:
    """**装了但坏了，与没装是两件事。** `bsp` 长期 import 不起来（第十五个里程碑记过），
    扫到就照实报，不静默跳过。"""
    pytest.importorskip("process_bigraph")
    from newlife.adapters.process_bigraph import discovery

    found = list(discovery.blocks(("process_bigraph", "no_such_package_xyz")))
    broken = [m for top, m, names in found if not names]
    assert any("import failed" in m for m in broken)
    assert any(names for _, _, names in found), "一个积木都没扫到"
