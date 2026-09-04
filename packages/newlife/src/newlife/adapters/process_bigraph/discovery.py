"""列出装在这个环境里的、可接入的第三方积木。

用户装完 wheel 之后**无从知道手上有什么**——`newlife --help` 里没有任何发现机制，
而积木散在 `process_bigraph` 与各个可选的第三方包里。第一次真实使用时是靠现写
`pkgutil.walk_packages` 扫出来的，那段代码就是这里。

**只报告，不判断**：能不能接进来还要看它的 `update` 返回什么形状，
那由 `admit()` 在运行时硬失败。这里不假装检查过。
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterator

CANDIDATES = ("process_bigraph", "spatio_flux", "bsp")
"""扫哪些包。`bsp`（biosimulator-processes）**长期 import 不起来**——
第十五个里程碑记过，今天复查仍报同一个 `ProcessTypes` 错误。扫到就跳过，不静默假装它在。"""


def _classes(module) -> list[str]:
    from process_bigraph import Process, Step

    return sorted(
        name for name, obj in vars(module).items()
        if inspect.isclass(obj) and issubclass(obj, (Process, Step))
        and obj.__module__ == module.__name__ and not name.startswith("_")
    )


def blocks(packages: tuple[str, ...] = CANDIDATES) -> Iterator[tuple[str, str, list[str]]]:
    """产出 `(顶层包, 模块全名, 类名列表)`。**import 不起来的照实报，不跳过不掩盖。**"""
    for top in packages:
        try:
            root = importlib.import_module(top)
        except Exception as exc:                     # 装了但坏了，与没装是两件事
            yield top, f"<import 失败：{type(exc).__name__}: {str(exc)[:70]}>", []
            continue
        for info in pkgutil.walk_packages(root.__path__, f"{top}."):
            try:
                module = importlib.import_module(info.name)
            except Exception:
                continue                             # 子模块坏了是常态（可选依赖没装）
            found = _classes(module)
            if found:
                yield top, info.name, found
