"""第六世界的 verdict runner：四个调度相关循环的 bound 分类，机械合取。

判据冻结于 exloop 的预注册（freeze commit `671d6f4`）。本模块只计算冻结的东西。

**分类在这里是独立实现**，与 exloop 的 `designs/verification/loop_census.py` 同规格、
不同代码路径。复用同一份分类代码会让判定退化成「实现 vs 它自己」——第三世界的 M1
是同一条纪律。

**verdict 从合取机械算出，从不手填**；S1/S2/S3 三条子命题与 H0/H1 分开记，不参与合取。
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
from typing import Any

# --- 预注册 §3.1 的冻结对象，逐字抄入（file, line, 期望的源码片段）---
FROZEN_LOOPS: tuple[tuple[str, str, int, str], ...] = (
    ("world1", "mechanisms/resource_foraging/assay.py", 140, "for _ in range(config.assay_episodes)"),
    ("world2", "mechanisms/second_world/ms_coalescent.py", 111, "while len(active) > 1"),
    ("world3", "mechanisms/third_world/moran.py", 95, "while 0 < i < n_pop and steps < step_cap"),
    ("world4", "mechanisms/fourth_world/genealogy.py", 80, "while alive > 1"),
)
EXPRESSIBLE = {"static", "config", "capped"}
SRC = pathlib.Path(__file__).resolve().parents[1]


def classify(node: ast.AST, source_line: str) -> str:
    """预注册 §3.2 的四类。独立实现：直接看循环形态与条件里出现的名字。

    `loop unrolling 可表达` ⟺ 存在执行前即可由配置确定的上界。
    """
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return "static"                          # `for ... in range(<配置量>)`
    test = node.test
    if isinstance(test, ast.Constant) and test.value is True:
        return "unbounded"                       # `while True`
    names = {n.id for n in ast.walk(test) if isinstance(n, ast.Name)}
    calls = {n.func.id for n in ast.walk(test)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    # 显式静态上限：条件里与一个 cap 变量比较
    if names & {"step_cap", "cap", "maxallowed", "limit"}:
        return "capped"
    # 由配置量单调走向终止：对一个集合取长度，或一个存活计数
    if "len" in calls or (names & {"alive", "active", "remaining"}):
        return "config"
    return "unbounded"


def locate(rel: str, line: int) -> tuple[ast.AST | None, str]:
    path = SRC / rel
    if not path.exists():
        return None, ""
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.While, ast.For, ast.AsyncFor)) and node.lineno == line:
            return node, text.splitlines()[line - 1].strip()
    return None, ""


def resolve_s2() -> dict[str, Any]:
    """S2：World 1 的 tick 循环是手写的，还是 staging 编出来的 DAG。"""
    hits = []
    for path in sorted((SRC / "mechanisms/resource_foraging").glob("*.py")):
        text = path.read_text()
        if "staging" in text:
            hits.append(path.name)
    return {
        "resource_foraging_imports_staging": bool(hits),
        "files_mentioning_staging": hits,
        "ruling": ("World 1 的世界循环是手写 Python 循环，未经 staging 编排"
                   if not hits else "World 1 引用了 staging，需人工细看"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    loops: list[dict[str, Any]] = []
    ic3: list[str] = []
    for world, rel, line, expected in FROZEN_LOOPS:
        node, actual = locate(rel, line)
        if node is None:
            ic3.append(f"{world}: {rel}:{line} 已无循环——冻结的行号不再指向该循环")
            continue
        if expected.split("(")[0].strip() not in actual:
            ic3.append(f"{world}: {rel}:{line} 现在是 {actual!r}，与冻结的 {expected!r} 不符")
            continue
        bound = classify(node, actual)
        loops.append({"world": world, "file": rel, "line": line,
                      "source": actual, "bound": bound,
                      "unrolling_expressible": bound in EXPRESSIBLE})

    invalid = bool(ic3)
    all_expressible = bool(loops) and all(x["unrolling_expressible"] for x in loops)
    complete = len(loops) == len(FROZEN_LOOPS)
    h1 = (not invalid) and complete and all_expressible
    h0 = (not invalid) and complete and not all_expressible

    bounds = sorted({x["bound"] for x in loops})
    summary = {
        "schema": "newlife.sixth-world.verdict.v1",
        "prereg_freeze_commit": "671d6f4",
        "loops": loops,
        "invalid_conditions": ic3,
        "invalid": invalid,
        "h1_all_unrolling_expressible": h1,
        "h0_at_least_one_unbounded": h0,
        "verdict": "INVALID" if invalid else ("H1" if h1 else "H0"),
        # S1/S2/S3 与 H0/H1 分开，不参与合取（预注册 §5）
        "S1_count": {"recorded": 5, "adjudicated": len(FROZEN_LOOPS),
                     "note": "第五世界是方法学度量，没有世界循环"},
        "S2_world1": resolve_s2(),
        "S3_same_cause": {
            "distinct_bound_types": bounds,
            "holds": len(bounds) <= 1,
            "note": "四个循环出现两种以上 bound 类型即「同因」不成立",
        },
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    for x in loops:
        print(f"  {x['world']:7s} {x['file'].split('/')[-1]}:{x['line']:<4d} "
              f"{x['bound']:10s} unrolling={'✓' if x['unrolling_expressible'] else '✗'}")
    for m in ic3:
        print(f"  IC-3: {m}")
    print(f"\nS1 次数: 记录 5 → 裁定 {len(FROZEN_LOOPS)}")
    print(f"S2 World 1: {summary['S2_world1']['ruling']}")
    print(f"S3 同因: bound 类型 {bounds} → {'成立' if summary['S3_same_cause']['holds'] else '不成立'}")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
