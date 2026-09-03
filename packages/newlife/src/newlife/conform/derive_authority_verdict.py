"""第十八个里程碑的判定：权限声明能不能从第三方已交付的东西机械推导出来。

预注册 `f948447` §2：verdict = Y0 ∧ Y1 ∧ … ∧ Y6，机械合取，`passed` 不手填。
"""

from __future__ import annotations

import argparse
import inspect
import subprocess
import sys
from pathlib import Path
from typing import Any

from newlife.adapters.process_bigraph import derive
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from newlife.mechanisms.foreign_dfba import declaration as DFBA
from newlife.mechanisms.foreign_growth import declaration as GROW
from newlife.mechanisms.foreign_monod import declaration as MONOD

REPO = Path(__file__).resolve().parents[5]
BASELINES = ("results/fifteenth/summary.json", "results/sixteenth/summary.json",
             "results/seventeenth/summary.json")
RUNNERS = ("newlife.conform.foreign_process_verdict",
           "newlife.conform.external_package_verdict",
           "newlife.conform.solver_backed_verdict")

# 三个 provider：第三方自己的接线生成器 + 它在输出端口上声明的类型
PROVIDERS = {
    "Grow": {
        "declaration": GROW,
        "generator": "process_bigraph.processes.growth_division:grow_divide_agent",
        "generator_kwargs": {"path": ["a"]},
        "address_suffix": ":Grow",
    },
    "MonodKinetics": {
        "declaration": MONOD,
        "generator": "spatio_flux.processes.configs:get_kinetic_particle_composition",
        "generator_kwargs": {"core": "<core>"},
        "address_suffix": ":MonodKinetics",
    },
    "DynamicFBA": {
        "declaration": DFBA,
        "generator": "spatio_flux.processes.configs:get_single_dfba_process",
        "generator_kwargs": {"path": ["fields"], "biomass_id": "biomass"},
        "address_suffix": ":DynamicFBA",
    },
}


def _resolve(dotted: str) -> Any:
    import importlib  # noqa: PLC0415

    module, attr = dotted.split(":")
    return getattr(importlib.import_module(module), attr)


def _core() -> Any:
    return derive.allocate_probe_core("spatio_flux:register_types")


