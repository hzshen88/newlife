"""`newlife status` —— 中断后续接靠读文件夹，不靠 AI 猜。

评审抓到的具体错误：入口 skill 的表把「有 summary.json」当成收尾，而模板的最终结论在
reproduction.json，两者之间中断的一次运行看起来像做完了。这里沿一条问题的完整生命周期逐站断言。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from newlife import cli, scaffold, status

S2_ROW = "| **S2** | (your positive control) | | |"


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


def test_not_a_question_folder(tmp_path: Path) -> None:
    report = status.inspect(tmp_path)
    assert report.stage == "not a question folder"
    assert status.main([str(tmp_path)]) == 1


def test_every_stage_along_one_question(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-walk", cwd=repo)

    r = status.inspect(folder)
    assert r.stage == "goal" and r.blockers and "newlife-goal" in r.next
    assert r.origin_files == 0
    assert "state      goal" in status.render(r)

    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 走一遍生命周期-->\n\n## 5. Closeout judgement\n\n"
        "(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)\n",
        encoding="utf-8",
    )
    assert status.inspect(folder).stage == "world & pilot"

    assert cli._pilot(folder) == 0
    r = status.inspect(folder)
    assert r.stage == "criteria"
    assert any("S2" in b for b in r.blockers)
    assert any("pilot run" in d for d in r.done)

    prereg = folder / "prereg.md"
    text = prereg.read_text(encoding="utf-8")
    assert S2_ROW in text
    prereg.write_text(
        text.replace(S2_ROW, "| **S2** | (your positive control) | increases | seen |")
        + "\n<!--@pilot_gate: no_blind_waived — 生命周期测试-->\n",
        encoding="utf-8",
    )
    r = status.inspect(folder)
    assert r.stage == "ready to freeze" and r.frozen_at is None
    assert any("freeze now" in d for d in r.decisions)

    assert scaffold.freeze(folder, cwd=repo) == 0
    r = status.inspect(folder)
    assert r.stage == "run" and r.frozen_at

    subprocess.run(
        [sys.executable, str(folder / "verdict.py")], check=False, capture_output=True
    )
    assert (folder / "results" / "summary.json").exists()
    r = status.inspect(folder)
    assert r.stage == "verdict computed, not committed" and r.verdict in {
        "H1",
        "H0",
        "INVALID",
    }
    assert r.category == status.DECISION

    rel = folder.relative_to(repo) / "results"
    subprocess.run(["git", "-C", str(repo), "add", str(rel)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "verdict"], check=True)
    r = status.inspect(folder)
    assert r.stage == "closeout"
    assert r.audit == "PASS"
    assert any("section 5" in b for b in r.blockers)  # §5 仍是占位符
    assert status.main([str(folder)]) == 0


def test_a_run_that_died_between_the_two_files_is_not_reported_as_done(
    tmp_path: Path,
) -> None:
    """**评审抓到的那个洞**：summary.json 在、reproduction.json 不在 = S0 没跑完 = 没有判定。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-interrupted", cwd=repo)
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测中断-->\n", encoding="utf-8"
    )
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 测中断-->\n")
    assert scaffold.freeze(folder, cwd=repo) == 0
    (folder / "results" / "summary.json").write_text("{}\n", encoding="utf-8")

    r = status.inspect(folder)
    assert r.stage == "run interrupted"
    assert r.verdict is None
    assert any("reproduction.json" in b for b in r.blockers)
    assert "do not commit" in r.next


