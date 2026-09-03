"""第九世界的 verdict runner：真 tick 循环的终止条件能不能用纯数据表达。

判据冻结于 exloop 的预注册（freeze commit `10e26c7`）。三条合取，机械算出：

1. `ForagingWorld.run` 与 `.tick` 在 `mechanisms/resource_foraging/` 下消失，
   且范围外的部件一个都没少
2. 终止条件是纯数据、算符全在冻结集内、`observable` 全是已声明观测量
3. `results/v0.2/gate.json` 逐字节不变

**C3 本次未能评估**：重跑 v0.2 gate 需要外部 L2 录制根目录（`--l2-root`/`--parworlds`）。
合取判据在 C1 已经失败，C3 的取值不改变 verdict——但未评估就是未评估，如实记，
不写成「通过」也不写成「失败」。
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys

ABSORBED = ("ForagingWorld.run", "ForagingWorld.tick")
WORLD_DIR = "packages/newlife/src/newlife/mechanisms/resource_foraging"
CONFIG = f"{WORLD_DIR}/spec.py"
REPO = pathlib.Path(__file__).resolve().parents[5]


def enumerate_parts(directory: pathlib.Path) -> set[str]:
    out: set[str] = set()
    for path in sorted(directory.glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.add(node.name)
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.add(f"{node.name}.{sub.name}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    sys.path.insert(0, str(REPO / "packages/newlife/src"))
    from newlife.core.harness import OPERATORS, config_is_pure_data  # noqa: PLC0415
    from newlife.mechanisms.resource_foraging.spec import WORLD  # noqa: PLC0415

    present = enumerate_parts(REPO / WORLD_DIR)
    still_there = sorted(p for p in ABSORBED if p in present)
    c1 = not still_there

    pure, offenders = config_is_pure_data(str(REPO / CONFIG))
    loop = WORLD.loop
    ops = sorted({c.op for c in loop.while_all})
    ops_ok = set(ops) <= set(OPERATORS)
    declared = set(loop.observables)
    obs_ok = all(c.observable in declared for c in loop.while_all)
    c2 = pure and ops_ok and obs_ok

    summary = {
        "schema": "newlife.ninth-world.verdict.v1",
        "prereg_freeze_commit": "10e26c7",
        "c1_parts_absorbed": {
            "absorbed": list(ABSORBED), "still_present": still_there, "passed": c1,
            "why": ("`run` 是混合部件：21 行里只有中间的 while 是 simulator，"
                    "前后是 frame（tick-0 快照 + WorldRunResult 聚合）。"
                    "只吃循环则 run 不消失；连带搬走前后两段则超出 goal §4 的范围。"
                    "两条路都是 H0-a。此外通用 harness 假设自己拥有引擎装配，"
                    "而 World 1 已经拥有——只能并排贴上去借一个循环，不是吃掉。")
                   if still_there else "",
        },
        "c2_termination_is_pure_data": {
            "config": CONFIG, "pure_data": pure, "offenders": offenders,
            "operators_used": ops, "operators_frozen": sorted(OPERATORS),
            "operators_within_frozen_set": ops_ok,
            "clauses": len(loop.while_all), "composition": "conjunction-only",
            "observables_declared": sorted(declared),
            "all_observables_declared": obs_ok, "passed": c2,
        },
        "c3_gate_bit_identical": {
            "evaluated": False,
            "reason": ("重跑 v0.2 gate 需要外部 L2 录制根目录（--l2-root/--parworlds），"
                       "本次不可得；合取在 C1 已失败，C3 不改变 verdict"),
        },
        "verdict": "H1" if (c1 and c2) else "H0",
        "h0_shape": ("H0-a：表达不了 / 必须超范围搬运" if not c1 else
                     ("H0-b：靠扩算符集或取值语言" if not c2 else "")),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    print(f"  C1 部件消失: {'PASS' if c1 else 'FAIL'}  残留={still_there or '无'}")
    print(f"  C2 终止条件纯数据: {'PASS' if c2 else 'FAIL'}  算符={ops} ⊆ 冻结集={ops_ok}")
    print(f"  C3 gate 逐位不变: 未评估（{summary['c3_gate_bit_identical']['reason'][:28]}…）")
    print(f"\nverdict: {summary['verdict']}  {summary['h0_shape']}")
    return 0 if summary["verdict"] == "H1" else 1
if __name__ == "__main__":
    raise SystemExit(main())
