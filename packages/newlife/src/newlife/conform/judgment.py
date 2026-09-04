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
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

_LEDGER_ENV = "NEWLIFE_SAFETY_LINE_LEDGER"
"""进程树内「这个 runner 已经跑过了」的账本路径。

**去重前是指数的。** 每个 runner 的安全绳无条件重跑它全部的上游，而上游又各自
重跑自己的上游：f(n) = 1 + Σ_{k<n} f(k)，即 **f(n) = 2^(n-1)**。第十九个里程碑
展开成 17 个子进程（第十五个跑 8 次、第十六 4 次、第十七 2 次），实测 300.66 秒。

**去重是语义免费的**：安全绳断言的是「重跑这个 runner，它的产物逐字节不变」。
这个断言在一棵进程树里成立一次就够了，跑第二遍不增加任何信息。

**用文件而不是环境变量传递**，因为环境变量只能往下传：A 依赖 B 和 C、B 和 C 都依赖 D
时，A 无从得知 B 已经跑过 D。今天的依赖图恰好没有这种菱形，**但「里程碑排成一条线」
正是要拆掉的那个假设**——用户的问题之间是兄弟不是父子。

**先登记再执行**：万一依赖成环，也是停下而不是无限递归。
"""


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
    ledger = os.environ.get(_LEDGER_ENV)
    owner = ledger is None          # 树根负责建账本，也负责删
    if owner:
        handle, ledger = tempfile.mkstemp(prefix="newlife-safety-line-")
        os.close(handle)
    try:
        failed = _run_upstream(repo, runner_modules, Path(ledger))
    finally:
        if owner:
            Path(ledger).unlink(missing_ok=True)
    if failed is not None:
        return failed
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


def _run_upstream(
    repo: Path, runner_modules: Sequence[str], ledger: Path
) -> BaselineCheck | None:
    """跑还没跑过的上游 runner；返回 None 表示都过了。

    **跳过的那些并非没被检查**——是这棵进程树里已经有人跑过它并写过它的产物，
    下面的 `git status` 读的正是同一批文件。跳过不改变任何上报值，
    所以判定产物逐字节不变。
    """
    for module in runner_modules:
        if module in ledger.read_text().split():
            continue
        with ledger.open("a") as fh:
            fh.write(module + "\n")     # 先登记后执行：成环时停下，不递归到死
        run = subprocess.run(
            [sys.executable, "-m", module], cwd=repo, capture_output=True, text=True,
            env={**os.environ, _LEDGER_ENV: str(ledger)},
        )
        if run.returncode != 0:
            return BaselineCheck(False, module, run.returncode, "")
    return None


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
