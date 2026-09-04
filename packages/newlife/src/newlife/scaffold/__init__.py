"""一个问题一个文件夹：建骨架、冻结判据、审计。

## 布局

    my-research/                     ← 一次 git init，一个仓库
    ├── .gitignore
    └── questions/
        ├── 2026-09-05-<slug>/
        │   ├── prereg.md            ← 判据，冻结在这里
        │   ├── verdict.py           ← 判定 runner
        │   ├── env.lock             ← 跑这次时装了什么
        │   └── results/
        └── 2026-09-12-<另一个>/      ← **兄弟，不是父子**

**预注册与产物必须同仓**：`prereg.sh` 的 chronology 靠 git 祖先关系证明
「产物晚于冻结」，而祖先关系**只存在于一个仓库之内**。本项目自己踩过这个坑——
预注册在一个仓库、产物在另一个，22 份预注册的 chronology **一次都没建立过**，
而旧版脚本在检查了零个产物之后照样打印「predictions pre-date outputs」。

**但不是一个问题一个仓库**：那意味着 N 次 `git init`、N 个远端、没法共享辅助代码。
一个仓库多个问题文件夹同样有共同祖先，实测成立。

## 为什么 `init` 会自己提交

**冻结必须是 `prereg.md` 的第一次提交。** 而用户最自然的动作是「建好文件夹就
`git add -A && git commit`」——这一下就把冻结能力锁死了，且不可撤销（历史已经在那）。
所以 `init` **替用户把骨架提交掉，唯独留下 `prereg.md` 不提交**：
这样用户没有理由在冻结前再跑一次 `git add -A`。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from newlife import provenance

TEMPLATES = Path(__file__).resolve().parent / "templates"
PREREG_SH = Path(__file__).resolve().parent / "prereg.sh"
SCAFFOLD_FILES = ("verdict.py", "env.lock")     # **不含 prereg.md**，见模块文档


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=check)


def repo_root(start: Path) -> Path:
    """所在的 git 仓库根。**不在仓库里就硬失败**——没有 git 就没有时间证明。"""
    try:
        out = _git(start, "rev-parse", "--show-toplevel")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SystemExit(
            f"{start} 不在一个 git 仓库里。判定的可信度全部来自 git 历史"
            f"（冻结提交即时间证明），所以这一步没有退路：先 `git init`。\n原始错误：{exc}"
        ) from exc
    return Path(out.stdout.strip())


def init(slug: str, *, cwd: Path, commit: bool = True) -> Path:
    """建一个问题文件夹，并把骨架提交掉（`prereg.md` 除外）。"""
    root = repo_root(cwd)
    folder = root / "questions" / slug
    if folder.exists():
        raise SystemExit(f"{folder} 已存在——换一个 slug，不要覆盖已有的问题。")
    (folder / "results").mkdir(parents=True)

    title = slug.split("-", 3)[-1].replace("-", " ") or slug
    (folder / "prereg.md").write_text(
        (TEMPLATES / "prereg.md").read_text().format(title=title), encoding="utf-8")
    (folder / "verdict.py").write_text(
        (TEMPLATES / "verdict.py.template").read_text()
        .replace("{title}", title).replace("{slug}", slug), encoding="utf-8")
    (folder / "env.lock").write_text(
        "\n".join(provenance.env_lock_lines()) + "\n", encoding="utf-8")

    gitignore = root / ".gitignore"
    if not gitignore.exists():
        shutil.copyfile(TEMPLATES / "gitignore", gitignore)

    rel = folder.relative_to(root)
    if commit:
        paths = [str(rel / name) for name in SCAFFOLD_FILES]
        if gitignore.exists():
            paths.append(".gitignore")
        _git(root, "add", *paths)
        _git(root, "commit", "-m", f"question({slug}): 骨架（prereg 未提交，待冻结）")
    return folder


def freeze(folder: Path, *, cwd: Path) -> int:
    """冻结这个问题的判据。**冻结必须是 `prereg.md` 的第一次提交。**"""
    root = repo_root(cwd)
    prereg = (folder / "prereg.md").resolve()
    rel = prereg.relative_to(root)
    history = _git(root, "log", "--format=%h", "--", str(rel), check=False).stdout.strip()
    if history:
        raise SystemExit(
            f"{rel} 已经有 git 历史，冻结必须是它的第一次提交——"
            f"否则那个提交证明不了「判据早于结果」。\n"
            f"**补救**：`git mv {rel} {rel.with_name('prereg-v2.md')}` 之后冻结新文件"
            f"（旧的留在历史里，不要删——它是这次改动本身的记录）。"
        )
    return _run_prereg(root, "freeze", str(rel))


def audit(folder: Path, *, cwd: Path) -> int:
    """审计：判据没被改过，且产物晚于冻结。**范围自动划到这个问题自己。**"""
    root = repo_root(cwd)
    rel = (folder / "prereg.md").resolve().relative_to(root)
    return _run_prereg(root, "audit", "--results", str(rel.parent / "results"), str(rel))


def _run_prereg(root: Path, *args: str) -> int:
    proc = subprocess.run(["sh", str(PREREG_SH), *args], cwd=root)
    return proc.returncode
