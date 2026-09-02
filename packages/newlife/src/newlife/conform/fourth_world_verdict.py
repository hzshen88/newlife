"""第四世界的 verdict runner：claim (i) 精确枚举 + claim (ii) 聚合，机械合取。

判据冻结于 `exloop` 预注册（freeze commit `24bb02e`）。本模块只计算冻结的东西。

**两条边界，来自预注册 §7：**

- verdict 从合取机械算出，**从不手填**；
- 本模块**不判 goal 的 P1**。它读 `reuse-trace.json` 只为把事实抄进 bundle 供人
  判定，`summary.json` 的 schema 对 goal 词汇封闭（无 `p1` / `achieved` /
  `regressed` 等键或字符串值）。P1 由人写在 goal 文档与 `docs/worlds/`。
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import statistics
from fractions import Fraction as F
from itertools import combinations
from typing import Any

from newlife.mechanisms.fourth_world.genealogy import moran_step_outcome
from newlife.mechanisms.fourth_world.world import MoranGenealogyWorld
from newlife.mechanisms.second_world.ms_coalescent import RecordedDrawStream

# --- 预注册 §3 的冻结参数，逐字抄入，不重新推导 ---
CLAIM_I_SAMPLES = (3, 4, 5, 6, 7)
CLAIM_I_POP = 10  # N=10 槽位布局，不是默认满占用
CLAIM_II_SAMPLE = 6
CLAIM_II_POP = 10
CLAIM_II_THETA = 2.0
CLAIM_II_REPLICATES = 2101
CLAIM_II_TARGET = F(137, 30)
CLAIM_II_LO = 4.4286
CLAIM_II_HI = 4.7047
HISTORY_BUDGET = 100_000  # IC-1


def kingman_ranked_history_probability(n: int) -> F:
    """Kingman 的 ranked labelled history 分布是均匀的，每个恰为
    `2^(n-1) / (n!(n-1)!)` —— 闭式，与 Moran 侧不共用任何枚举代码。"""
    return F(2 ** (n - 1), math.factorial(n) * math.factorial(n - 1))


def _merge_pair_weights(
    blocks: tuple[int, ...], slots: dict[int, int], n_pop: int
) -> dict[tuple[int, int], int]:
    """在给定槽位布局下，枚举全部 (reproducer, dier)，数出每一对 block 的合并次数。

    **调用 builder 自己的 `moran_step_outcome`**（预注册 R5）：枚举与建树共用一份
    步规则，所以 builder 的步规则出错时这里也会错，而不是各错各的。
    """
    labels: list[int | None] = [None] * n_pop
    for block, slot in slots.items():
        labels[slot] = block
    weights = {pair: 0 for pair in combinations(sorted(blocks), 2)}
    for reproducer in range(n_pop):
        for dier in range(n_pop):
            kind, a, b = moran_step_outcome(labels, reproducer, dier)
            if kind == "merge":
                weights[tuple(sorted((a, b)))] += 1
    return weights


def moran_ranked_history_distribution(n: int, n_pop: int) -> dict[tuple, F]:
    """builder 步规则诱导的 ranked labelled history 精确分布（有理数）。

    每条谱系恒占一个槽位，所以布局只需给出「哪 n 个槽位」；合并后存活的谱系留在
    繁殖者槽位，被合并的那个槽位空出——与 builder 完全一致。
    """
    start = tuple(frozenset([i]) for i in range(n))
    out: dict[tuple, F] = {}

    def rec(blocks: tuple, slot_of: dict, history: tuple, prob: F) -> None:
        if len(blocks) == 1:
            out[history] = out.get(history, F(0)) + prob
            return
        ids = {id(b): b for b in blocks}
        idx = {b: i for i, b in enumerate(blocks)}
        weights = _merge_pair_weights(
            tuple(idx[b] for b in blocks),
            {idx[b]: slot_of[b] for b in blocks},
            n_pop,
        )
        total = sum(weights.values())
        for (i, j), w in weights.items():
            if w == 0:
                continue
            bi, bj = blocks[i], blocks[j]
            merged = bi | bj
            rest = tuple(b for b in blocks if b not in (bi, bj))
            new_slots = {b: slot_of[b] for b in rest}
            # 合并后谱系位于繁殖者槽位；枚举里 j 侧来自繁殖者
            new_slots[merged] = slot_of[bj]
            rec(rest + (merged,), new_slots, history + ((bi, bj),), prob * F(w, total))
        del ids

    rec(start, {b: i for i, b in enumerate(start)}, (), F(1))
    return out


def run_claim_i() -> dict[str, Any]:
    """claim (i)：每个 n 的精确分布必须逐项等于 Kingman 的闭式。"""
    cells = []
    for n in CLAIM_I_SAMPLES:
        dist = moran_ranked_history_distribution(n, CLAIM_I_POP)
        expected = kingman_ranked_history_probability(n)
        mismatches = sum(1 for p in dist.values() if p != expected)
        cells.append(
            {
                "n": n,
                "histories": len(dist),
                "expected_probability": str(expected),
                "mismatches": mismatches,
                "within_budget": len(dist) <= HISTORY_BUDGET,
                "passed": mismatches == 0 and len(dist) <= HISTORY_BUDGET,
            }
        )
    return {"cells": cells, "passed": all(c["passed"] for c in cells)}


class _Dev:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def next(self) -> float:
        return self._rng.random()


def run_claim_ii(world_seed: int) -> dict[str, Any]:
    """claim (ii)：2101 个 replicate 的 S̄ 必须落在冻结验收域内。"""
    values = []
    traces = []
    for k in range(CLAIM_II_REPLICATES):
        orng = random.Random(world_seed + 10_000_000 + k)
        world = MoranGenealogyWorld(
            CLAIM_II_SAMPLE,
            CLAIM_II_POP,
            CLAIM_II_THETA,
            _Dev(world_seed + k),
            RecordedDrawStream([orng.random() for _ in range(400)]),
            replicate_index=k,
        )
        values.append(world.run()["segsites"])
        if k == 0:
            traces.append(world.reuse_trace())
    mean = statistics.mean(values)
    return {
        "replicates": len(values),
        "mean_segsites": mean,
        "target": str(CLAIM_II_TARGET),
        "acceptance_region": [CLAIM_II_LO, CLAIM_II_HI],
        "passed": CLAIM_II_LO <= mean <= CLAIM_II_HI,
        "reuse_trace": traces[0],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--world-seed", type=int, default=20260902)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    claim_i = run_claim_i()
    claim_ii = run_claim_ii(args.world_seed)
    trace = claim_ii.pop("reuse_trace")

    # 机械合取，从不手填
    passed = bool(claim_i["passed"] and claim_ii["passed"])

    summary = {
        "schema": "newlife.fourth-world.gate.v1",
        "prereg_freeze_commit": "24bb02e",
        "world_seed": args.world_seed,
        "claim_i": claim_i,
        "claim_ii": claim_ii,
        # 事实抄录，供人判定 goal；本 bundle 不含任何 goal 词汇
        "observer_reuse": trace,
        "passed": passed,
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")
    else:
        print(text)

    print(f"claim (i):  {'PASS' if claim_i['passed'] else 'FAIL'}")
    print(
        f"claim (ii): {'PASS' if claim_ii['passed'] else 'FAIL'} "
        f"(mean {claim_ii['mean_segsites']:.4f} in "
        f"[{CLAIM_II_LO}, {CLAIM_II_HI}])"
    )
    print(f"verdict:    {'H1 accepted' if passed else 'H0'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
