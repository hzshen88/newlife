"""第十四个里程碑的判定：同一个世界跑在两个运行时上，结果一样吗。

预注册 `1b9257a` §2：verdict = U0 ∧ U1 ∧ U2，机械合取，`passed` 不手填。

**负控内建**：把 pb 侧的 store handler 改坏之后，U2 必须变红。若改坏了还相同，
说明这个比对没有判定力——判 INVALID，不判 H1。这是本项目栽过两次的坑
（「用一个检测不出任何东西的变异去判定『通过』」）。
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

from newlife.adapters.process_bigraph import lowering as pb_lowering
from newlife.adapters.process_bigraph.world_runtime import run_world
from newlife.adapters.reference_kernel.world_runtime import ReferenceKernelRuntime
from newlife.conform.contract.canonical_ruler import canonical_bytes
from newlife.conform.fourth_world_verdict import (
    CLAIM_II_POP,
    CLAIM_II_REPLICATES,
    CLAIM_II_SAMPLE,
    CLAIM_II_THETA,
    _Dev,
)
from newlife.core.harness import GenericWorld
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code
from newlife.mechanisms.fourth_world.spec import WORLD
from newlife.mechanisms.second_world.mechanisms import RecordedDrawStream

REPO = Path(__file__).resolve().parents[5]
BASELINE = "results/fourth-world/summary.json"
WORLD_SEED = 20260901


def _inputs(k: int) -> tuple[dict, dict]:
    """两条路径的输入由**同一处**构造（预注册 §3 F3），不许各建各的。"""
    orng = random.Random(WORLD_SEED + 10_000_000 + k)
    streams = {
        "builder": _Dev(WORLD_SEED + k),
        "observer": RecordedDrawStream([orng.random() for _ in range(400)]),
    }
    runtime = {
        "n_sample": CLAIM_II_SAMPLE,
        "n_pop": CLAIM_II_POP,
        "nsam": CLAIM_II_SAMPLE,
        "theta": CLAIM_II_THETA,
        "replicate_index": k,
    }
    return streams, runtime


def _unit_0() -> dict:
    """安全绳：harness 改收 runtime 工厂之后，RK 路径产物逐字节不变。

    基线不是硬编码常量，是 git 里已提交的那份产物——重跑之后 `git status` 干净
    即通过（预注册 §3 F4：runner 不读本文件以外的期望值）。
    """
    run = subprocess.run(
        [sys.executable, "-m", "newlife.conform.fourth_world_verdict"],
        cwd=REPO, capture_output=True, text=True,
    )
    if run.returncode != 0:
        return {"passed": False, "reason": f"World 4 runner 非零退出：{run.returncode}"}
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", BASELINE],
            cwd=REPO, capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as exc:  # git 缺失是环境问题，不是「基线不同」
        raise SystemExit(
            "git 不可用——U0 的基线取不到。这是环境缺失，不是判定结果；"
            f"非 Python 依赖见 conform/dep_declaration.py。原始错误：{exc}"
        ) from exc
    dirty = status.stdout.strip()
    return {
        "passed": dirty == "",
        "baseline": BASELINE,
        "baseline_commit": subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", BASELINE],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip(),
        "git_status": dirty,
    }


def _compare(replicates: int) -> dict:
    """U1 与 U2：pb 路径跑完，且与 RK 路径逐字节相同。"""
    t0 = time.perf_counter()
    completed = 0
    identical = 0
    first_diff: dict | None = None
    for k in range(replicates):
        s_rk, r_rk = _inputs(k)
        s_pb, r_pb = _inputs(k)
        a = GenericWorld(WORLD, streams=s_rk, runtime=r_rk,
                         backend=ReferenceKernelRuntime).run()
        b = run_world(WORLD, s_pb, r_pb)
        if "segsites" in b and "genotype_rows" in b:
            completed += 1
        if canonical_bytes(a) == canonical_bytes(b):
            identical += 1
        elif first_diff is None:
            first_diff = {"replicate": k, "reference_kernel": a, "process_bigraph": b}
    return {
        "replicates": replicates,
        "pb_completed": completed,
        "byte_identical": identical,
        "first_difference": first_diff,
        "seconds": round(time.perf_counter() - t0, 1),
    }


def _negative_control() -> dict:
    """把 pb 的 store handler 改坏，U2 必须变红。不变红即比对无判定力。"""
    key = "mapping-direct-structural"
    original = pb_lowering.STORE_HANDLERS[key]

    def broken(op, port, _view, _interval):
        after = dict(op.payload["after"])
        after["time"] = tuple(reversed(after["time"]))
        return {port: after}

    pb_lowering.STORE_HANDLERS[key] = broken
    try:
        s_rk, r_rk = _inputs(0)
        s_pb, r_pb = _inputs(0)
        a = GenericWorld(WORLD, streams=s_rk, runtime=r_rk,
                         backend=ReferenceKernelRuntime).run()
        b = run_world(WORLD, s_pb, r_pb)
        went_red = canonical_bytes(a) != canonical_bytes(b)
    finally:
        pb_lowering.STORE_HANDLERS[key] = original
    return {"mutation": f"{key} 写树时反转 time", "went_red": went_red}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=CLAIM_II_REPLICATES)
    parser.add_argument("--out", type=Path,
                        default=REPO / "results/fourteenth/summary.json")
    args = parser.parse_args()

    u0 = _unit_0()
    control = _negative_control()
    cmp_ = _compare(args.replicates)

    u1 = cmp_["pb_completed"] == cmp_["replicates"]
    u2 = cmp_["byte_identical"] == cmp_["replicates"]

    # IC-1：U0 假 → 差异归因不清，作废，不判 H0。
    # 负控不红 → 比对无判定力，作废。
    # IC-3：超时 → 可用性问题，作废。
    invalid = (not u0["passed"]) or (not control["went_red"]) or cmp_["seconds"] > 300
    h1 = (not invalid) and u0["passed"] and u1 and u2
    h0 = (not invalid) and not (u1 and u2)
    verdict = decide(h1=h1, h0=h0, invalid=invalid)

    summary = {
        "schema": "newlife.fourteenth.cross-runtime.v1",
        "preregistration": "1b9257a",
        "units": {
            "U0_safety_line": u0,
            "U1_pb_completes": {"passed": u1, "completed": cmp_["pb_completed"]},
            "U2_byte_identical": {"passed": u2, "identical": cmp_["byte_identical"]},
        },
        "negative_control": control,
        "comparison": cmp_,
        "runtimes": ["reference_kernel", "process_bigraph"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary, _text = emit(verdict, summary, RenderSpec(verdict_key="verdict"), args.out)

    print(f"  U0 安全绳 (RK 产物不变): {'PASS' if u0['passed'] else 'FAIL'}")
    print(f"  U1 pb 跑完:              {cmp_['pb_completed']}/{cmp_['replicates']}")
    print(f"  U2 逐字节相同:            {cmp_['byte_identical']}/{cmp_['replicates']}")
    print(f"  负控（改坏 pb 写入）变红: {control['went_red']}")
    print(f"  用时 {cmp_['seconds']}s")
    if cmp_["first_difference"]:
        print(f"  首个差异: replicate {cmp_['first_difference']['replicate']}")
    print(f"\nverdict: {verdict}")
    return exit_code(verdict)


if __name__ == "__main__":
    raise SystemExit(main())
