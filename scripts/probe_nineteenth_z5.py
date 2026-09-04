"""第十九个里程碑 Z5 的判定力探测 —— **post-hoc，不写进 results/**。

Z5 的冻结判据是「`yield` 设成 dFBA 某点的产率后重扫，Monod 产率仍逐点恒定」。
Monod 的配置里**没有氧的位置**，所谓「重扫」是同一份配置跑五遍，
所以该判据在任何物理配置下都为真——**零判定力**。

本探测做两件事，都不改动任何已判定产物：
  ① 证明恒真：对一批差异极大的 `yield` 参数，逐个求 Z5 表达式的值。
  ② 补上 Z5 本该做的负控：Monod 的**表观**产率随声明 `yield` 怎么变，
     以及单一常数能否覆盖 dFBA 在扫描上的那组产率。
"""

from __future__ import annotations

import json
from pathlib import Path

from newlife.conform.yield_verdict import MONOD, O2_SWEEP, _monod_config, _run

REPO = Path(__file__).resolve().parents[1]
ARTIFACT = REPO / "results/nineteenth/summary.json"


def apparent(declared: float) -> float:
    """跑一次 Monod，返回表观产率。"""
    return _run(MONOD, "probe-monod", _monod_config(declared))["yield"]


def z5_value(declared: float) -> bool:
    """逐字复算 Z5：同一配置跑 len(O2_SWEEP) 遍，取极差。"""
    ys = [_run(MONOD, "probe-monod", _monod_config(declared))["yield"] for _ in O2_SWEEP]
    return (max(ys) - min(ys)) < 1e-9


def main() -> int:
    dfba = [r["yield"] for r in json.loads(ARTIFACT.read_text())["dfba"]]

    print("① 恒真探测：Z5 对任意 yield 参数的取值")
    for declared in (1e-6, 0.0552442948756313, 1.0, 1e3):
        print(f"   yield={declared:<20g} Z5={z5_value(declared)}")

    print("\n② 负控本该测的：表观产率 vs 声明 yield")
    print(f"   {'声明':>12} {'表观':>12} {'相对偏差':>10}")
    rows = []
    for declared in sorted({*dfba, 1.0}):
        got = apparent(declared)
        rows.append((declared, got))
        print(f"   {declared:12.6f} {got:12.6f} {(got - declared) / declared:9.1%}")

    print(f"\n   dFBA 在扫描上的产率: {[round(y, 6) for y in dfba]}")
    print(f"   极差 {max(dfba) - min(dfba):.6f}（相对 {(max(dfba) - min(dfba)) / min(dfba):.1%}）")
    print("   Monod 的表观产率与氧无关（②中每个参数只有一个值），")
    print("   故任一常数至多命中 dFBA 五点中的一点 —— 这才是 Z5 想说的话。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
