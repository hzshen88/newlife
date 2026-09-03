"""第十七个里程碑的判定：接一个依赖 LP 求解器的第三方 process。

预注册 `642361c` §2：verdict = X0 ∧ X1 ∧ … ∧ X7，机械合取，`passed` 不手填。

接的是 `spatio_flux.processes.dfba.DynamicFBA`（`spatio-flux==1.4.0`）——
每个 tick 解一个线性规划。**确定性来自求解器，不来自代码**，所以 X7 把求解器
身份也列进合取：不记录它，就是把「同一个求解器的同一个选择」冒充成
「同一个科学答案」（FBA 的最优解通常不唯一）。
"""

from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path
from typing import Any

from newlife.adapters.process_bigraph import bare_control
from newlife.adapters.process_bigraph.foreign import (
    build_composite,
    resolve_foreign,
    third_party_types,
)
from newlife.adapters.process_bigraph.wrapper import BiologicalProfile, run_composite
from newlife.conform import judgment
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from newlife.mechanisms.foreign_dfba import declaration as D

REPO = Path(__file__).resolve().parents[5]
SAFETY_BASELINES = ("results/fifteenth/summary.json", "results/sixteenth/summary.json")
SAFETY_RUNNERS = (
    "newlife.conform.foreign_process_verdict",
    "newlife.conform.external_package_verdict",
)
GLUCOSE, ACETATE, BIOMASS, STEPS = 10.0, 0.0, 0.1, 4

DFBA = resolve_foreign(D.FOREIGN)


def _build(spec, bindings, *, contract: bool = True):
    profile = BiologicalProfile()
    profile.register_mechanism(spec, D.IDENTITY)
    composite = build_composite(
        D.FOREIGN,
        identity=D.IDENTITY,
        bindings=bindings,
        lowering=D.LOWERING,
        config=dict(third_party_types(D.REGISTRY)[D.MODEL_KEY]),
        state_roots={"fields": {"glucose": GLUCOSE, "acetate": ACETATE,
                                "biomass": BIOMASS}},
        in_wiring=D.IN_WIRING,
        out_wiring=D.OUT_WIRING,
        contract=contract,
        register_types=third_party_types("spatio_flux:register_types"),
    )
    return composite, profile


def _admitted_trajectory(spec, bindings, *, contract: bool = True):
    composite, profile = _build(spec, bindings, contract=contract)
    out = [bare_control.normalise_fields(composite.state["fields"])]
    for _ in range(STEPS):
        run_composite(composite, 1.0, profile)
        out.append(bare_control.normalise_fields(composite.state["fields"]))
    return out


def _rejected(spec, bindings, *, contract: bool = True) -> dict[str, Any]:
    composite, profile = _build(spec, bindings, contract=contract)
    before = bare_control.normalise_fields(composite.state["fields"])
    try:
        for _ in range(STEPS):
            run_composite(composite, 1.0, profile)
    except Exception as exc:  # noqa: BLE001 —— 判据是「有没有被拒」，类型另记
        after = bare_control.normalise_fields(composite.state["fields"])
        return {"rejected": True, "error": type(exc).__name__, "detail": str(exc)[:160],
                "from_newlife_contract": type(exc).__module__.startswith("newlife"),
                "state_unchanged": after == before}
    after = bare_control.normalise_fields(composite.state["fields"])
    return {"rejected": False, "state_unchanged": after == before}


def _x0_safety_line() -> dict[str, Any]:
    """安全绳：动接线表之后，第十五与第十六个里程碑的产物均逐字节不变。"""
    checked = judgment.check_baselines(REPO, SAFETY_RUNNERS, SAFETY_BASELINES)
    if checked.failed_runner is not None:
        return {"passed": False,
                "reason": f"{checked.failed_runner} 非零退出：{checked.returncode}"}
    return {"passed": checked.ok, "baselines": list(SAFETY_BASELINES),
            "git_status": checked.git_status}


def _x1_unmodified() -> dict[str, Any]:
    prov = judgment.foreign_provenance(DFBA)
    return {
        "passed": prov.unmodified_within("spatio_flux"),
        "class_module": prov.class_module,
        "update_defined_in": prov.update_module,
        "source_sha256": prov.source_sha256,
    }


