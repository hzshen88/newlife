"""判定层的共用断言。**只共用定义，不共用上报形状。**

起因：第十四到第十八个 runner 形状押韵，我一度说它们有「约 1100 行同构代码」。
**实测是 58 行 / 1113 行（5%）**——五个 runner 形状押韵，主体却是各自的科学。
所以这里**不是**一个判定 harness，只是三条断言的单一定义处：

| 断言 | 出现 | 为什么值得单一定义 |
|---|---|---|
| 基线未变 | 4/5 | 里面有第十三个里程碑的教训：**git 缺失是环境问题，必须硬失败并指名**，不能当成「基线不同」 |
| 第三方未被改动 | 3/5 | 「什么算未被改动」是判据的一部分，不该有三份定义 |
| 对照组不含 newlife | 3/5 | 同上 |

**上报形状留在各 runner 自己手里**——四个 safety line 报的键各不相同
（`baseline` / `baselines` / 外加 `baseline_commit` / 都不报）。把它们塞进一个
带选项的共用函数，正是 inner-platform effect 的第一步：函数越可配置，配置本身
越像一门编程语言。**共用件返回事实，runner 自己决定报哪些。**
"""

from __future__ import annotations

import dataclasses
import hashlib
import inspect
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


@dataclasses.dataclass(frozen=True, slots=True)
class BaselineCheck:
    """重跑上游 runner 之后，它们的产物在 git 里动没动。"""

    ok: bool
    failed_runner: str | None
    returncode: int | None
    git_status: str


def check_baselines(
    repo: Path, runner_modules: Sequence[str], baselines: Sequence[str]
) -> BaselineCheck:
    """把 `runner_modules` 各跑一遍，再问 git：`baselines` 有没有变。

    **git 不可用时硬失败并指名**（第十三个里程碑的教训）——那是环境缺失，
    不是「基线不同」。**不许静默取一个对自己有利的默认值。**
    """
    for module in runner_modules:
        run = subprocess.run(
            [sys.executable, "-m", module], cwd=repo, capture_output=True, text=True
        )
        if run.returncode != 0:
            return BaselineCheck(False, module, run.returncode, "")
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", *baselines],
            cwd=repo, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as exc:
        raise SystemExit(
            "git 不可用——安全绳的基线取不到。这是环境缺失，不是判定结果；"
            f"非 Python 依赖见 conform/dep_declaration.py。原始错误：{exc}"
        ) from exc
    dirty = status.stdout.strip()
    return BaselineCheck(dirty == "", None, None, dirty)


@dataclasses.dataclass(frozen=True, slots=True)
class Provenance:
    """一个第三方类的出身。**「什么算未被改动」的唯一定义在这里。**"""

    class_module: str
    update_module: str | None
    file: Path
    source_sha256: str
    under_site_packages: bool

    def unmodified_within(self, package: str) -> bool:
        """类与它的 `update` 都还在那个包里，且包是**装出来的**不是本地改出来的。"""
        return (
            self.class_module.startswith(package)
            and self.update_module is not None
            and self.update_module.startswith(package)
            and self.under_site_packages
        )


def foreign_provenance(cls: Any) -> Provenance:
    module = inspect.getmodule(cls.update)
    file = Path(inspect.getfile(cls))
    return Provenance(
        class_module=cls.__module__,
        update_module=None if module is None else module.__name__,
        file=file,
        source_sha256=hashlib.sha256(inspect.getsource(cls).encode()).hexdigest(),
        under_site_packages="site-packages" in str(file),
    )


def newlife_imports_in(module: Any) -> list[str]:
    """对照组里出现的 newlife import。空列表 = 这个对照组确实不经本项目。"""
    source = Path(inspect.getfile(module)).read_text()
    return [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from ")) and "newlife" in line
    ]
