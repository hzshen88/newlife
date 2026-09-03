"""第十六个里程碑的判定：一个真正独立的第三方包，接得进来而契约还咬得住吗。

预注册 `588137e` §2：verdict = W0 ∧ W1 ∧ W2 ∧ W3 ∧ W4 ∧ W5 ∧ W6，
机械合取，`passed` 不手填。

接的是 `spatio_flux.processes.monod_kinetics.MonodKinetics`
（`spatio-flux==1.4.0`，**独立发行的第三方包**，走 optional extra）。
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from newlife.adapters.process_bigraph import bare_control
from newlife.adapters.process_bigraph.foreign import (
    PortBinding,
    build_composite,
    resolve_foreign,
    third_party_types,
)
from newlife.adapters.process_bigraph.wrapper import BiologicalProfile, run_composite
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from newlife.mechanisms.foreign_monod import declaration as D

REPO = Path(__file__).resolve().parents[5]
FIFTEENTH = "results/fifteenth/summary.json"
INITIAL_MASS, GLUCOSE, STEPS = 1.0, 10.0, 5

MONOD = resolve_foreign(D.FOREIGN)


def _build(spec, bindings, *, contract: bool = True):
    profile = BiologicalProfile()
    profile.register_mechanism(spec, D.IDENTITY)
    composite = build_composite(
        D.FOREIGN,
        identity=D.IDENTITY,
        bindings=bindings,
        lowering=D.LOWERING,
        config={},
        state_roots={"mass": INITIAL_MASS, "local": {"glucose": GLUCOSE},
                     "exchange": {"glucose": 0.0}},
        in_wiring=D.IN_WIRING,
        out_wiring=D.OUT_WIRING,
        contract=contract,
        register_types=third_party_types("spatio_flux:register_types"),
    )
    return composite, profile


def _snapshot(composite) -> tuple[float, dict[str, float]]:
    return float(composite.state["mass"]), dict(composite.state["exchange"])


def _admitted_trajectory(spec, bindings, *, contract: bool = True):
    composite, profile = _build(spec, bindings, contract=contract)
    out = [_snapshot(composite)]
    for _ in range(STEPS):
        run_composite(composite, 1.0, profile)
        out.append(_snapshot(composite))
    return out


def _rejected(spec, bindings, *, contract: bool = True) -> dict[str, Any]:
    """冻结判据是「抛异常**且状态不变**」——两件都查。"""
    composite, profile = _build(spec, bindings, contract=contract)
    before = _snapshot(composite)
    try:
        for _ in range(STEPS):
            run_composite(composite, 1.0, profile)
    except Exception as exc:  # noqa: BLE001 —— 判据是「有没有被拒」，类型另记
        after = _snapshot(composite)
        return {"rejected": True, "error": type(exc).__name__, "detail": str(exc)[:160],
                "state_unchanged": after == before}
    after = _snapshot(composite)
    return {"rejected": False, "state_unchanged": after == before}


def _w0_safety_line() -> dict[str, Any]:
    """安全绳：改 `admit()`/`lowering` 之后，第十五个里程碑的产物逐字节不变。

    基线不是硬编码常量，是 git 里已提交的那份产物（预注册 §3 F5）。
    """
    run = subprocess.run(
        [sys.executable, "-m", "newlife.conform.foreign_process_verdict"],
        cwd=REPO, capture_output=True, text=True,
    )
    if run.returncode != 0:
        return {"passed": False, "reason": f"第十五个里程碑 runner 非零退出：{run.returncode}"}
    try:
        status = subprocess.run(["git", "status", "--porcelain", "--", FIFTEENTH],
                                cwd=REPO, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            "git 不可用——W0 的基线取不到。这是环境缺失，不是判定结果；"
            f"非 Python 依赖见 conform/dep_declaration.py。原始错误：{exc}"
        ) from exc
    dirty = status.stdout.strip()
    return {"passed": dirty == "", "baseline": FIFTEENTH, "git_status": dirty}


def _w1_unmodified() -> dict[str, Any]:
    module = inspect.getmodule(MONOD.update)
    file = Path(inspect.getfile(MONOD))
    return {
        "passed": (
            MONOD.__module__.startswith("spatio_flux")
            and module is not None
            and module.__name__.startswith("spatio_flux")
            and "site-packages" in str(file)
        ),
        "class_module": MONOD.__module__,
        "update_defined_in": None if module is None else module.__name__,
        "source_sha256": hashlib.sha256(inspect.getsource(MONOD).encode()).hexdigest(),
        "installed_under_site_packages": "site-packages" in str(file),
    }


def _f3_control_is_newlife_free() -> dict[str, Any]:
    src = Path(inspect.getfile(bare_control)).read_text()
    offending = [line.strip() for line in src.splitlines()
                 if line.strip().startswith(("import ", "from ")) and "newlife" in line]
    return {"passed": not offending, "offending_imports": offending}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "results/sixteenth/summary.json")
    args = ap.parse_args()

    w0 = _w0_safety_line()
    w1 = _w1_unmodified()
    f3 = _f3_control_is_newlife_free()

    bare = bare_control.monod_trajectory(
        initial_mass=INITIAL_MASS, glucose=GLUCOSE, steps=STEPS
    )
    admitted = _admitted_trajectory(D.SPEC, D.BINDINGS)
    w2 = json.dumps(bare) == json.dumps(admitted)

    grew = admitted[-1][0] > admitted[0][0]
    consumed = admitted[-1][1]["glucose"] < 0.0
    w3 = grew and consumed

    # 负控甲：把两条 own 声明挪到别的路径上
    wrong_path = dataclasses.replace(D.SPEC, claims=tuple(
        dataclasses.replace(c, path=("elsewhere",)) if c.permission == "own" else c
        for c in D.SPEC.claims))
    nc_a = _rejected(wrong_path, D.BINDINGS)

    # 负控乙：allowed_effects 不含 StateDelta
    no_effect = dataclasses.replace(D.SPEC, allowed_effects=frozenset({"Event"}))
    nc_b = _rejected(no_effect, D.BINDINGS)

    w4 = nc_a["rejected"] and nc_a["state_unchanged"]
    w5 = nc_b["rejected"] and nc_b["state_unchanged"]

    # 元负控：同一份错误声明，**绕开契约**跑。必须**不**被拒。
    meta = _rejected(wrong_path, D.BINDINGS, contract=False)
    w6 = not meta["rejected"]

    units = [w0["passed"], w1["passed"], w2, w3, w4, w5, w6]
    invalid = (not f3["passed"]) or (not w0["passed"]) or (not w6)
    h1 = (not invalid) and all(units)
    h0 = (not invalid) and not all(units)
    verdict = decide(h1=h1, h0=h0, invalid=invalid)

    summary = {
        "schema": "newlife.sixteenth.external-package.v1",
        "preregistration": "588137e",
        "foreign_package": "spatio-flux==1.4.0",
        "foreign": f"{MONOD.__module__}.{MONOD.__qualname__}",
        "units": {
            "W0_safety_line_fifteenth": w0,
            "W1_unmodified": w1,
            "W2_faithful_to_bare_pb": {"passed": w2, "bare": bare, "admitted": admitted},
            "W3_positive_control": {"passed": w3, "grew": grew, "substrate_consumed": consumed},
            "W4_wrong_path_rejected": {"passed": w4, **nc_a},
            "W5_undeclared_effect_rejected": {"passed": w5, **nc_b},
            "W6_meta_control_bypass_not_rejected": {"passed": w6, **meta},
        },
        "f3_control_is_newlife_free": f3,
        "vocabulary_from_third_party": {
            "entry_point": "spatio_flux:register_types",
            "note": "类型词表由第三方交付；我们代写的只剩权限声明",
        },
        "what_we_wrote_on_its_behalf": {
            "claims": [[list(c.path), c.permission] for c in D.SPEC.claims],
            "allowed_effects": sorted(D.SPEC.allowed_effects),
            "bindings": [[b.port, list(b.path), b.operation] for b in D.BINDINGS],
            "lowering": {f"{k[0]}@{'/'.join(k[1])}": list(v) for k, v in D.LOWERING.items()},
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _text = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  W0 安全绳（第十五产物不变）:  {w0['passed']}")
    print(f"  W1 第三方未被改动:            {w1['passed']}  ({w1['update_defined_in']})")
    print(f"  W2 与裸 pb 逐字节一致:        {w2}")
    print(f"  W3 正控（增长且底物被消耗）:  {w3}")
    print(f"  W4 负控甲 声明错路径被拒:     {w4}  {nc_a.get('error','')}")
    print(f"  W5 负控乙 未声明 Effect 被拒: {w5}  {nc_b.get('error','')}")
    print(f"  W6 元负控（绕开契约不被拒）:  {w6}")
    print(f"  F3 对照组不含 newlife import: {f3['passed']}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
