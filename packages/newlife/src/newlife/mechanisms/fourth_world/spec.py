"""第四世界的声明。**纯数据**——不含 lambda、函数定义、`eval`/`getattr` 构造。

由 `core.harness.GenericWorld` 消费。世界侧不再有引擎装配、阶段执行、阶段编排、
观测提取的代码——那四件事由通用 harness 承担（预注册 `6f2bc25` §3.1）。

保留在 `world.py` 的是 `build_mechanism_specs` 与 `genealogy_step`：第七世界判它们为
`model`，是科学本身，本就不该被生成（`proposal.md` §1.4 第三层）。

**`reuse_trace` 的字段名在这里**，因为 `results/fourth-world/summary.json` 原样嵌入
这份 trace，字段名是本世界对外的声明契约；harness 算事实，这里给名字。
"""

from __future__ import annotations

from newlife.core.harness import (
    ObservationSpec,
    ReuseTraceSpec,
    StageSpec,
    WorldSpec,
)

PROTOCOL_VERSION = "fourth-world-v1"
BUILDER_IDENTITY = "fourth-world-moran-genealogy"
OBSERVER_IDENTITY = "second-world-observer"

WORLD = WorldSpec(
    protocol_version=PROTOCOL_VERSION,
    state_roots={"second_world": {"tree": None}},
    specs_from="newlife.mechanisms.fourth_world.world:build_mechanism_specs",
    stages=(
        StageSpec(
            identity=BUILDER_IDENTITY,
            step="newlife.mechanisms.fourth_world.world:genealogy_step",
            params={"n_sample": None, "n_pop": None},
            streams={"draws": "builder"},
        ),
        StageSpec(
            identity=OBSERVER_IDENTITY,
            step="newlife.mechanisms.second_world.mechanisms:observer_step",
            params={"nsam": None, "theta": None, "replicate_index": None},
            streams={"draws": "observer"},
        ),
    ),
    observation=ObservationSpec(
        stage=OBSERVER_IDENTITY,
        record=0,
        fields=("segsites", "genotype_rows"),
        list_fields=("genotype_rows",),
    ),
    reuse_trace=ReuseTraceSpec(
        schema="newlife.fourth-world.reuse-trace.v1",
        subject_stage=OBSERVER_IDENTITY,
        declared_source="newlife.mechanisms.second_world.mechanisms",
        field_names={
            "identity": "observer_identity",
            "is_declared_object": "observer_is_world2_object",
            "module": "observer_module",
            "spec_unedited": "observer_spec_unedited",
        },
        execution_input_paths=(),
    ),
)
