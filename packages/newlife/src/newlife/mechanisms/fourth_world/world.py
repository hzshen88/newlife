"""第四世界的注册表组装：自己的 Moran builder + World 2 的 observer（原样复用）。

冻结判据见 `exloop` 预注册（freeze commit `24bb02e`）。本模块承担其中两条：

- **R1 复用范围**：只注册 World 2 的 `second-world-observer`，**不**注册它的
  `second-world-coalescent`——两者都会 `own` `TREE_PATH`，registry 会抛
  `StructuralOwnershipConflictError`（plan §1.1 的 0.2，由执行确认）。
- **R14 provenance**：`reuse-trace.json` 由本模块产出、由 verdict runner *读取*，
  runner 永不撰写它。判 goal C1 的是**对象同一性**——实际被调用的 step 函数
  `is second_world.mechanisms.observer_step`。只比 `__module__` 不够：手工改写
  `__module__` 的复制品能通过，而同一性挡得住（实测三种假复用，见 plan R1）。

`TREE_PATH` 沿用 World 2 的模块常量（R2）：第四世界的状态里因此带一个名为
`second_world` 的键。这是复用的真实代价，收尾时如实记录，不描述成干净的组合。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.core.contracts import MechanismSpec, StateClaim, StructuralRewrite
from newlife.mechanisms.fourth_world.genealogy import DrawStream, build_moran_genealogy
from newlife.mechanisms.second_world import mechanisms as w2

PROTOCOL_VERSION = "fourth-world-v1"
BUILDER_IDENTITY = "fourth-world-moran-genealogy"
OBSERVER_IDENTITY = "second-world-observer"


def build_mechanism_specs() -> list[MechanismSpec]:
    """两条注册表条目：新建的 builder，以及 World 2 的 observer spec **原样**。

    observer 的 spec 直接取自 World 2 的构造函数，不复制字段、不改写——任何编辑
    都会触发预注册的 IC-2，并使本次运行不能算作 as-declared reuse。
    """
    observer = next(
        s for s in w2.build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
    )
    builder = MechanismSpec(
        identity=BUILDER_IDENTITY,
        version=PROTOCOL_VERSION,
        plane="biological",
        biological_role="neutral Moran genealogy construction (prereg R5, R8)",
        ports=("state",),
        claims=(StateClaim(w2.TREE_PATH, "own"),),
        schedule={"stage": "coalesce"},
        rng_streams=("moran-draws",),
        allowed_effects=frozenset({"StructuralRewrite"}),
        invariants=(f"{PROTOCOL_VERSION}-moran-genealogy",),
    )
    return [builder, observer]


def genealogy_step(
    view: Mapping[tuple[str, ...], Any],
    *,
    n_sample: int,
    n_pop: int,
    draws: DrawStream,
) -> w2.MechanismStep:
    """把整棵 Moran 谱系作为一次 `StructuralRewrite` 提交。

    与 World 2 的 `coalescent_step` 同构：`view` 不被读取，树完全由 draw 流决定。
    """
    time, abv, _steps = build_moran_genealogy(n_sample, n_pop, draws)
    tree = {"time": tuple(time), "abv": tuple(abv)}
    return w2.MechanismStep((StructuralRewrite(w2.TREE_PATH, None, tree),), ())
