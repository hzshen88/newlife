"""**我们替 `process_bigraph.processes.growth_division.Grow` 说的话。**

单独成文件，就是为了让这一点一眼可见：下面每一行都是**我们代写的断言**，
不是从第三方读出来的事实。第三方只提供 `inputs()` / `outputs()` / `update()`，
它不说自己拥有哪条路径、不说写入是增量还是覆写、不说自己只发这一类 Effect。

对照 FMI：那里接口描述由模型作者随实现一起交付。这里没有。
所以本文件填错了，**没有任何东西会发现**——预注册 `8d65582` §5 事前声明的那一点。
"""

from __future__ import annotations

from newlife.adapters.process_bigraph.foreign import PortBinding
from newlife.core.contracts import MechanismSpec, StateClaim

FOREIGN = "process_bigraph.processes.growth_division:Grow"
"""**点分路径是数据**：声明侧因此不 import vendor（import-lint 规则 2）。"""

IDENTITY = "foreign-grow"
STATE_ROOTS = {"cell": {"mass": None}}
WIRING = {"mass": ["cell", "mass"]}
MASS_PATH = ("cell", "mass")

SPEC = MechanismSpec(
    identity=IDENTITY,
    version="pb-growth-division-v1",
    plane="biological",
    biological_role="third-party mass growth (process_bigraph.processes.growth_division.Grow)",
    ports=("state",),
    claims=(StateClaim(MASS_PATH, "own"),),
    schedule={"stage": "grow"},
    rng_streams=(),
    allowed_effects=frozenset({"StateDelta"}),
    invariants=(),
)

BINDINGS = (PortBinding("mass", MASS_PATH, "add"),)
"""`add` 是我们判断出来的：`Grow.update` 返回 `mass * rate * interval`，
是**增量**。签名说不出这一点——填 `set` 会把质量覆写成增量，而结果照样跑得出来。"""

LOWERING = {"StateDelta": ("mass", "sum-float-add")}