def _f3_control_is_newlife_free() -> dict[str, Any]:
    offending = judgment.newlife_imports_in(bare_control)
    return {"passed": not offending, "offending_imports": offending}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "results/seventeenth/summary.json")
    args = ap.parse_args()

    x0 = _x0_safety_line()
    x1 = _x1_unmodified()
    f3 = _f3_control_is_newlife_free()

    bare = bare_control.dfba_trajectory(
        glucose=GLUCOSE, acetate=ACETATE, biomass=BIOMASS, steps=STEPS
    )
    admitted = _admitted_trajectory(D.SPEC, D.BINDINGS)
    x2 = json.dumps(bare) == json.dumps(admitted)

    grew = admitted[-1]["biomass"] > admitted[0]["biomass"]
    consumed = admitted[-1]["glucose"] < admitted[0]["glucose"]
    x3 = grew and consumed

    wrong_path = dataclasses.replace(D.SPEC, claims=tuple(
        dataclasses.replace(c, path=("elsewhere",)) for c in D.SPEC.claims))
    nc_a = _rejected(wrong_path, D.BINDINGS)
    no_effect = dataclasses.replace(D.SPEC, allowed_effects=frozenset({"Event"}))
    nc_b = _rejected(no_effect, D.BINDINGS)
    meta = _rejected(wrong_path, D.BINDINGS, contract=False)

    # IC-4：异常须来自 newlife 的契约层，来自 cobra/optlang 的不计入
    x4 = nc_a["rejected"] and nc_a["state_unchanged"] and nc_a.get("from_newlife_contract")
    x5 = nc_b["rejected"] and nc_b["state_unchanged"] and nc_b.get("from_newlife_contract")
    x6 = not meta["rejected"]

    solver = bare_control.solver_identity()
    x7 = bool(solver.get("optlang_interface")) and bool(solver.get("glpk_version"))

    units = [x0["passed"], x1["passed"], x2, x3, x4, x5, x6, x7]
    invalid = (not f3["passed"]) or (not x0["passed"]) or (not x6)
    h1 = (not invalid) and all(units)
    h0 = (not invalid) and not all(units)
    verdict = decide(h1=h1, h0=h0, invalid=invalid)

    summary = {
        "schema": "newlife.seventeenth.solver-backed.v1",
        "preregistration": "642361c",
        "foreign_package": "spatio-flux==1.4.0",
        "foreign": f"{DFBA.__module__}.{DFBA.__qualname__}",
        "model": D.MODEL_KEY,
        "units": {
            "X0_safety_line": x0,
            "X1_unmodified": x1,
            "X2_faithful_to_bare_pb": {"passed": x2, "bare": bare, "admitted": admitted},
            "X3_positive_control": {"passed": x3, "grew": grew, "glucose_consumed": consumed},
            "X4_wrong_path_rejected": {"passed": bool(x4), **nc_a},
            "X5_undeclared_effect_rejected": {"passed": bool(x5), **nc_b},
            "X6_meta_control_bypass_not_rejected": {"passed": x6, **meta},
            "X7_solver_identity_recorded": {"passed": x7, **solver},
        },
        "f3_control_is_newlife_free": f3,
        "what_byte_identity_buys_here": (
            "同一个求解器的同一个选择，不是同一个科学答案——FBA 的最优解通常不唯一。"
            "换求解器或换 GLPK 版本，这条轨迹没有理由仍然逐字节相同，本轮未测。"
        ),
        "normalisation_applied": "np.float64 → float，两侧同样施加（预注册 §3 F5）",
        "granularity_loss": (
            "substrates 端口按 key 逐个接线，而一条 StateDelta 只有一个路径，"
            "所以只能声明在父路径 ('fields',) 上——比第三方实际写的位置粗。"
        ),
        "what_we_wrote_on_its_behalf": {
            "claims": [[list(c.path), c.permission] for c in D.SPEC.claims],
            "allowed_effects": sorted(D.SPEC.allowed_effects),
            "bindings": [[b.port, list(b.path), b.operation] for b in D.BINDINGS],
        },
        "what_the_third_party_supplied": [
            "类型词表 spatio_flux:register_types",
            f"模型与动力学参数 MODEL_REGISTRY_DFBA[{D.MODEL_KEY!r}]（cobra 自带 textbook，不联网）",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _text = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  X0 安全绳（十五/十六产物不变）: {x0['passed']}")
    print(f"  X1 第三方未被改动:              {x1['passed']}")
    print(f"  X2 与裸 pb 逐字节一致:          {x2}")
    print(f"  X3 正控（生物量增长、葡萄糖降）: {x3}")
    print(f"  X4 负控甲 声明错路径被拒:       {bool(x4)}  {nc_a.get('error','')}")
    print(f"  X5 负控乙 未声明 Effect 被拒:   {bool(x5)}  {nc_b.get('error','')}")
    print(f"  X6 元负控（绕开契约不被拒）:    {x6}")
    print(f"  X7 求解器身份已记录:            {x7}  {solver}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
