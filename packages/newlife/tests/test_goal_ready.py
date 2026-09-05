"""goal 就绪门 —— 第 ① 阶段（提出问题）在用户侧的机械检查。

洞是这么来的：`decidable-question` skill 随 wheel 发布、会让 AI 写出六个锚，
**而验锚的门不发布**。实测四份真实 `prereg.md`，锚数是 **0 · 0 · 0 · 0**。
用户拿到了写锚的东西，没拿到验锚的东西。

**这里每一条都先证明它会红，再说它有用。** 本项目已经付过两次账：
一条门在合法数据上误红、否决了科学上成功的运行；一条守卫的白名单漏掉了
它最该守的东西。所以红的一侧和绿的一侧都要有断言。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newlife import scaffold
from newlife.gates import goal_ready

TEMPLATES = Path(scaffold.TEMPLATES)


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    return tmp_path


def test_selftest_battery_passes() -> None:
    """19 条 fixture：每种遗漏都红，就绪的那份绿，脚手架红。"""
    assert goal_ready.main(["--selftest"]) == 0


def test_the_scaffold_template_is_red() -> None:
    """**最关键的一条。**

    `newlife init` 生成的 `goal.md` 必须**过不了**这道门。它要是自满足，
    门从文件夹被创建的那一刻起就是绿的，**一次都不会问用户问题**——
    恒真，正是这一族检查存在的理由所要防的那个缺陷。
    """
    assert goal_ready.check((TEMPLATES / "goal.md").read_text())


def test_a_ready_goal_is_green() -> None:
    """红的一侧证明完了还要证绿的一侧——只会红的门和只会绿的门一样没用。"""
    assert goal_ready.check(goal_ready.READY) == []


@pytest.mark.parametrize("anchor", [
    "evidence", "counterparty", "attack_layer",
    "decides", "who_changes_behavior", "size_estimate",
])
def test_each_missing_anchor_goes_red(anchor: str) -> None:
    text = goal_ready.READY.replace(f"<!--@{anchor}:", f"<!--@{anchor}_GONE:")
    assert goal_ready.check(text), f"@{anchor} 缺失时门没红"


def test_missing_goal_file_is_reported_not_skipped(tmp_path: Path, capsys) -> None:
    """**缺文件不是静默跳过。**

    「尝试失败 → 静默取默认 → 看起来一切正常」正是 `silent_degradation_scan`
    在代码侧挡的那个形状。门自己犯这个错就没资格挡别人。
    """
    assert goal_ready.main([str(tmp_path)]) == 1
    assert "does not exist" in capsys.readouterr().out


def test_anchor_body_containing_gt_does_not_parse() -> None:
    """锚体里出现 `>` 会让整条锚**静默消失**——模板里明写了这条，这里钉住它。

    起草模板时就踩到了：示例锚写成 `not_applicable — <your reason here>`，
    若它能解析，模板自己就被豁免、变绿，最关键的那条性质当场作废。
    """
    assert "goal_gate" not in goal_ready.parse("<!--@goal_gate: not_applicable — <r>-->")
    assert "goal_gate" in goal_ready.parse("<!--@goal_gate: not_applicable — r-->")


def test_init_writes_a_red_goal_and_freeze_refuses(tmp_path: Path) -> None:
    """端到端：脚手架建出来的问题，冻结**必须**被拒。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-x", cwd=repo)

    assert goal_ready.check((folder / "goal.md").read_text())
    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "goal_gate" in str(excinfo.value)


def test_freeze_proceeds_once_the_goal_is_filled_in(tmp_path: Path) -> None:
    """填完就放行。**门不能只会拒绝**——那样用户只会去绕开它。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-y", cwd=repo)
    (folder / "goal.md").write_text(goal_ready.READY, encoding="utf-8")

    assert scaffold.freeze(folder, cwd=repo) == 0


def test_freeze_reports_prereg_history_before_the_goal_gate(tmp_path: Path) -> None:
    """两条都会拒绝时，**先报不可逆的那条**。

    `prereg.md` 已有历史是已经发生、撤不掉的，它的补救（`git mv`）必须先被看到；
    goal 还没填是随时能改的。goal 门排在前面就会把那条补救遮掉。
    """
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-z", cwd=repo)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "全提交了"], check=True)

    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "git mv" in str(excinfo.value)
