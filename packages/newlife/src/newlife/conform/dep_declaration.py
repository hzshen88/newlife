"""非 Python 依赖的声明，与「缺了会不会静默」的实测。

判据冻结于 exloop 的预注册（freeze commit `6c94455`）。

`pyproject.toml` 停在语言边界上——文献原话：*uv / Bun / Deno 这类工具不定义编译器、
头文件、C 库，构建与运行时的可复现性到项目边界为止*。本模块把边界之外的东西声明出来，
并测**缺一条时的失败方式**：

| 结果 | 合格 |
|---|---|
| `hard_fail_named` 无产物且报错指名该依赖 | ✓ |
| `hard_fail_unnamed` 无产物但不指名 | ✗ 读的人不知道缺什么 |
| `silent_output` **产出了 summary** | ✗✗ 最危险——跑出来了，结果可能是错的 |
| `unaffected` 该 runner 用不到它 | 记「无害」，不计入 H0 |

**`unaffected` 与 `silent_output` 的区别是核心**：前者是「用不到」，后者是
「用得到却装作没事」。混了即 IC-2。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[5]
CONFORM = "packages/newlife/src/newlife/conform"

# --- 预注册 §2.1 的穷举结果，不得增删 ---
DECLARED: dict[str, dict] = {
    "cc": {
        "why": "编译 ms 的 C 源码",
        "sites": ["mechanisms/second_world/ms_binary.py:19"],
        "affects": ["second"],
    },
    "git": {
        "why": "记录分析代码的 commit / 取基线与依赖变动",
        "sites": [f"{CONFORM}/verdict.py:315", f"{CONFORM}/eighth_world_verdict.py",
                  f"{CONFORM}/verdict_rot.py",
                  f"{CONFORM}/cross_runtime_verdict.py:70"],
        "affects": ["eighth", "fourteenth"],
    },
}
# 对照组：用不到这两条的 runner，用来确认 `unaffected` 分类真的会出现
CONTROL = {"third": ["cc", "git"]}

INVOKE = {
    "second": ["conform/second_world_verdict.py", "--output", "{out}"],
    "third": ["conform/third_world_verdict.py", "--out", "{out}/summary.json"],
    "eighth": ["conform/eighth_world_verdict.py", "--out", "{out}/summary.json"],
}


def masked_env(dep: str) -> tuple[dict, pathlib.Path]:
    """PATH 换成只含一个空目录。**不删系统文件**（预注册 §2.3）。"""
    empty = pathlib.Path(tempfile.mkdtemp(prefix=f"_mask_{dep}_"))
    env = dict(os.environ)
    env["PATH"] = str(empty)
    return env, empty


def confirm_masked(dep: str, env: dict) -> bool:
    """屏蔽后必须先确认它真的不可用，确认不了即 IC-1。"""
    return shutil.which(dep, path=env["PATH"]) is None


def classify(dep: str, world: str) -> dict:
    env, _empty = masked_env(dep)
    if not confirm_masked(dep, env):
        return {"state": "IC-1", "detail": f"屏蔽后仍能找到 {dep}——屏蔽无效"}
    out = pathlib.Path(tempfile.mkdtemp(prefix=f"_run_{world}_"))
    argv = [a.replace("{out}", str(out)) for a in INVOKE[world]]
    proc = subprocess.run(
        [sys.executable, str(REPO / "packages/newlife/src/newlife" / argv[0]), *argv[1:]],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=900,
    )
    produced = (out / "summary.json").exists()
    text = proc.stdout + proc.stderr
    named = dep in text
    if produced:
        state = "silent_output"
    elif named:
        state = "hard_fail_named"
    else:
        state = "hard_fail_unnamed"
    return {"state": state, "exit": proc.returncode, "produced_summary": produced,
            "names_dependency": named, "evidence": text.strip().splitlines()[-1][:120]
            if text.strip() else ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    results: dict[str, dict] = {}
    for dep, meta in DECLARED.items():
        for world in meta["affects"]:
            results[f"{dep}/{world}"] = {**classify(dep, world), "kind": "affected"}
    for world, deps in CONTROL.items():
        for dep in deps:
            r = classify(dep, world)
            # 对照组产出 summary = `unaffected`，不是 `silent_output`
            if r["state"] == "silent_output":
                r["state"] = "unaffected"
            results[f"{dep}/{world}"] = {**r, "kind": "control"}

    affected = {k: v for k, v in results.items() if v["kind"] == "affected"}
    ics = [k for k, v in results.items() if v["state"] == "IC-1"]
    bad = {k: v["state"] for k, v in affected.items()
           if v["state"] in ("hard_fail_unnamed", "silent_output")}
    h1 = not ics and not bad and bool(affected)

    summary = {
        "schema": "newlife.thirteenth.verdict.v1",
        "prereg_freeze_commit": "6c94455",
        "declared_non_python_dependencies": DECLARED,
        "enumeration_boundary": ("已知会被执行的路径上的依赖。声明的是「已知需要什么」，"
                                 "不是「只需要这些」"),
        "results": results,
        "failures": bad,
        "invalid_conditions": ics,
        "invalid": bool(ics),
        "verdict": "INVALID" if ics else ("H1" if h1 else "H0"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")
    for k, v in results.items():
        print(f"  {k:14s} {v['state']:18s} {'[对照]' if v['kind']=='control' else ''} {v.get('evidence','')[:60]}")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