def test_a_runner_of_ones_own_that_records_s0_in_summary_is_not_interrupted(
    tmp_path: Path,
) -> None:
    """**真实问题上的误报**：自定义 runner 把 S0 写进 summary.json 的 units，没有 reproduction.json，
    status 曾报 run interrupted。现在按合取读判定：S0 真、其余有假 → H0。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-own-runner", cwd=repo)
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — 测自定义 runner-->\n", encoding="utf-8"
    )
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — 同上-->\n")
    assert scaffold.freeze(folder, cwd=repo) == 0
    (folder / "results" / "summary.json").write_text(
        json.dumps({"units": {
            "S1_n_configs": {"passed": True},
            "S3_rank_correlation": {"passed": True},
            "S2_decision_equivalence": {"passed": False},
            "S0_self_proof": {"passed": True},
        }}),
        encoding="utf-8",
    )
    r = status.inspect(folder)
    assert r.stage == "verdict computed, not committed"
    assert r.verdict == "H0"

    (folder / "results" / "summary.json").write_text(
        json.dumps({"units": {"S0_self_proof": {"passed": False}, "S1": {"passed": True}}}),
        encoding="utf-8",
    )
    assert status.inspect(folder).verdict == "INVALID"

    # 真实 GRN 问题的形状：S0 是一组谓词布尔值，没有 passed —— 不猜，但也不是中断
    (folder / "results" / "summary.json").write_text(
        json.dumps({"units": {
            "S1_n_configs": {"value": 42, "passed": True},
            "S0_self_proof": {"s1_too_few": True, "all_predicates_can_go_red": True},
        }}),
        encoding="utf-8",
    )
    r = status.inspect(folder)
    assert r.stage == "verdict computed, not committed"
    assert r.verdict and "not derived" in r.verdict


def test_a_frozen_legacy_question_is_not_sent_back_to_goal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-legacy", cwd=repo)
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — legacy test-->\n", encoding="utf-8"
    )
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable — legacy test-->\n")
    assert scaffold.freeze(folder, cwd=repo) == 0
    subprocess.run([sys.executable, str(folder / "verdict.py")], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", str(folder.relative_to(repo) / "results")],
        check=True,
    )
    (folder / "goal.md").unlink()
    subprocess.run(
        ["git", "-C", str(repo), "add", "-u", str(folder.relative_to(repo) / "goal.md")],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "legacy result"], check=True)

    report = status.inspect(folder)
    assert report.stage == "complete (legacy)"
    assert report.audit == "PASS"
    assert report.category == status.DONE


def test_a_committed_unfrozen_prereg_is_never_ready_to_freeze(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-poisoned", cwd=repo)
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — history test-->\n", encoding="utf-8"
    )
    rel = folder.relative_to(repo) / "prereg.md"
    subprocess.run(["git", "-C", str(repo), "add", str(rel)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "committed too early"], check=True)

    report = status.inspect(folder)
    assert report.stage == "preregistration cannot be frozen"
    assert report.category == status.REPAIR
    assert "-v2" in report.next


def test_a_prefreeze_closeout_is_terminal_even_when_the_draft_was_committed(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-06-exploratory", cwd=repo)
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — exploratory close-->\n\n"
        "## 5. Closeout judgement (filled afterwards)\n\n"
        "not_achieved — the ruler failed its own control.\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", str(folder.relative_to(repo) / "prereg.md")],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "preserve draft"], check=True)

    report = status.inspect(folder)
    assert report.stage == "exploratory closed"
    assert report.category == status.DONE
    assert "no confirmatory conclusion" in report.trust


def test_workspace_status_shows_only_actionable_questions_and_a_done_summary(
    tmp_path: Path, monkeypatch, capsys,
) -> None:
    repo = _repo(tmp_path)
    decision = scaffold.init("2026-09-06-decision", cwd=repo)
    progress = scaffold.init("2026-09-06-progress", cwd=repo)
    (progress / "goal.md").write_text(
        "<!--@goal_gate: not_applicable — workspace test-->\n", encoding="utf-8"
    )
    done = scaffold.init("2026-09-06-done", cwd=repo)
    (done / "goal.md").write_text(
        "<!--@disposition: abandoned — scope no longer matters-->\n", encoding="utf-8"
    )
    repair = scaffold.init("2026-09-06-repair", cwd=repo)
    subprocess.run(
        ["git", "-C", str(repo), "add", str(repair.relative_to(repo) / "prereg.md")],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "poison prereg"], check=True)

    root, reports = status.inspect_workspace(repo)
    text = status.render_workspace(root, reports)
    assert decision.name in text and "YOUR DECISION" in text
    assert progress.name in text and "IN PROGRESS" in text
    assert repair.name in text and "NEEDS REPAIR" in text
    assert "DONE  1" in text
    assert done.name not in text  # completed questions are deliberately aggregated

    monkeypatch.chdir(repo)
    assert cli.main(["status"]) == 0
    assert "YOUR DECISION" in capsys.readouterr().out
