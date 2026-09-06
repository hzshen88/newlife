"""规则七的接线：prereg.md 的 @reproduction_class 一个锚决定 freeze 查不查 judgement-design.json。

此前 judgement_design 与 reproduction_class 只存在于文字里，freeze 什么都不查；模板占位符原样
留着也能冻结。现在：seeded / stochastic 必须有能重推 N 的设计文件；deterministic 或未声明按
S0 原样处理，并在冻结时说出来。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from newlife import scaffold
from newlife.gates import judgement_design


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "baseline"], check=True)
    return tmp_path


def _ready(folder: Path) -> Path:
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测规则七-->\n", encoding="utf-8"
    )
    prereg = folder / "prereg.md"
    with prereg.open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 同上-->\n")
    return prereg


def _declare(prereg: Path, body: str) -> None:
    text = prereg.read_text(encoding="utf-8")
    placeholder = "<!--@reproduction_class: deterministic | seeded | stochastic — one word, plus why-->"
    assert placeholder in text
    prereg.write_text(text.replace(placeholder, f"<!--@reproduction_class: {body}-->"), encoding="utf-8")


def test_declared_class_parser() -> None:
    assert judgement_design.declared_class("") is None
    assert judgement_design.declared_class(
        "<!--@reproduction_class: deterministic | seeded | stochastic — one word, plus why-->") is None
    assert judgement_design.declared_class("<!--@reproduction_class: Seeded — proofroot streams-->") == "seeded"
    assert judgement_design.declared_class("<!--@reproduction_class: stochastic, an LLM behind HTTP-->") == "stochastic"
    assert judgement_design.declared_class("<!--@reproduction_class: quantum-->") is None


def test_untouched_placeholder_freezes_as_deterministic_and_says_so(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-placeholder", cwd=repo)
    _ready(folder)
    assert scaffold.freeze(folder, cwd=repo) == 0
    out = capsys.readouterr().out
    assert "not stated" in out and "treated as deterministic" in out


def test_deterministic_stated(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-det", cwd=repo)
    _declare(_ready(folder), "deterministic — plain arithmetic")
    assert scaffold.freeze(folder, cwd=repo) == 0
    assert "deterministic — S0 as written" in capsys.readouterr().out


def test_stochastic_without_a_design_is_refused(tmp_path: Path, capsys) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-stoch", cwd=repo)
    _declare(_ready(folder), "stochastic — an LLM behind an HTTP call")
    with pytest.raises(SystemExit) as exc:
        scaffold.freeze(folder, cwd=repo)
    assert "not accounted for" in str(exc.value)
    assert "no judgement-design.json" in capsys.readouterr().out
    # 拒绝发生在冻结之前：prereg.md 仍未提交
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline", "--", str(folder / "prereg.md")],
                         capture_output=True, text=True).stdout
    assert log.strip() == ""
