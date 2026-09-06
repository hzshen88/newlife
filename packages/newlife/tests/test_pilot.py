"""试探门与 `newlife pilot` —— 第 ② 阶段（写判据）在冻结前的机械检查。

四份真实问题里两份 INVALID，根因都是判据写了自己没量过的量（`docs/zh/product/2026-09-04-first-user-questions.md` §4）。
newlife-prereg 的第一条规则「试探必须覆盖判据里每一个量」和第三条「留一格真盲」此前只是散文，
工具链里没有任何一步支持它。这里把它变成：`newlife pilot` 记账，`newlife freeze` 查账。

**每一条都先证明它会红，再说它有用。**
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from newlife import cli, scaffold
from newlife.gates import pilot_coverage

TEMPLATES = Path(scaffold.TEMPLATES)
S2_ROW = "| **S2** | (your positive control) | | |"


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    return tmp_path


def _waive_goal(folder: Path) -> None:
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测的是试探门，不是选题-->\n", encoding="utf-8"
    )


def _mark_s2(folder: Path, value: str, waive_blind: bool) -> None:
    """把模板里空着的 S2 标成 `value`；可选地把「没有盲格」显式豁免掉。"""
    p = folder / "prereg.md"
    text = p.read_text(encoding="utf-8")
    assert S2_ROW in text, "模板的 S2 行变了，测试夹具要跟着改"
    text = text.replace(
        S2_ROW, f"| **S2** | (your positive control) | increases | {value} |"
    )
    if waive_blind:
        text += "\n<!--@pilot_gate: no_blind_waived — 试探门的机制测试，无关于世界的主张-->\n"
    p.write_text(text, encoding="utf-8")


def test_selftest_battery_passes() -> None:
    assert pilot_coverage.main(["--selftest"]) == 0


def test_the_scaffold_prereg_is_red() -> None:
    """**最关键的一条。** 模板的 S2 行 Piloted 列是空的、没有任何一格 blind：
    脚手架自己必须过不了这道门，否则门从建文件夹那一刻起就是绿的。"""
    text = (TEMPLATES / "prereg.md").read_text(encoding="utf-8")
    rows = pilot_coverage.piloted(text)
    assert set(rows) == {"S0", "S1", "S2", "S3"}
    # 模板里那两行示例锚**不能**被解析成真豁免——第一版就栽在这里：示例被当成豁免，
    # 「没有盲格」当场绿了，端到端测试抓到的。与 goal.md 模板同一个手法：示例体里留 `<why>`。
    assert pilot_coverage.waiver(text) is None, "模板的示例锚被解析成了真豁免"
    assert pilot_coverage.check(rows, set(), pilot_coverage.waiver(text))
    problems = " ".join(pilot_coverage.check(rows, set(), None))
    assert "S2" in problems and "no unit is blind" in problems


def test_pilot_writes_to_pilot_dir_records_ledger_and_leaves_results_alone(
    tmp_path: Path,
) -> None:
    """`newlife pilot`：产物落 `pilot/<stamp>/`，`results/` 一个文件都不多；台账多一行，
    里面是这次跑出来的单元名。**未冻结的 prereg 在试探模式下不许硬失败**——试探本来就在冻结前。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-pilot", cwd=repo)

    assert cli._pilot(folder) == 0

    runs = sorted((folder / "pilot").glob("*/summary.json"))
    assert len(runs) == 1
    assert (runs[0].parent / "reproduction.json").exists()
    assert not (runs[0].parent / ".reproduction-probe.json").exists()
    assert list((folder / "results").iterdir()) == []

    lines = (folder / "pilot" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert {"S0", "S1", "S2", "S3"} <= set(entry["units"])
    assert entry["out"] == str(runs[0].relative_to(folder))

    summary = json.loads(runs[0].read_text(encoding="utf-8"))
    assert "UNFROZEN" in summary["provenance"]["preregistration_freeze"]


def test_freeze_refuses_a_seen_unit_with_no_run_then_passes_after_a_pilot(
    tmp_path: Path,
) -> None:
    """端到端：S2 标 seen 而没有试探 → 拒；跑一次 `newlife pilot` → 放行。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-e2e", cwd=repo)
    _waive_goal(folder)
    _mark_s2(folder, "seen", waive_blind=True)

    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "pilot" in str(excinfo.value)

    assert cli._pilot(folder) == 0
    assert scaffold.freeze(folder, cwd=repo) == 0


def test_freeze_refuses_when_nothing_is_blind_and_it_is_not_waived(
    tmp_path: Path, capsys
) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-noblind", cwd=repo)
    _waive_goal(folder)
    _mark_s2(folder, "seen", waive_blind=False)
    assert cli._pilot(folder) == 0

    with pytest.raises(SystemExit):
        scaffold.freeze(folder, cwd=repo)
    assert "no unit is blind" in capsys.readouterr().out


def test_freeze_reports_the_goal_gate_before_the_pilot_gate(tmp_path: Path) -> None:
    """两道门都红时先报 goal：选题不值得问，试探做得再全也没用。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-order", cwd=repo)

    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "goal_gate" in str(excinfo.value) and "pilot_gate" not in str(excinfo.value)


def test_check_reports_the_pilot_gate(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-check", cwd=repo)
    cli._check(folder)
    assert "pilot coverage" in capsys.readouterr().out


def test_init_writes_origin_readme_and_commits_it(tmp_path: Path) -> None:
    """`origin/` 是四份真实问题都没记的那件事：这个问题从哪来。脚手架必须建好这个位置。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-origin", cwd=repo)
    assert (folder / "origin" / "README.md").exists()
    tracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True
    ).stdout
    assert "origin/README.md" in tracked