def _y0_safety_line() -> dict[str, Any]:
    for module in RUNNERS:
        run = subprocess.run([sys.executable, "-m", module], cwd=REPO,
                             capture_output=True, text=True)
        if run.returncode != 0:
            return {"passed": False, "reason": f"{module} 非零退出：{run.returncode}"}
    try:
        status = subprocess.run(["git", "status", "--porcelain", "--", *BASELINES],
                                cwd=REPO, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise SystemExit(
            "git 不可用——Y0 的基线取不到。这是环境缺失，不是判定结果；"
            f"非 Python 依赖见 conform/dep_declaration.py。原始错误：{exc}"
        ) from exc
    return {"passed": status.stdout.strip() == "", "git_status": status.stdout.strip()}


def _y1_wiring_is_third_party() -> dict[str, Any]:
    """F1 的机械兑现：推导模块不许 import 或引用任何 `declaration` 的接线/权限常量。

    **按 AST 查，不按子串查。** 第一版按子串，命中的是文档字符串里的散文
    （那段正是在说「本模块不 import declaration」）——**检查在自己的说明文字上误报**，
    与本项目栽过的「检查太弱」是同一个病的反面：检查太笨。
    """
    import ast  # noqa: PLC0415

    tree = ast.parse(Path(inspect.getfile(derive)).read_text())
    banned_names = {"IN_WIRING", "OUT_WIRING", "BINDINGS", "SPEC", "LOWERING"}
    bad_imports, bad_names = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bad_imports += [a.name for a in node.names if "mechanisms" in a.name]
        elif isinstance(node, ast.ImportFrom):
            if node.module and "mechanisms" in node.module:
                bad_imports.append(node.module)
        elif isinstance(node, ast.Name) and node.id in banned_names:
            bad_names.append(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in banned_names:
            bad_names.append(node.attr)
    return {"passed": not bad_imports and not bad_names,
            "banned_imports": sorted(set(bad_imports)),
            "banned_names": sorted(set(bad_names)),
            "method": "AST（不按子串——第一版在自己的文档字符串上误报）"}


def _y2_probe_discriminates(core) -> dict[str, Any]:
    """推导器负控：探针必须能把覆写型判成 `set`、求和型判成 `add`（自检在适配器区）。"""
    results = derive.probe_selftest(core)
    return {
        "passed": results.get("PositiveFloat") == "add" and results.get("SetFloat") == "set",
        **results,
    }


def _classify_claims(hand: list, derived: list) -> dict[str, Any]:
    """把 claims 的差异分成两类——预注册 `f948447` §5 要求分清，不许混为一谈。

    - **推不出来**：信息不在第三方交付物里 → 真正的 H0，是「必须人写」的部分
    - **推得更细 / 布局不同**：信息在，是手写声明当初的选择或被端口粒度限制

    机械判据：
    - `finer`：每条手写路径都是某条推导路径的前缀，且推导条数更多
    - `layout`：两侧路径在**各自去掉共同前缀**后集合相同
    - `unknown`：以上都不成立 —— 这一档才是「推不出来」的候选
    """
    hp = {tuple(p) for p, _ in hand}
    dp = {tuple(p) for p, _ in derived}
    if hp == dp:
        return {"kind": "identical"}
    if len(dp) > len(hp) and all(any(d[: len(h)] == h for d in dp) for h in hp):
        return {"kind": "finer",
                "why": "推导给出更细的路径；手写当初被端口粒度限制（第十七个里程碑已记）"}

    def strip(paths: set) -> set:
        if not paths:
            return paths
        n = 0
        while all(len(p) > n + 1 for p in paths) and len({p[n] for p in paths}) == 1:
            n += 1
        return {p[n:] for p in paths}

    if strip(hp) == strip(dp):
        return {"kind": "layout",
                "why": "去掉各自的共同前缀后相同；差的是**我们选的状态布局**，不是信息"}
    return {"kind": "underivable",
            "why": "信息不在第三方交付物里——这一项必须人写"}


def _compare(name: str, spec: dict, core) -> dict[str, Any]:
    cfg = PROVIDERS[name]
    D = cfg["declaration"]
    hand_claims = sorted((tuple(c.path), c.permission) for c in D.SPEC.claims)
    derived_claims = sorted((tuple(c.path), c.permission) for c in spec["claims"])
    hand_ops = {b.port: b.operation for b in D.BINDINGS}
    derived_ops = dict(spec["operations"])
    return {
        "claims_match": hand_claims == derived_claims,
        "hand_claims": [[list(p), k] for p, k in hand_claims],
        "derived_claims": [[list(p), k] for p, k in derived_claims],
        "effects_match": set(D.SPEC.allowed_effects) == set(spec["allowed_effects"]),
        "hand_effects": sorted(D.SPEC.allowed_effects),
        "derived_effects": sorted(spec["allowed_effects"]),
        "claims_mismatch": _classify_claims(hand_claims, derived_claims),
        "operations_match": hand_ops == derived_ops,
        "hand_operations": hand_ops,
        "derived_operations": derived_ops,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=REPO / "results/eighteenth/summary.json")
    args = ap.parse_args()

    core = _core()
    y0 = _y0_safety_line()
    y1 = _y1_wiring_is_third_party()
    y2 = _y2_probe_discriminates(core)

    per_provider: dict[str, Any] = {}
    for name, cfg in PROVIDERS.items():
        kwargs = {k: (core if v == "<core>" else v)
                  for k, v in cfg["generator_kwargs"].items()}
        tree = _resolve(cfg["generator"])(**kwargs)
        nodes = list(derive.process_nodes(tree, cfg["address_suffix"]))
        if not nodes:
            per_provider[name] = {"error": "第三方生成器里找不到该 process 节点"}
            continue
        foreign = _resolve(cfg["declaration"].FOREIGN)
        # config 也从第三方生成器给的节点里取——仍然是第三方交付物，不是我们写的
        outputs_schema, how = derive.outputs_declared_by(
            foreign, derive.config_of(nodes[0]), core
        )
        spec = derive.derive_spec(core, nodes[0], outputs_schema)
        per_provider[name] = {**_compare(name, spec, core), "outputs_obtained_by": how}

    y3 = all(p.get("claims_match") for p in per_provider.values())
    y4 = all(p.get("effects_match") for p in per_provider.values())
    y5 = all(p.get("operations_match") for p in per_provider.values())
    # Y6：推导声明与手写不同则无从「用它重跑」——如实记为未达成，不假装跑过
    y6 = y3 and y4 and y5 and y0["passed"]

    units = [y0["passed"], y1["passed"], y2["passed"], y3, y4, y5, y6]
    invalid = (not y2["passed"]) or (not y1["passed"]) or (not y0["passed"])
    h1 = (not invalid) and all(units)
    h0 = (not invalid) and not all(units)
    verdict = decide(h1=h1, h0=h0, invalid=invalid)

    summary = {
        "schema": "newlife.eighteenth.derive-authority.v1",
        "preregistration": "f948447",
        "units": {
            "Y0_safety_line": y0,
            "Y1_wiring_is_third_party": y1,
            "Y2_probe_discriminates": y2,
            "Y3_claims_match": {"passed": y3},
            "Y4_effects_match": {"passed": y4},
            "Y5_operations_match": {"passed": y5},
            "Y6_artifacts_unchanged_under_derived": {
                "passed": y6,
                "note": "Y3–Y5 不全为真时无从「用推导声明重跑」，如实记未达成，不假装跑过",
            },
        },
        # **判定之记录与本次运行分开写。** 本 runner 现在出 H1，但那是两条修法
        # 做完之后的结果；冻结预注册下做出的判定是 H0，那一条不因后来的修复而改写。
        # 静态声明，不参与合取（预注册 §3 F4 管的是「期望值」，历史不是期望值）。
        "judgment_of_record": {
            "verdict": "H0",
            "judged_on": "2026-09-03",
            "preregistration": "f948447",
            "artifact_sha256_at_judgment": "bae0508a5e19d3b4a574d925",
            "why_this_run_differs": (
                "H0 指向的两条修法已做完：① 第十五个改用第三方自己给的状态布局"
                "（原来的 cell/ 前缀是我们凭空加的）；② 推导塌到接入路径的粒度上限"
                "（admit() 对每个端口只发一条 StateDelta）。两条都不是「改手写声明去"
                "迁就推导」——前者去掉我们自己加的东西，后者的理由取自 admit() 的代码。"
            ),
        },
        "per_provider": per_provider,
        "underivable_items": sorted(
            f"{n}.claims" for n, p in per_provider.items()
            if p.get("claims_mismatch", {}).get("kind") == "underivable"
        ),
        "what_this_h0_means": (
            "Y4（allowed_effects）与 Y5（add/set 算符）三个 provider 全部推导正确——"
            "**算符正是类型-效应系统文献点名「从接口类型推不出来」的那一项**。"
            "差只差在 claims，且两处差异都不是「信息缺失」，见每个 provider 的 claims_mismatch。"
        ),
        "derivation_sources": {
            name: {"generator": cfg["generator"], "kwargs": {
                k: ("<core>" if v == "<core>" else v)
                for k, v in cfg["generator_kwargs"].items()}}
            for name, cfg in PROVIDERS.items()
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _text = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  Y0 安全绳（三份产物不变）: {y0['passed']}")
    print(f"  Y1 接线真取自第三方:       {y1['passed']}")
    print(f"  Y2 探针能分辨 add/set:     {y2['passed']}  {y2.get('PositiveFloat')}/{y2.get('SetFloat')}")
    print(f"  Y3 claims 逐项相同:        {y3}")
    print(f"  Y4 allowed_effects 相同:   {y4}")
    print(f"  Y5 算符相同:               {y5}")
    print(f"  Y6 产物在推导声明下不变:   {y6}")
    for name, p in per_provider.items():
        if "error" in p:
            print(f"    {name}: {p['error']}"); continue
        print(f"    {name:14s} claims={p['claims_match']} effects={p['effects_match']} ops={p['operations_match']}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
