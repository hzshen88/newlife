#!/usr/bin/env python3
"""一个里程碑的全部 gate，一条命令跑完。

由第二轮外审（2026-09-02）找出的缺口：三条新检查（@frozen、--vocabulary、
静默退化扫描）**被证明「能抓住」，但没有被证明「会被跑」**——它们只存在于
`gate_selftest.py` 的自检 harness 里，question 的验证命令块一条都没引用。
下一次同类漂移仍然不会被日常流程发现，只是从「没有机制」变成「有机制但没人跑」。

修的是**类**，不是那三条：这里有一份 `GATE_KINDS` 注册表，`gate_selftest.py`
会强制交叉核对——**它用到的每一种 gate，都必须在这份注册表里出现，或在
`EXEMPT` 里写明豁免理由**。以后再加新检查却忘了接进日常路径，自检直接红。
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

# 日常路径会跑的 gate：**注册表即执行体**，不是两份手写清单。
#
# 第三轮外审证实了双清单必然腐烂：交叉核对只验「注册了的有没有跑」，不验反向——
# 加了 `_run(...)` 却忘了登记就没人管。这里把 kind → 命令的构造合成一份，
# 「注册表说跑了而实际没跑」和「跑了却没登记」都变成结构上不可能。
def _gates(args, scan_targets: list[str]) -> dict:
    V = "verification/verify_doc_claims.py"
    S = "verification/silent_degradation_scan.py"
    return {
        # 各机制自身的性质，不依赖任何存储值
        "frozen_selftest": [V, "--selftest"],
        "silentdeg_selftest": [S, "--selftest"],
        # 对本里程碑文档与代码的检查
        # 豁免上限：现有 3 处（mutation_scan 的分类过滤器、本扫描器的豁免探测器、
        # 第五世界分类器逐行匹配 check 表格行、gate_selftest 的 expect_check）。
        # 要新增豁免，必须在这里显式改这个数——增长留在 diff 里，不会无声累积。
        "silentdeg": [S, "--max-exemptions", "5", *scan_targets],
        "ledger": [V, "--ledger", str(args.ledger), str(args.question)],
        "frozen": [V, "--ledger", str(args.ledger), str(args.goal)],
        "trace": [V, "--trace", f"goal={args.goal}", str(args.question)],
        "vocabulary": [V, "--vocabulary", str(args.goal), str(args.question)],
        # goal 冻结前的门：只查「跳过了看不出来」的那几步有没有做
        "goal_ready": [str(HERE / "check_goal_ready.py"), str(args.goal)],
        # exloop 独有的那条（第五世界的 hollow）不随库发布——它测的是那个仓库的脚本。
        # 用 --extra-gate 传入，**不在这里写死别的仓库的路径**。
        **({"extra": [str(args.extra_gate)]} if args.extra_gate else {}),
    }


# 供 gate_selftest.py 交叉核对用的种类清单，由上面那份唯一真源导出。
GATE_KINDS = list(_gates(
    argparse.Namespace(ledger="", question="", goal="", extra_gate=None), []))

# 明确豁免的 gate 种类，连同理由。豁免是**声明**出来的，不是默默漏掉。
EXEMPT = {
    "mutscan": "单次运行数分钟（要把被测脚本跑几十遍），且它是本里程碑的研究对象"
               "而非对文档的 gate；按需单独运行。",
    "script": "指验证脚本自身的 exit code，已由 ledger 的 all_passed 覆盖。",
}


def _run(name: str, argv: list[str]) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, *argv], cwd=ROOT, capture_output=True, text=True
    )
    tail = (proc.stdout or proc.stderr).strip().splitlines()
    print(f"[{'PASS' if proc.returncode == 0 else 'FAIL'}] {name:16s} "
          f"exit={proc.returncode}  {tail[-1][:90] if tail else ''}")
    return name, proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--goal", required=True, type=pathlib.Path)
    ap.add_argument("--question", required=True, type=pathlib.Path)
    ap.add_argument("--ledger", required=True, type=pathlib.Path)
    ap.add_argument("--extra-gate", type=pathlib.Path,
                    help="额外跑一个本仓之外的门（如 exloop 自己的 plan 脚本）——"
                         "**别的仓库的路径不写死在这里**")
    ap.add_argument(
        "--scan",
        nargs="*",
        default=["scripts", "packages"],
        help="静默退化扫描的目录（本仓相对路径）",
    )
    ap.add_argument(
        "--scan-external",
        nargs="*",
        default=["~/Projects/newlife/packages/newlife/src",
                 "~/Projects/newlife/packages/proofroot/src"],
        help=("仓外也要扫的源码根。**第十三个里程碑暴露的范围缺口**：扫描器一直只扫 exloop "
              "的验证脚本，而那处 silent_output 在 newlife 的 conform/ 里——"
              "工具够得着的范围本身就是一个洞。"),
    )
    args = ap.parse_args()

    scan_targets = [
        str(p) for d in args.scan for p in sorted((ROOT / d).glob("*.py"))
    ] + [
        str(p)
        for d in args.scan_external
        for p in sorted(pathlib.Path(d).expanduser().rglob("*.py"))
        if "__pycache__" not in str(p)
    ]
    gates = _gates(args, scan_targets)

    # 注册表即执行体，所以这条只可能因为「有人把 GATE_KINDS 改成别的来源」而失败
    assert list(gates) == GATE_KINDS, (
        f"注册表与执行体脱节：{list(gates)} != {GATE_KINDS}"
    )

    results = [_run(kind, argv) for kind, argv in gates.items()]
    failed = [name for name, code in results if code != 0]
    print()
    if failed:
        print(f"{len(failed)}/{len(results)} 个 gate 失败：{failed}")
        return 1
    print(f"全部 {len(results)} 个 gate 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
