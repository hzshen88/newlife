"""判定产物的出身：**这一次是在什么东西上跑出来的。**

## 为什么不能只记版本号

`newlife` 的版本写死在 `pyproject.toml` 里，每次构建都是 `0.1.0`——
**拿它指认不出用的是哪一版库**。用户仓库形态的第一次实测就撞在这里：
产物想记「我用的哪一版 newlife」，在技术上办不到。

`uv pip freeze` 也不行，它记的是 `newlife @ file:///…/newlife-0.1.0-py3-none-any.whl`，
**一个本地路径**——换台机器既复现不了也校验不了。

所以这里记的是**装出来的那份源码的内容摘要**：包目录下全部 `.py`，按相对路径
排序后逐个哈希。同一份 wheel 装在哪里都一样，改动一个字节就变。

**这不是给人看的字段，是给「下次还能不能对上」用的。**
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import sys
from pathlib import Path
from typing import Any


def package_digest(package: Any) -> str:
    """一个已安装包的源码内容摘要。**版本号骗得了人，这个骗不了。**"""
    root = Path(package.__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def file_digest(path: Path) -> str:
    """一个文件的 sha256。用来钉 `env.lock`。"""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(**extra: Any) -> dict[str, Any]:
    """写进产物的那一格。

    `extra` 里放这个问题特有的东西——冻结提交、求解器身份、随机种子。
    **第十七个里程碑定过规矩：求解器身份进合取**，那条规矩在这里有位置了。
    """
    import newlife

    location = Path(newlife.__file__).resolve().parent
    try:
        version = importlib.metadata.version("newlife")
    except importlib.metadata.PackageNotFoundError:
        # 从源码目录直接跑（没装成 distribution）。**不许填 "unknown" 蒙混过去**——
        # 那读起来像一个版本号。写成一句人一眼看得出不是版本的话。
        version = "UNAVAILABLE: newlife is not installed as a distribution"
    return {
        "newlife_version": version,
        "newlife_source_sha256": package_digest(newlife),
        "newlife_location": str(location),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        **extra,
    }


def frozen_at(prereg: Path) -> str:
    """从预注册自己的图章行读冻结提交。

    **不让 runner 手写这个 SHA**——手写就会漂移，而它恰恰是「产物晚于冻结」的
    全部证据：一个 SHA 在它的提交存在之前写不出来，**指名即晚于**。
    """
    for line in Path(prereg).read_text().splitlines():
        if line.startswith("**Frozen at commit:**"):
            sha = line.split(":**", 1)[1].strip().strip("`_")
            if sha and sha != "pending":
                return sha
            raise SystemExit(f"{prereg} 还没冻结——先跑 `newlife freeze`。")
    raise SystemExit(f"{prereg} 里没有 `**Frozen at commit:**` 行，不是一份预注册。")


def env_lock_lines() -> list[str]:
    """当前环境里装了什么。**只用 stdlib**，不依赖 pip 或 uv。

    `uv venv` 建的环境**没有 pip**，`pip freeze` 直接不存在——用户记录环境最自然的
    那条命令在这个工具链下是空的。而 `uv pip freeze` 把本地 wheel 记成
    `name @ file:///…`，**一个换台机器就失效的路径**。这里两个坑都绕开。
    """
    seen = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        if name:
            seen[name.lower()] = f"{name}=={dist.version}"
    return [seen[k] for k in sorted(seen)]
