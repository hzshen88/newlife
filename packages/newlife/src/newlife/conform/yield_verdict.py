"""第十九个里程碑：产率是输入还是结果。

预注册 `0e04160` §2：verdict = Z0 ∧ … ∧ Z6，机械合取，`passed` 不手填。

两个第三方积木（`MonodKinetics` / `DynamicFBA`）**输入签名逐字相同**，在同一端口
可互换；而 dFBA 内部用的正是 Monod 摄取律。**共用同一条摄取律，差别只在摄取之后。**

**这同时是产品形态的第一次端到端检验**：一个只用现成积木的新问题值多少行新代码。
产物里的 `implementation_lines` 是这个指标，不是附注（预注册 §3 F6）。
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path
from typing import Any

from newlife.adapters.process_bigraph.foreign import (
    PortBinding, build_composite, resolve_foreign, third_party_types,
)
from newlife.adapters.process_bigraph.wrapper import BiologicalProfile, run_composite
from newlife.conform import judgment
from newlife.core.contracts import MechanismSpec, StateClaim
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code

REPO = Path(__file__).resolve().parents[5]
BASELINES = tuple(f"results/{m}/summary.json" for m in
                  ("fourteenth", "fifteenth", "sixteenth", "seventeenth", "eighteenth"))
RUNNERS = tuple(f"newlife.conform.{m}_verdict" for m in
                ("cross_runtime", "foreign_process", "external_package",
                 "solver_backed", "derive_authority"))

MONOD = "spatio_flux.processes.monod_kinetics:MonodKinetics"
DFBA = "spatio_flux.processes.dfba:DynamicFBA"
REGISTRY = "spatio_flux.processes.dfba:MODEL_REGISTRY_DFBA"
MASS, LOCAL, EXCHANGE = ("mass",), ("local",), ("exchange",)
GLUCOSE, BIOMASS0, STEPS = 10.0, 0.1, 10
O2_SWEEP = (-1.0, -2.0, -4.0, -8.0, -20.0)

# 两个积木的输出签名同形（biomass 是标量、substrates 是 map），所以**一份接线吃两个**。
# 这正是「可互换」在代码上的样子。
BINDINGS = (PortBinding("biomass", MASS, "add"), PortBinding("substrates", EXCHANGE, "add"))
LOWERING = {("StateDelta", MASS): ("biomass", "sum-float-add"),
            ("StateDelta", EXCHANGE): ("substrates", "sum-map-add")}
IN_WIRING = {"biomass": ["mass"], "substrates": ["local"]}
OUT_WIRING = {"biomass": ["mass"], "substrates": ["exchange"]}


def _spec(identity: str, role: str) -> MechanismSpec:
    return MechanismSpec(
        identity=identity, version="spatio-flux-1.4.0", plane="biological",
        biological_role=role, ports=("state",),
        claims=(StateClaim(LOCAL, "read"), StateClaim(MASS, "own"),
                StateClaim(EXCHANGE, "own")),
        schedule={"stage": "growth"}, rng_streams=(),
        allowed_effects=frozenset({"StateDelta"}), invariants=(),
    )


def _run(foreign: str, identity: str, config: dict) -> dict[str, float]:
    """跑一个积木，返回表观产率、乙酸产出、单位生物量摄取速率。"""
    profile = BiologicalProfile()
    profile.register_mechanism(_spec(identity, foreign), identity)
    composite = build_composite(
        foreign, identity=identity, bindings=BINDINGS, lowering=LOWERING, config=config,
        state_roots={"local": {"glucose": GLUCOSE, "acetate": 0.0},
                     "exchange": {"glucose": 0.0, "acetate": 0.0}, "mass": BIOMASS0},
        in_wiring=IN_WIRING, out_wiring=OUT_WIRING, contract=True,
        register_types=third_party_types("spatio_flux:register_types"),
    )
    masses = [float(composite.state["mass"])]
    for _ in range(STEPS):
        run_composite(composite, 1.0, profile)
        masses.append(float(composite.state["mass"]))
    used = -float(composite.state["exchange"]["glucose"])       # np.float64 → float，两侧同施
    acetate = float(composite.state["exchange"]["acetate"])
    grown = masses[-1] - masses[0]
    mean_mass = sum(masses[:-1]) / STEPS
    return {"yield": grown / used if used else 0.0, "acetate": acetate,
            "uptake_per_biomass": used / STEPS / mean_mass if mean_mass else 0.0}


def _dfba_config(o2: float) -> dict:
    cfg = copy.deepcopy(dict(third_party_types(REGISTRY)["ecoli core"]))
    cfg["bounds"] = {**dict(cfg["bounds"]), "EX_o2_e": {"lower": o2, "upper": None}}
    return cfg


def _monod_config(yield_: float = 1.0) -> dict:
    """`km`/`vmax` **从 dFBA 自己的 `kinetic_params` 读出**，不手写（预注册 F2）。"""
    km, vmax = third_party_types(REGISTRY)["ecoli core"]["kinetic_params"]["glucose"]
    return {"reactions": {"uptake": {"reactant": "glucose", "product": "mass",
                                     "km": float(km), "vmax": float(vmax),
                                     "yield": yield_}}}


def _strictly_opposed(a: list[float], b: list[float]) -> bool:
    """两列在扫描上严格反向：一列不增时另一列不减，且至少各动一次。"""
    da = [y - x for x, y in zip(a, a[1:])]
    db = [y - x for x, y in zip(b, b[1:])]
    return (all(p <= 0 for p in da) and all(q >= 0 for q in db)
            and any(p < 0 for p in da) and any(q > 0 for q in db))


PINNED_HASH_SEED = "0"


def _pin_hash_seed() -> None:
    """哈希种子不定则**重新以固定种子启动自己**，并说出来。

    **实测**：`PYTHONHASHSEED` 变了，Monod 的表观产率末位就变
    （0.9999286994899365 ↔ …363）。第三方代码路径上有 `set` 迭代，
    顺序随种子变，浮点求和顺序随之变。

    这与第十七个里程碑记的是同一形状：**逐字节复现买到的是「同一个种子的同一个
    求和顺序」**，不是「同一个数学答案」。判据本身对这个抖动不敏感（容差 1e-3），
    但**产物要逐字节稳定，就必须把种子钉住并记录**。

    **不静默**：重启会打印出来；种子写进产物。
    """
    if os.environ.get("PYTHONHASHSEED") == PINNED_HASH_SEED:
        return
    print(f"  [重启] PYTHONHASHSEED 未固定为 {PINNED_HASH_SEED}——"
          f"第三方积木的浮点求和顺序随它变，用固定种子重新启动自己")
    sys.stdout.flush()   # execve 直接替换进程，不 flush 这行提示就没了——那就成静默了
    os.execve(sys.executable,
              [sys.executable, "-m", "newlife.conform.yield_verdict", *sys.argv[1:]],
              {**os.environ, "PYTHONHASHSEED": PINNED_HASH_SEED})


def main() -> int:
    _pin_hash_seed()
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "results/nineteenth/summary.json")
    args = ap.parse_args()

    checked = judgment.check_baselines(REPO, RUNNERS, BASELINES)
    z0 = {"passed": checked.ok, "failed_runner": checked.failed_runner,
          "git_status": checked.git_status}
    z1 = {name: judgment.foreign_provenance(resolve_foreign(d)).unmodified_within("spatio_flux")
          for name, d in (("MonodKinetics", MONOD), ("DynamicFBA", DFBA))}

    km, vmax = third_party_types(REGISTRY)["ecoli core"]["kinetic_params"]["glucose"]
    monod_cfg = _monod_config()
    used = monod_cfg["reactions"]["uptake"]
    z2 = {"passed": used["km"] == float(km) and used["vmax"] == float(vmax),
          "from_third_party": [float(km), float(vmax)],
          "used_by_monod": [used["km"], used["vmax"]]}

    dfba = [_run(DFBA, "foreign-dfba", _dfba_config(o2)) for o2 in O2_SWEEP]
    monod = [_run(MONOD, "foreign-monod", monod_cfg) for _ in O2_SWEEP]
    # 负控：把 Monod 的 yield 设成 dFBA 在**某一点**上的产率，重扫
    pinned = _monod_config(dfba[0]["yield"])
    monod_pinned = [_run(MONOD, "foreign-monod", pinned) for _ in O2_SWEEP]

    z3 = _strictly_opposed([r["acetate"] for r in dfba], [r["yield"] for r in dfba])
    z4 = all(abs(r["yield"] - 1.0) < 1e-3 for r in monod)
    z5 = (max(r["yield"] for r in monod_pinned) - min(r["yield"] for r in monod_pinned)) < 1e-9
    z6 = any(r["acetate"] == 0.0 for r in dfba) and any(r["acetate"] > 0.0 for r in dfba)

    units = [z0["passed"], all(z1.values()), z2["passed"], z3, z4, z5, z6]
    invalid = (not z0["passed"]) or (not z2["passed"]) or (not z4) or (not z6)
    verdict = decide(h1=(not invalid) and all(units),
                     h0=(not invalid) and not all(units), invalid=invalid)

    summary = {
        "schema": "newlife.nineteenth.yield-input-or-outcome.v1",
        "preregistration": "0e04160",
        "o2_sweep": list(O2_SWEEP),
        "units": {
            "Z0_safety_line": z0, "Z1_unmodified": z1, "Z2_uptake_law_aligned": z2,
            "Z3_acetate_opposes_yield": {"passed": z3},
            "Z4_monod_yield_is_its_declared_constant": {"passed": z4},
            "Z5_pinning_one_point_does_not_help": {"passed": z5,
                "pinned_to": dfba[0]["yield"]},
            "Z6_sweep_reaches_zero_acetate": {"passed": z6},
        },
        "dfba": dfba, "monod": monod, "monod_yield_pinned": monod_pinned,
        "normalisation_applied": "np.float64 → float，两侧同样施加（预注册 §3 F4）",
        "scope_caveat": (
            "只证「固定形式的 Monod（单反应、常数产率）覆盖不了这个依赖」，"
            "不证「任何唯象模型都覆盖不了」——给 Monod 加一条 glucose→acetate 反应"
            "就能表示乙酸，但那是换一个模型，不是同一个模型的参数化。本轮明确不加。"
        ),
        "hash_seed_pinned": PINNED_HASH_SEED,
        "why_hash_seed_matters": (
            "实测：PYTHONHASHSEED 变了，Monod 的表观产率末位就变（…365 ↔ …363）——"
            "第三方代码路径上有 set 迭代，浮点求和顺序随之变。逐字节复现在这里买到的是"
            "「同一个种子的同一个求和顺序」，不是「同一个数学答案」。判据本身对此不敏感"
            "（容差 1e-3），但产物要逐字节稳定就必须钉住并记录它。"
        ),
        "implementation_lines": len(Path(__file__).read_text().splitlines()),
        "reused_without_new_code": [
            "adapters/process_bigraph/foreign.py（接入）",
            "conform/judgment.py（安全绳与出身断言）",
            "spatio_flux 的两个 Process 与它自己的 kinetic_params",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _ = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  Z0 安全绳（五份产物不变）: {z0['passed']}")
    print(f"  Z1 两个第三方未被改动:     {all(z1.values())}")
    print(f"  Z2 摄取律对齐（km,vmax）:  {z2['passed']}  {z2['from_third_party']}")
    print(f"  Z3 乙酸与产率反向:         {z3}")
    print(f"  Z4 Monod 产率恒等于声明:   {z4}")
    print(f"  Z5 负控（钉一点仍不动）:   {z5}")
    print(f"  Z6 扫描覆盖到乙酸归零:     {z6}")
    print(f"\n  {'O2':>6} {'dFBA产率':>10} {'乙酸':>9} {'Monod产率':>10}")
    for o2, d, m in zip(O2_SWEEP, dfba, monod):
        print(f"  {o2:6.0f} {d['yield']:10.5f} {d['acetate']:9.5f} {m['yield']:10.5f}")
    print(f"\n  实现行数: {summary['implementation_lines']}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
