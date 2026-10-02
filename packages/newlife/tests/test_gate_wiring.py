"""随包发布的门 —— 每一条都必须真的**被 freeze 或 run 调用**。

`test_gates.py` 证明每条门「能抓住」（selftest 会红），但不证明「会被跑」：从
`scaffold.freeze` 删掉一行门调用，那边照样全绿。第十九个里程碑栽的正是这一跤——
单门自检全绿，聚合入口八个门全部打不开文件。这里补另一半：

1. **登记**：`newlife.gates` 下每个模块，必须恰好出现在 `WIRING`（谁调用它）或
   `EXEMPT`（为什么不在命令路径上）之一。新加一条门却忘了接线，这里直接红。
2. **行为**：把每条门的 `main` 换成「记账并放行」，真的跑一次 freeze 和 run，
   断言登记为该命令的门全部被调用——**不扫源码字样**，扫描会因错理由变绿。
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import subprocess
from pathlib import Path

import pytest

import newlife.gates
from newlife import cli, scaffold

WIRING: dict[str, str] = {
    "goal_ready": "freeze",
    "pilot_coverage": "freeze",
    # 只在 seeded / stochastic 时经 `reproduction_class_gate` 调用，所以夹具声明 stochastic
    "judgement_design": "freeze",
    "vacuous_criterion_scan": "freeze",
    "silent_degradation_scan": "freeze",
    # 对齐要等产物，所以跟着 run 而不是 freeze
    "unit_alignment": "run",
}
"""门 → 调用它的命令。"""

EXEMPT: dict[str, str] = {
    "reproduction_class": "研究用分类器：问「复现类别能否从 bundle 里判定」，由问题 "
    "2026-09-06-reproduction-class-declarability 的 verdict.py 使用；"
    "freeze 认的是 prereg.md 里声明的类别（judgement_design.declared_class），"
    "不是它的判定。",
}
"""不在任何命令路径上的模块，连同理由。例外写在这里，留在 diff 里。"""


def _modules() -> dict[str, object]:
    """按目录枚举，不是手写清单——手写清单会在加新门时一声不响地漏掉它。"""
    found = {
        info.name: importlib.import_module(f"newlife.gates.{info.name}")
        for info in pkgutil.iter_modules(newlife.gates.__path__)
    }
    assert len(found) >= 4, (
        f"只发现 {len(found)} 个门——发现逻辑坏掉的样子恰好是「全绿」"
    )
    return found


def _record(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """把每条门的 `main` 换成记账并返回 0。门的内容不是这里要测的，接线才是。"""
    calls: list[str] = []
    for name, module in _modules().items():
        monkeypatch.setattr(
            module, "main", lambda argv=None, _n=name: calls.append(_n) or 0
        )
    return calls


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


def _stochastic(folder: Path) -> None:
    """声明 stochastic，让 freeze 走到 judgement_design 那一支；设计文件只需存在（门已被替换）。"""
    prereg = folder / "prereg.md"
    text = prereg.read_text(encoding="utf-8")
    placeholder = "<!--@reproduction_class: deterministic | seeded | stochastic — one word, plus why-->"
    assert placeholder in text
    prereg.write_text(
        text.replace(placeholder, "<!--@reproduction_class: stochastic — 接线测试-->"),
        encoding="utf-8",
    )
    (folder / "judgement-design.json").write_text(json.dumps({}), encoding="utf-8")


def _expected(command: str) -> set[str]:
    return {name for name, cmd in WIRING.items() if cmd == command}


def _assert_called(command: str, calls: list[str]) -> None:
    expected = _expected(command)
    missing, extra = expected - set(calls), set(calls) - expected
    assert not missing and not extra, (
        f"`{command}` 漏调用 {sorted(missing)}，多调用 {sorted(extra)}——"
        f"改了接线就同步改 WIRING，反之亦然"
    )


def test_every_gate_is_wired_or_exempt() -> None:
    found = set(_modules())
    overlap = set(WIRING) & set(EXEMPT)
    assert not overlap, f"既登记了调用方又写了豁免：{sorted(overlap)}"
    unaccounted = found - set(WIRING) - set(EXEMPT)
    assert not unaccounted, (
        f"{sorted(unaccounted)} 在 newlife.gates 里，但既没登记调用方也没写豁免理由——"
        f"接进 freeze / run 并登记到 WIRING，或在 EXEMPT 里写明为什么不在命令路径上"
    )
    stale = (set(WIRING) | set(EXEMPT)) - found
    assert not stale, f"登记了不存在的模块：{sorted(stale)}"


def test_freeze_calls_every_gate_registered_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-10-02-wiring", cwd=repo)
    _stochastic(folder)
    calls = _record(monkeypatch)
    assert scaffold.freeze(folder, cwd=repo) == 0
    _assert_called("freeze", calls)


def test_run_calls_every_gate_registered_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-10-02-wiring", cwd=repo)
    _stochastic(folder)
    calls = _record(monkeypatch)
    assert scaffold.freeze(folder, cwd=repo) == 0
    calls.clear()
    monkeypatch.chdir(repo)
    assert cli.main(["run", str(folder)]) == 0
    _assert_called("run", calls)
