"""World 1 的 tick 循环声明。**纯数据**——算符全在冻结集内，无 lambda / 函数定义。

预注册 `10e26c7` §2.1：算符只有 `lt/le/gt/ge/eq/ne`，组合只有合取，
`observable` 只能是**已声明的观测量名**（不是任意状态路径）。

`observables` 与 `per_iteration_params` 把名字绑到宿主的属性/方法名——**是绑定点，
不是取值语言**：没有表达式，只有名字。
"""

from __future__ import annotations

from newlife.core.harness import Clause, LoopSpec, StageSpec, WorldSpec

M = "newlife.mechanisms.resource_foraging.mechanisms"

TICK_STAGES = (
    "resource-environment",
    "forager-movement",
    "forager-harvest-metabolism",
    "forager-reproduction",
    "forager-aging",
    "world-observer",
)

WORLD = WorldSpec(
    protocol_version="resource-foraging-v1",
    state_roots={},
    specs_from=f"{M}:build_mechanism_specs",
    stages=(
        StageSpec(identity="resource-environment", step=f"{M}:environment_step"),
        StageSpec(identity="forager-movement", step=f"{M}:movement_step"),
        StageSpec(identity="forager-harvest-metabolism", step=f"{M}:harvest_metabolism_step"),
        StageSpec(identity="forager-reproduction", step=f"{M}:reproduction_step"),
        StageSpec(identity="forager-aging", step=f"{M}:aging_step"),
        StageSpec(identity="world-observer", step="host:_observe"),
    ),
    loop=LoopSpec(
        stages=TICK_STAGES,
        # `while tick < config.ticks and population > 0` —— 两个子句，只有合取
        while_all=(
            Clause(observable="tick", op="lt", value="config.ticks"),
            Clause(observable="population", op="gt", value=0),
        ),
        observables={"tick": "current_tick", "population": "population"},
        per_iteration_params={
            "forager-reproduction": {"next_organism_id": "_next_organism_id"},
        },
    ),
)
