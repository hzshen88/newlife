"""第七世界的 verdict runner：harness 部件归类的覆盖核对 + 词表封闭性判定。

判据冻结于 exloop 的预注册（freeze commit `c10dcb3`）。本模块只计算冻结的东西。

**枚举独立重做，不读 exloop 那份台账**——判定不能建立在被判定方自己的输出上；
第三世界的 M1 是同一条纪律。归类表是**声明**的输入，本模块核对它恰好覆盖枚举集。

**verdict 从合取机械算出，从不手填。**
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
from typing import Any

# --- 预注册 §3.1 的冻结词表，不得扩充 ---
VOCABULARY = ("model", "simulator", "frame", "rng")

# --- 预注册 §3.2 的冻结对象，逐字抄入 ---
HARNESS_FILES: dict[str, tuple[str, ...]] = {
    "world1": ("mechanisms/resource_foraging/world.py",
               "mechanisms/resource_foraging/assay.py"),
    "world2": ("mechanisms/second_world/world.py",),
    "world3": (),
    "world4": ("mechanisms/fourth_world/world.py",),
}
SRC = pathlib.Path(__file__).resolve().parents[1]


def enumerate_parts(rel: str) -> list[str]:
    """独立枚举：模块级函数 + 类方法，返回 `file::name`。"""
    path = SRC / rel
    if not path.exists():
        return []
    out: list[str] = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(f"{rel}::{node.name}")
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(f"{rel}::{node.name}.{sub.name}")
    return out


def adjudicate_world3() -> dict[str, Any]:
    """S1/S2：World 3 没有 world.py，它的 harness 在哪。"""
    third = SRC / "mechanisms/third_world"
    files = sorted(p.name for p in third.glob("*.py"))
    verdict_runner = SRC / "conform/third_world_verdict.py"
    engine_calls = []
    if verdict_runner.exists():
        text = verdict_runner.read_text()
        for token in ("ReferenceKernel", "register_mechanism", "_run_stage",
                      "apply_batch_fast", "guarded_read_fast"):
            if token in text:
                engine_calls.append(token)
    return {
        "third_world_files": files,
        "verdict_runner_engine_calls": engine_calls,
        "ruling": ("S2：World 3 没有 harness——它既不装配引擎也不跑阶段，"
                   "verdict runner 直接调机制函数。它是 P3 唯一成立的实例，"
                   "代价是完全不接入 registry/引擎"
                   if not engine_calls else
                   "S1：harness 落在 verdict runner 里——判定逻辑与 harness 混在一起"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--classification", required=True, type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    enumerated: list[str] = []
    for files in HARNESS_FILES.values():
        for rel in files:
            enumerated += enumerate_parts(rel)

    decl_raw = json.loads(args.classification.read_text())
    decl_raw.pop("_note", None)
    decl = {k: v[0] for k, v in decl_raw.items()}
    reasons = {k: v[1] for k, v in decl_raw.items()}

    keys = set(enumerated)
    missing = sorted(keys - set(decl))
    phantom = sorted(set(decl) - keys)
    unclassified = sorted(k for k, v in decl.items() if v == "unclassified")
    out_of_vocab = sorted(k for k, v in decl.items()
                          if v not in VOCABULARY and v != "unclassified")

    covered = not (missing or phantom or out_of_vocab)
    invalid = not covered
    h1 = covered and not unclassified
    h0 = covered and bool(unclassified)

    from collections import Counter
    dist = dict(Counter(decl.values()))

    summary = {
        "schema": "newlife.seventh-world.verdict.v1",
        "prereg_freeze_commit": "c10dcb3",
        "enumerated_parts": len(enumerated),
        "declared_parts": len(decl),
        "distribution": dist,
        "coverage": {"missing": missing, "phantom": phantom,
                     "out_of_vocabulary": out_of_vocab, "ok": covered},
        "unclassified": [{"part": k, "reason": reasons[k]} for k in unclassified],
        "invalid": invalid,
        "h1_vocabulary_closed": h1,
        "h0_at_least_one_unclassified": h0,
        "verdict": "INVALID" if invalid else ("H1" if h1 else "H0"),
        "world3": adjudicate_world3(),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    print(f"  枚举 {len(enumerated)} · 声明 {len(decl)} · 覆盖 {'OK' if covered else '不完整'}")
    print(f"  分布: {dist}")
    for u in summary["unclassified"]:
        print(f"  unclassified: {u['part'].split('::')[-1]}")
        print(f"      {u['reason'][:96]}")
    print(f"\n  World 3: {summary['world3']['ruling']}")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
