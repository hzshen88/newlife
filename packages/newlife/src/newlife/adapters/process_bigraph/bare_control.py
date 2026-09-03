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


# --- 第十六个里程碑：一个真正独立的第三方包（spatio-flux 1.4.0）---


def monod_trajectory(
    *, initial_mass: float, glucose: float, steps: int
) -> list[tuple[float, dict[str, float]]]:
    """裸 pb 上跑 `spatio_flux` 的 `MonodKinetics`，返回 (mass, exchange) 轨迹。

    接线取自第三方自己的用法（`spatio_flux/processes/configs.py`）：
    `biomass` 读写都在 `mass`；`substrates` **读 `local`、写 `exchange`**。

    **缺包硬失败并指名**（预注册 `588137e` §3 F4）——不静默跳过、不降级。
    """
    try:
        import spatio_flux
        from spatio_flux.processes.monod_kinetics import MonodKinetics
    except ImportError as exc:
        raise SystemExit(
            "spatio-flux 未安装——这是环境缺失，不是判定结果。"
            "装：uv sync --package newlife --extra process-bigraph --extra spatio-flux。"
            f"原始错误：{exc}"
        ) from exc

    core = allocate_core()
    spatio_flux.register_types(core)          # 第三方交付的类型词表
    core.register_link("MonodKinetics", MonodKinetics)

    state: dict[str, Any] = {
        "mass": initial_mass,
        "local": {"glucose": glucose},
        "exchange": {"glucose": 0.0},
        "kin": {
            "_type": "process",
            "address": "local:MonodKinetics",
            "config": {},
            "inputs": {"biomass": ["mass"], "substrates": ["local"]},
            "outputs": {"biomass": ["mass"], "substrates": ["exchange"]},
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    out = [(float(composite.state["mass"]), dict(composite.state["exchange"]))]
    for _ in range(steps):
        composite.run(1.0)
        out.append((float(composite.state["mass"]), dict(composite.state["exchange"])))
    return out


# --- 第十七个里程碑：一个求解器背后的第三方 process（spatio-flux 的 dFBA）---

FIELDS = ("glucose", "acetate", "biomass")


def dfba_trajectory(
    *, glucose: float, acetate: float, biomass: float, steps: int
) -> list[dict[str, float]]:
    """裸 pb 上跑 `spatio_flux` 的 `DynamicFBA`（COBRApy + LP 求解器）。

    模型是 `ecoli core` → cobra 自带的 `textbook`，**不联网**。
    接线用第三方自己的写法（`configs.get_single_dfba_process`）：
    `substrates` 端口**按 key 逐个**接到不同的 store。

    **值归一成 Python float**：裸跑时状态里是 `np.float64`，两侧同样施加
    （预注册 `642361c` §3 F5——归一必须两侧一致，且写明施加了什么）。
    """
    try:
        import spatio_flux
        from spatio_flux.processes.dfba import MODEL_REGISTRY_DFBA, DynamicFBA
    except ImportError as exc:
        raise SystemExit(
            "spatio-flux / cobra 未安装——这是环境缺失，不是判定结果。"
            "装：uv sync --package newlife --extra process-bigraph --extra spatio-flux。"
            f"原始错误：{exc}"
        ) from exc

    core = allocate_core()
    spatio_flux.register_types(core)
    core.register_link("DynamicFBA", DynamicFBA)

    state: dict[str, Any] = {
        "fields": {"glucose": glucose, "acetate": acetate, "biomass": biomass},
        "fba": {
            "_type": "process",
            "address": "local:DynamicFBA",
            "config": dict(MODEL_REGISTRY_DFBA["ecoli core"]),
            "inputs": {
                "substrates": {"glucose": ["fields", "glucose"],
                               "acetate": ["fields", "acetate"]},
                "biomass": ["fields", "biomass"],
            },
            "outputs": {
                "substrates": {"glucose": ["fields", "glucose"],
                               "acetate": ["fields", "acetate"]},
                "biomass": ["fields", "biomass"],
            },
            "interval": 1.0,
        },
    }
    composite = Composite({"state": state}, core=core)
    out = [normalise_fields(composite.state["fields"])]
    for _ in range(steps):
        composite.run(1.0)
        out.append(normalise_fields(composite.state["fields"]))
    return out


def normalise_fields(fields: Any) -> dict[str, float]:
    """`np.float64` → `float`。**两侧同样施加**，见 `dfba_trajectory` 的说明。"""
    return {k: float(fields[k]) for k in FIELDS}


def solver_identity() -> dict[str, str]:
    """求解器身份——判定单元 X7 要的东西。

    **逐字节复现在这里买到的是「同一个求解器的同一个选择」，不是「同一个科学答案」**：
    FBA 的最优解通常不唯一（问题退化）。不记录它，就是把前者冒充成后者。
    """
    from cobra.io import load_model
    import swiglpk

    return {
        "optlang_interface": load_model("textbook").solver.interface.__name__,
        "glpk_version": str(swiglpk.glp_version()),
    }
