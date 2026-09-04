"""脚手架与出身记录 —— 用户仓库形态的那一套。

用户仓库形态第一次实测时撞到的墙，这里每一堵都有一条对应的断言。
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from newlife import provenance, scaffold

TEMPLATES = Path(scaffold.TEMPLATES)


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
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
    assert "verdict.py" in tracked and "env.lock" in tracked
    assert "prereg.md" not in tracked


def test_freeze_refuses_and_says_how_to_recover(tmp_path: Path) -> None:
    """撞上墙 3 之后必须给出可执行的补救，而不只是拒绝——历史已经在那，撤不掉。"""
    repo = _repo(tmp_path)
    folder = scaffold.init("2026-09-05-x", cwd=repo)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "全提交了"], check=True)
    with pytest.raises(SystemExit) as excinfo:
        scaffold.freeze(folder, cwd=repo)
    assert "git mv" in str(excinfo.value)


def test_init_refuses_outside_a_git_repo(tmp_path: Path) -> None:
    """没有 git 就没有时间证明。**这一步没有退路，不许降级继续。**"""
    with pytest.raises(SystemExit):
        scaffold.init("x", cwd=tmp_path / "nowhere")
