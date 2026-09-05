"""脚手架与出身记录 —— 用户仓库形态的那一套。

用户仓库形态第一次实测时撞到的墙，这里每一堵都有一条对应的断言。
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from newlife import provenance, scaffold

TEMPLATES = Path(scaffold.TEMPLATES)


def _waive_goal(folder: Path) -> None:
    """把 goal 阶段显式豁免掉。

    **不是绕过门，是走门自己的那条出口**——本文件测的是冻结/审计的机制，
    不是选题是否值得。豁免要留痕，正是门要求的形状。
    """
    (folder / "goal.md").write_text(
        "<!--@goal_gate: not_applicable —— 这是脚手架机制的测试，不是一个问题-->\n",
        encoding="utf-8")


def _waive_pilot(folder: Path) -> None:
    """同上，把试探门显式豁免掉——本文件测的是冻结/审计机制，不是判据有没有试探过。"""
    with (folder / "prereg.md").open("a", encoding="utf-8") as fh:
        fh.write("\n<!--@pilot_gate: not_applicable —— 这是脚手架机制的测试，不是一个问题-->\n")


def _repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    return tmp_path


def test_template_is_valid_python() -> None:
    """模板扩展名不是 `.py`，所以 lint 与 pytest 都够不着它——这里补上语法检查。"""
    src = (TEMPLATES / "verdict.py.template").read_text()
    ast.parse(src.replace("{title}", "T").replace("{slug}", "s"))


def test_digest_identifies_content_not_location() -> None:
    """**版本号永远是 0.1.0，指认不出任何东西**，所以出身靠源码内容摘要。"""
    import newlife

    assert provenance.package_digest(newlife) == provenance.package_digest(newlife)
    assert len(provenance.package_digest(newlife)) == 64


def test_digest_covers_non_python_package_assets(tmp_path: Path) -> None:
    """The freeze script, templates, and skills are part of the build identity too."""
    package = tmp_path / "fake_package"
    package.mkdir()
    init = package / "__init__.py"
    asset = package / "skill.md"
    init.write_text("\n")
    asset.write_text("before\n")
    fake = SimpleNamespace(__file__=str(init))

    before = provenance.package_digest(fake)
    asset.write_text("after\n")

    assert provenance.package_digest(fake) != before


def test_frozen_at_refuses_an_unfrozen_prereg(tmp_path: Path) -> None:
    """还没冻结就想跑判定 → 硬失败。**不许静默填一个空 SHA。**"""
    p = tmp_path / "prereg.md"
    p.write_text("# X\n\n**Frozen at commit:** _pending_\n")
    with pytest.raises(SystemExit):
        provenance.frozen_at(p)
    p.write_text("# X\n\n**Frozen at commit:** `abc1234`\n")
    assert provenance.frozen_at(p) == "abc1234"


def test_init_commits_the_scaffold_but_not_the_prereg(tmp_path: Path) -> None:
    """**墙 3**：冻结必须是 `prereg.md` 的第一次提交，而用户会习惯性地全提交。

    所以 `init` 替他把骨架提交掉，**唯独留下 `prereg.md`**——他就没有理由
    在冻结前再跑一次 `git add -A`。
    """
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-x", cwd=repo)
    assert (folder / "prereg.md").exists() and (folder / "verdict.py").exists()
    assert (folder / "goal.md").exists()
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
    assert "verdict.py" in tracked and "env.lock" in tracked
    assert "goal.md" in tracked
    assert ".gitignore" in tracked
    assert "prereg.md" not in tracked


def test_init_does_not_commit_unrelated_staged_or_gitignore_changes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / ".gitignore").write_text("base\n")
    (repo / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)

    (repo / ".gitignore").write_text("base\nuser-change\n")
    (repo / "staged.txt").write_text("user staged work\n")
    subprocess.run(["git", "-C", str(repo), "add", "staged.txt"], check=True)

    scaffold.init("2026-09-05-x", cwd=repo)

    committed = subprocess.run(
        ["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert set(committed) == {
        "questions/2026-09-05-x/env.lock",
        "questions/2026-09-05-x/goal.md",
        "questions/2026-09-05-x/origin/README.md",
        "questions/2026-09-05-x/verdict.py",
    }
    staged = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    unstaged = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert staged == ["staged.txt"]
    assert unstaged == [".gitignore"]


def test_symlinked_repo_path_freezes_and_audits(tmp_path: Path) -> None:
    real = _repo(tmp_path / "real")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    (real / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(real), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(real), "commit", "-qm", "baseline"], check=True)

    folder = scaffold.init("2026-09-05-linked", cwd=alias)
    _waive_goal(folder)
    _waive_pilot(folder)
    assert scaffold.freeze(folder, cwd=alias) == 0
    (folder / "results" / "summary.json").write_text("{}\n")
    subprocess.run(["git", "-C", str(real), "add", "questions/2026-09-05-linked/results"], check=True)
    subprocess.run(["git", "-C", str(real), "commit", "-qm", "result"], check=True)

    assert scaffold.audit(folder, cwd=alias) == 0


def test_audit_partial_is_nonzero(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "baseline.txt").write_text("base\n")
    subprocess.run(["git", "-C", str(repo), "add", "baseline.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "baseline"], check=True)
    folder = scaffold.init("2026-09-05-no-results", cwd=repo)
    _waive_goal(folder)
    _waive_pilot(folder)
    assert scaffold.freeze(folder, cwd=repo) == 0

    assert scaffold.audit(folder, cwd=repo) == 3


def test_freeze_refuses_and_says_how_to_recover(tmp_path: Path) -> None:
    """撞上墙 3 之后必须给出可执行的补救，而不只是拒绝——历史已经在那，撤不掉。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-x", cwd=repo)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "全提交了"], check=True)
    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "newlife init" in str(excinfo.value)


def test_init_refuses_outside_a_git_repo(tmp_path: Path) -> None:
    """没有 git 就没有时间证明。**这一步没有退路，不许降级继续。**"""
    with pytest.raises(SystemExit):
        scaffold.init("x", cwd=tmp_path / "nowhere")


@pytest.mark.parametrize(
    "slug",
    ["", ".", "..", ".hidden", "../outside", "nested/question", r"..\outside"],
)
def test_init_rejects_slug_that_is_not_one_safe_path_component(
    tmp_path: Path, slug: str,
) -> None:
    repo = _repo(tmp_path)

    with pytest.raises(SystemExit, match="one safe path component"):
        scaffold.init(slug, cwd=repo)

    assert not (repo / "questions").exists()


def test_init_rejects_absolute_slug_without_writing_outside_repo(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "repo")
    outside = tmp_path / "outside"

    with pytest.raises(SystemExit, match="one safe path component"):
        scaffold.init(str(outside), cwd=repo)

    assert not outside.exists()
