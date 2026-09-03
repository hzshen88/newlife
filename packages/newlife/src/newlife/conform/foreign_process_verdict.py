"""第十五个里程碑的判定：第三方 process 接得进来，而契约还咬得住吗。

预注册 `8d65582` §2：verdict = V1 ∧ V2 ∧ V3 ∧ V4 ∧ V5，机械合取，`passed` 不手填。
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from newlife.adapters.process_bigraph import bare_control
from newlife.adapters.process_bigraph.foreign import (
    PortBinding,
    build_composite,
    resolve_foreign,
)
from newlife.adapters.process_bigraph.wrapper import BiologicalProfile, run_composite
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from newlife.mechanisms.foreign_growth import declaration as D

REPO = Path(__file__).resolve().parents[5]
GROW = resolve_foreign(D.FOREIGN)
INITIAL_MASS = 1.0
RATE = 0.1
STEPS = 5


def _build(spec, bindings, *, contract: bool = True):
    """搭好一个 composite。`contract=False` 时**绕开契约**——元负控用。"""
    profile = BiologicalProfile()
    profile.register_mechanism(spec, D.IDENTITY)
    composite = build_composite(
        D.FOREIGN,
        identity=D.IDENTITY,
        bindings=bindings,
        lowering=D.LOWERING,
        config={"rate": RATE},
        state_roots={"mass": INITIAL_MASS},
        in_wiring=D.WIRING,
        out_wiring=D.WIRING,
        contract=contract,
    )
    return composite, profile


def _admitted_trajectory(spec, bindings, *, contract: bool = True) -> list[float]:
    """newlife 路径：第三方 `Grow` 经契约接入，跑 `STEPS` 个 tick。"""
    composite, profile = _build(spec, bindings, contract=contract)
    trajectory = [float(composite.state["mass"])]
    for _ in range(STEPS):
        run_composite(composite, 1.0, profile)
        trajectory.append(float(composite.state["mass"]))
    return trajectory


def _rejected(spec, bindings, *, contract: bool = True) -> dict[str, Any]:
    """负控。冻结判据是「抛异常**且状态不变**」——两件都查，不只查异常。"""
    composite, profile = _build(spec, bindings, contract=contract)
    before = float(composite.state["mass"])
    try:
        for _ in range(STEPS):
            run_composite(composite, 1.0, profile)
    except Exception as exc:  # noqa: BLE001 —— 判据是「有没有被拒」，类型另记
        after = float(composite.state["mass"])
        return {
            "rejected": True,
            "error": type(exc).__name__,
            "detail": str(exc)[:160],
            "state_before": before,
            "state_after": after,
            "state_unchanged": after == before,
        }
    after = float(composite.state["mass"])
    return {"rejected": False, "state_before": before, "state_after": after,
            "state_unchanged": after == before}


def _v1_unmodified() -> dict[str, Any]:
    """V1：`Grow` 源码与 `update` 均未被改动——两者都必须仍属 `process_bigraph`。"""
    source = inspect.getsource(GROW)
    module = inspect.getmodule(GROW.update)
    file = Path(inspect.getfile(GROW))
    return {
        "passed": (
            GROW.__module__.startswith("process_bigraph")
            and module is not None
            and module.__name__.startswith("process_bigraph")
            and "site-packages" in str(file)
        ),
        "class_module": GROW.__module__,
        "update_defined_in": None if module is None else module.__name__,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "installed_under_site_packages": "site-packages" in str(file),
    }


def _f3_control_is_newlife_free() -> dict[str, Any]:
    """F3 由机械检查兑现：对照组源码里不许出现 newlife 的 import。"""
    src = Path(inspect.getfile(bare_control)).read_text()
    offending = [
        line.strip()
        for line in src.splitlines()
        if line.startswith(("import ", "from ")) and "newlife" in line
    ]
    return {"passed": not offending, "offending_imports": offending}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=REPO / "results/fifteenth/summary.json")
    args = ap.parse_args()

    v1 = _v1_unmodified()
    f3 = _f3_control_is_newlife_free()

    bare = bare_control.bare_trajectory(
        initial_mass=INITIAL_MASS, rate=RATE, steps=STEPS
    )
    admitted = _admitted_trajectory(D.SPEC, D.BINDINGS)
    v2 = json.dumps(bare) == json.dumps(admitted)

    grew = admitted[-1] > admitted[0]
    # 逐 tick 迭代，**不用 `pow`**：预注册 V3 的原话是「按 mass * rate * interval
    # 增长」，那是每一步的更新式。`(1+RATE)**k` 代数上相等但浮点末位不同——
    # 用一个算不出同一个数的期望值去判「通过」，本身就是无效判据。
    expected = [INITIAL_MASS]
    for _ in range(STEPS):
        expected.append(expected[-1] + expected[-1] * RATE * 1.0)
    v3 = grew and json.dumps(admitted) == json.dumps(expected)

    # 负控甲：声明 own 在另一条路径上
    wrong_path = dataclasses.replace(
        D.SPEC, claims=(dataclasses.replace(D.SPEC.claims[0], path=("elsewhere",)),)
    )
    nc_a = _rejected(wrong_path, D.BINDINGS)

    # 负控乙：allowed_effects 不含 StateDelta
    no_effect = dataclasses.replace(D.SPEC, allowed_effects=frozenset({"Event"}))
    nc_b = _rejected(no_effect, D.BINDINGS)

    # 冻结判据是「抛异常**且状态不变**」，两个合取
    v4 = nc_a["rejected"] and nc_a["state_unchanged"]
    v5 = nc_b["rejected"] and nc_b["state_unchanged"]

    # 元负控：同一份错误声明，**绕开契约**（直接用裸 Grow）跑一次。
    # 必须**不**被拒——否则说明 V4 的红不是契约造成的，判据没有指向性。
    meta = _rejected(wrong_path, D.BINDINGS, contract=False)
    meta_ok = not meta["rejected"]

    # IC-1：裸 pb 本身跑不动。IC-2：元负控不成立 → V4/V5 的红没有指向性
    invalid = (not f3["passed"]) or (not grew) or (not meta_ok)
    h1 = (not invalid) and all([v1["passed"], v2, v3, v4, v5])
    h0 = (not invalid) and not all([v1["passed"], v2, v3, v4, v5])
    verdict = decide(h1=h1, h0=h0, invalid=invalid)

    summary = {
        "schema": "newlife.fifteenth.foreign-process.v1",
        "preregistration": "8d65582",
        "foreign": f"{GROW.__module__}.{GROW.__qualname__}",
        "units": {
            "V1_unmodified": v1,
            "V2_faithful_to_bare_pb": {"passed": v2, "bare": bare, "admitted": admitted},
            "V3_positive_control": {"passed": v3, "expected": expected},
            "V4_wrong_path_rejected": {"passed": v4, **nc_a},
            "V5_undeclared_effect_rejected": {"passed": v5, **nc_b},
        },
        "f3_control_is_newlife_free": f3,
        "meta_negative_control": {
            "question": "同一份错误声明，绕开契约跑，是否就不被拒了",
            "not_rejected_without_contract": meta_ok,
            **meta,
        },
        "what_we_wrote_on_its_behalf": {
            "claims": [[list(c.path), c.permission] for c in D.SPEC.claims],
            "allowed_effects": sorted(D.SPEC.allowed_effects),
            "bindings": [[b.port, list(b.path), b.operation] for b in D.BINDINGS],
            "lowering": {k: list(v) for k, v in D.LOWERING.items()},
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _text = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  V1 第三方未被改动:        {v1['passed']}  ({v1['update_defined_in']})")
    print(f"  V2 与裸 pb 逐字节一致:    {v2}")
    print(f"  V3 正控（按 1.1^n 增长）: {v3}")
    print(f"  V4 负控甲 声明错路径被拒: {v4}  {nc_a.get('error', '')}")
    print(f"  V5 负控乙 未声明 Effect 被拒: {v5}  {nc_b.get('error', '')}")
    print(f"  F3 对照组不含 newlife import: {f3['passed']}")
    print(f"  元负控（绕开契约则不被拒）: {meta_ok}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
