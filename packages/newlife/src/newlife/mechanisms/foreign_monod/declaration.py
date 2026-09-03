"""**我们替 `spatio_flux.processes.monod_kinetics.MonodKinetics` 说的话。**

与第十五个里程碑（`foreign_growth/declaration.py`）的关键差别：

> **词表这一半不用我们说了。** `spatio-flux` 交付 `register_types(core)`——
> `mass` / `concentration` / `reaction` 等类型由第三方自己定义。对照本体文献：
> **本体在独立开发的组件之间充当接口契约**。

**剩下的仍是我们代写的**：哪条路径归谁、允许发哪类 Effect、写入是增量还是覆写。
这三样第三方一个字都没说——它的 `outputs()` 只说类型（`float` / `map[float]`）。
所以 H1 若成立，证明的是**契约对被代写的权限声明有强制力**，不是「生态可以自动接」。
"""

from __future__ import annotations

from newlife.adapters.process_bigraph.foreign import PortBinding
from newlife.core.contracts import MechanismSpec, StateClaim

FOREIGN = "spatio_flux.processes.monod_kinetics:MonodKinetics"
IDENTITY = "foreign-monod"

MASS_PATH = ("mass",)
LOCAL_PATH = ("local",)        # 底物浓度，**只读**
EXCHANGE_PATH = ("exchange",)  # 底物交换量，**被写**

SPEC = MechanismSpec(
    identity=IDENTITY,
    version="spatio-flux-1.4.0-monod",
    plane="biological",
    biological_role="third-party Monod/MM kinetics (spatio_flux.processes.monod_kinetics)",
    ports=("state",),
    claims=(
        StateClaim(LOCAL_PATH, "read"),
        StateClaim(MASS_PATH, "own"),
        StateClaim(EXCHANGE_PATH, "own"),
    ),
    schedule={"stage": "kinetics"},
    rng_streams=(),
    allowed_effects=frozenset({"StateDelta"}),
    invariants=(),
)

BINDINGS = (
    PortBinding("biomass", MASS_PATH, "add"),
    PortBinding("substrates", EXCHANGE_PATH, "add"),
)
"""两个端口都是**增量**——第三方的 docstring 明写 "Returns deltas"。
`substrates` 的值是一个 **dict**（每个底物一项），这是第十五个里程碑没遇到的形状。"""

# 接线取自第三方自己的用法（spatio_flux/processes/configs.py）：读写路径不同
IN_WIRING = {"biomass": ["mass"], "substrates": ["local"]}
OUT_WIRING = {"biomass": ["mass"], "substrates": ["exchange"]}

STATE_ROOTS = {"mass": 1.0, "local": {"glucose": 10.0}, "exchange": {"glucose": 0.0}}

LOWERING = {
    ("StateDelta", MASS_PATH): ("biomass", "sum-float-add"),
    ("StateDelta", EXCHANGE_PATH): ("substrates", "sum-map-add"),
}
"""**按 (类别, 路径) 定位**，不能只按类别——第十六个里程碑撞出来的：
`MonodKinetics` 写两个端口，只按类别做键时两条 `StateDelta` 会全落到同一个端口上。"""
