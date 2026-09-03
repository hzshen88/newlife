"""V2 的对照组：**不经 newlife**，直接在裸 process-bigraph 上跑 `Grow`。

预注册 `8d65582` §3 F3：本文件**不得 import 任何 newlife 模块**。
这条由 `conform/foreign_process_verdict.py` 读本文件源码机械检查，不靠自觉。
本文件放在 `adapters/` 下，是因为 import-lint 规则 2 把 vendor import 限定在这里——
「对照组要用裸 pb」与「vendor import 只许在 adapter 里」两条规矩的交点就是这个位置。
"""

from __future__ import annotations

from typing import Any

from process_bigraph import Composite, allocate_core
from process_bigraph.processes.growth_division import Grow


def bare_trajectory(*, initial_mass: float, rate: float, steps: int) -> list[float]:
    """裸 pb：一个 `mass` 状态 + `Grow`，跑 `steps` 个 tick，返回质量轨迹。"""
    core = _core()
    state: dict[str, Any] = {
        "cell": {"mass": initial_mass},
        "grow": {
            "_type": "process",
            "address": "local:Grow",
            "config": {"rate": rate},
            "inputs": {"mass": ["cell", "mass"]},
            "outputs": {"mass": ["cell", "mass"]},
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    trajectory = [float(composite.state["cell"]["mass"])]
    for _ in range(steps):
        composite.run(1.0)
        trajectory.append(float(composite.state["cell"]["mass"]))
    return trajectory


def _core():
    core = allocate_core()
    core.register_link("Grow", Grow)
    return core
