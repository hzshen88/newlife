"""`newlife skills` 与 `newlife blocks` —— 两个补「用户拿不到东西」的子命令。

装完 wheel 之后，用户**既拿不到 skill、也无从知道手上有哪些积木**。
这两条都是第一次真实使用时实测出来的洞（wheel 里 skill 文件 0 个；
`newlife --help` 里没有任何发现机制）。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from newlife import cli

SKILL_DIRS = sorted(p.name for p in cli.SKILLS.iterdir() if (p / "SKILL.md").is_file())


def _args(dest: Path, action: str = "install", force: bool = False):
    return argparse.Namespace(action=action, dest=dest, force=force)


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


def test_install_is_verbatim_and_idempotent(tmp_path: Path) -> None:
    assert cli._skills(_args(tmp_path)) == 0
    for name in SKILL_DIRS:
        assert ((tmp_path / name / "SKILL.md").read_bytes()
                == (cli.SKILLS / name / "SKILL.md").read_bytes())
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


def test_path_prints_masters_without_touching_anything(tmp_path: Path, capsys) -> None:
    assert cli._skills(_args(tmp_path, action="path")) == 0
    printed = capsys.readouterr().out.strip().splitlines()
    assert len(printed) == len(SKILL_DIRS)
    assert not list(tmp_path.iterdir())               # path 不写任何东西


def test_blocks_reports_a_broken_package_instead_of_hiding_it() -> None:
    """**装了但坏了，与没装是两件事。** `bsp` 长期 import 不起来（第十五个里程碑记过），
    扫到就照实报，不静默跳过。"""
    pytest.importorskip("process_bigraph")
    from newlife.adapters.process_bigraph import discovery

    found = list(discovery.blocks(("process_bigraph", "no_such_package_xyz")))
    broken = [m for top, m, names in found if not names]
    assert any("import 失败" in m for m in broken)
    assert any(names for _, _, names in found), "一个积木都没扫到"
