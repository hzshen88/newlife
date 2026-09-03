"""**我们替 `spatio_flux.processes.dfba.DynamicFBA` 说的话。**

与第十六个里程碑（`foreign_monod/`）相比，第三方交付的部分又多了一样：
除了类型词表（`register_types`），**模型与动力学参数也是它给的**
（`MODEL_REGISTRY_DFBA["ecoli core"]` → cobra 自带的 `textbook` 模型）。

**仍由我们代写的是权限**：哪条路径归谁、允许发哪类 Effect、增量还是覆写。

---

**一处诚实的粒度损失，写在这里而不是藏起来。**

第三方把 `substrates` 端口**按 key 逐个**接到不同的 store（每个底物一条）。
而一条 `StateDelta` 只有一个路径，所以这个端口的写入只能声明在**父路径**
`("fields",)` 上——它比第三方实际写的位置**粗**：父路径也覆盖了 `biomass`。

> **端口的粒度限制了声明的粒度。** 这不是实现偷懒，是接法本身的上限。
"""

from __future__ import annotations

from newlife.adapters.process_bigraph.foreign import PortBinding
from newlife.core.contracts import MechanismSpec, StateClaim

FOREIGN = "spatio_flux.processes.dfba:DynamicFBA"
REGISTRY = "spatio_flux.processes.dfba:MODEL_REGISTRY_DFBA"
MODEL_KEY = "ecoli core"
IDENTITY = "foreign-dfba"

FIELDS_PATH = ("fields",)                  # 底物（按 key 接线，只能声明到父路径）
BIOMASS_PATH = ("fields", "biomass")

SPEC = MechanismSpec(
    identity=IDENTITY,
    version="spatio-flux-1.4.0-dfba-ecoli-core",
    plane="biological",
    biological_role="third-party dynamic FBA (spatio_flux.processes.dfba, E. coli core)",
    ports=("state",),
    claims=(
        StateClaim(FIELDS_PATH, "own"),
        StateClaim(BIOMASS_PATH, "own"),
    ),
    schedule={"stage": "fba"},
    rng_streams=(),
    allowed_effects=frozenset({"StateDelta"}),
    invariants=(),
)

BINDINGS = (
    PortBinding("substrates", FIELDS_PATH, "add"),
    PortBinding("biomass", BIOMASS_PATH, "add"),
)

LOWERING = {
    ("StateDelta", FIELDS_PATH): ("substrates", "sum-map-add"),
    ("StateDelta", BIOMASS_PATH): ("biomass", "sum-float-add"),
}

# 第三方自己的接线写法：substrates 按 key 逐个接
IN_WIRING = {
    "substrates": {"glucose": ["fields", "glucose"], "acetate": ["fields", "acetate"]},
    "biomass": ["fields", "biomass"],
}
OUT_WIRING = dict(IN_WIRING)

STATE_ROOTS = {"fields": {"glucose": 10.0, "acetate": 0.0, "biomass": 0.1}}
