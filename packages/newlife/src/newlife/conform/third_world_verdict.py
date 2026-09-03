"""第三世界的 verdict runner：claim (i) 逐步 oracle 重放 + claim (ii) 聚合，机械合取。

判据冻结于 `exloop` 的预注册（freeze commit `aa052dd`）。本模块只计算冻结的东西。

**这里的 oracle 与 `mechanisms/third_world/moran.py` 是同一规格的两个独立实现。**
claim (i) 检验的正是它们是否逐值一致；共用一份代码会让判据恒真（预注册 §6 的 M1）。
两者都按 question 的规格走字面浮点序列——规格相同、代码独立，这才是「独立实现」的
意思，不是「用不同的数学」。

**verdict 从合取机械算出，从不手填**；本模块不判 goal 的痛点。
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from proofroot.rng import derive_stream_seed

from newlife.mechanisms.resource_foraging.injection import DevStream
from newlife.mechanisms.third_world.moran import StepRecord, run_replicate

# --- 预注册 §3 的冻结参数，逐字抄入 ---
N_POP = 6
I0 = 1
R_VALUES: tuple[float, ...] = (0.5, 1.0, 1.5)
R_LABELS = {0.5: "1_2", 1.0: "1", 1.5: "3_2"}
REPLICATES_PER_CELL = 1350
STEP_CAP = 227
TARGETS = {0.5: 0.015873, 1.0: 0.166667, 1.5: 0.365414}
ACCEPTANCE = {0.5: (11, 33), 1.0: (193, 258), 1.5: (451, 536)}
RNG_VERSION = "evidencecore-rng-v1"


def oracle_post_state(
    n_pop: int, r: float, pre: int, draw1: float, draw2: float
) -> int:
    """独立 oracle：由 `(pre, draw1, draw2)` 算出应得的 post-state。

    与机制模块同规格、不同实现路径。`draw1` 按**消耗顺序**解释——它就是先被取出的
    那个值，用于繁殖者判定（M2）；把它当成「用于繁殖者的那个」会让角色互换类 bug
    对本重放完全不可见。
    """
    repro_threshold = pre * r / (pre * r + (n_pop - pre))
    die_threshold = pre / n_pop
    reproducer_is_A = draw1 < repro_threshold
    dier_is_A = draw2 < die_threshold
    if reproducer_is_A and not dier_is_A:
        return pre + 1
    if dier_is_A and not reproducer_is_A:
        return pre - 1
    return pre


def replay_claim_i(records: list[StepRecord], r: float) -> tuple[bool, dict | None]:
    """逐步重放。返回 `(通过?, 首个失败步的完整记录)`。

    同时兑现 M5 的轨迹完整性：首步 `pre == I0`、`pre[t+1] == post[t]`、
    末步的 post 即终态——claim (ii) 的终态必须读自这条验过的链，不是另一处统计。
    """
    if not records or records[0].pre_state != I0:
        return False, {"reason": "first step's pre_state != i0"}
    for index, record in enumerate(records):
        expected = oracle_post_state(
            N_POP, r, record.pre_state, record.draw1, record.draw2
        )
        if expected != record.post_state:
            return False, {
                "step": index,
                "pre_state": record.pre_state,
                "draw1": record.draw1,
                "draw2": record.draw2,
                "expected_post": expected,
                "actual_post": record.post_state,
            }
        if (
            index + 1 < len(records)
            and records[index + 1].pre_state != record.post_state
        ):
            return False, {"step": index, "reason": "pre[t+1] != post[t]"}
    return True, None


def run_cell(r: float, world_seed: int) -> dict[str, Any]:
    """一个 cell：1350 个 replicate，逐个流式验证，不归档全部逐步记录（R4）。"""
    label = R_LABELS[r]
    fixations = 0
    censored = 0
    claim_i_failures: list[dict] = []
    total_steps = 0

    for k in range(REPLICATES_PER_CELL):
        seed = derive_stream_seed(
            RNG_VERSION, world_seed, f"third-world-r{label}-replicate-{k:04d}"
        )
        stream = DevStream(seed)
        records, final, steps = run_replicate(
            N_POP, r, I0, _FloatSource(stream), STEP_CAP
        )
        total_steps += steps

        ok, failure = replay_claim_i(records, r)
        if not ok:
            claim_i_failures.append({"replicate": k, **(failure or {})})

        if steps >= STEP_CAP and 0 < final < N_POP:
            censored += 1
        elif final == N_POP:
            fixations += 1

    lo, hi = ACCEPTANCE[r]
    return {
        "r": label,
        "replicates": REPLICATES_PER_CELL,
        "fixations": fixations,
        "acceptance_region": [lo, hi],
        "target": TARGETS[r],
        "censored": censored,
        "total_steps": total_steps,
        "claim_i_failures": claim_i_failures[:5],
        "claim_i_failure_count": len(claim_i_failures),
        "claim_i_passed": not claim_i_failures,
        "claim_ii_passed": lo <= fixations <= hi,
    }


class _FloatSource:
    """把 `DevStream.draw_float()` 适配成机制模块要的 `next()`。"""

    def __init__(self, stream: DevStream) -> None:
        self._stream = stream

    def next(self) -> float:
        return self._stream.draw_float()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--world-seed", type=int, default=20260902)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    cells = [run_cell(r, args.world_seed) for r in R_VALUES]

    claim_i = all(c["claim_i_passed"] for c in cells)
    claim_ii = all(c["claim_ii_passed"] for c in cells)
    zero_censoring = all(c["censored"] == 0 for c in cells)
    passed = bool(claim_i and claim_ii and zero_censoring)

    summary = {
        "schema": "newlife.third-world.gate.v1",
        "prereg_freeze_commit": "aa052dd",
        "world_seed": args.world_seed,
        "cells": cells,
        "claim_i_passed": claim_i,
        "claim_ii_passed": claim_ii,
        "zero_censoring": zero_censoring,
        # 位置占位：布尔由 Definition 从三值导出并填入，键序不变
        "passed": None,
    }
    verdict = decide(h1=passed, h0=not passed)
    summary, _text = emit(
        verdict, summary, RenderSpec(verdict_key=None, passed_key="passed"), args.out
    )
    if args.out:
        print(f"summary written: {args.out}")

    for cell in cells:
        lo, hi = cell["acceptance_region"]
        print(
            f"  r={cell['r']:4s} fixations={cell['fixations']:4d} in [{lo},{hi}]  "
            f"censored={cell['censored']}  claim(i)={'PASS' if cell['claim_i_passed'] else 'FAIL'}"
            f"  claim(ii)={'PASS' if cell['claim_ii_passed'] else 'FAIL'}"
        )
    print(f"verdict: {'H1 accepted' if passed else 'H0'}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
