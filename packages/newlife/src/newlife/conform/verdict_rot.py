"""重跑八个旧 verdict，按冻结的四态词表分类。

判据冻结于 exloop 的预注册（freeze commit `3a2ca54`）。

**测的是「当下有效性」，不是「归档复现」**（design §1）：
归档复现是 `git checkout <冻结 commit>` + 冻结种子，那个**能**保障；
本模块问的是**今天的代码是否仍满足当时的判据**——那个不能，也不该保障。

**四态，不得扩充**：

- `reproduced`   —— 重跑产物与冻结产物**逐字节相同**
- `value_changed`—— 跑得通、产物不同，但判据仍能被评估。**答案变了**
- `unevaluable`  —— 判据引用的对象已不存在。**问题没了**
- `unrunnable`   —— 进程非正常结束、缺外部输入或超时。**不计入 H0**

`value_changed` 与 `unevaluable` 混淆即 IC-2——前者是正常的科学演化，后者是故障。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[5]
CONFORM = "packages/newlife/src/newlife/conform"
EXLOOP = pathlib.Path.home() / "Projects/exloop/docs/science-superpowers"

# (runner, 冻结产物, 额外参数构造器)。--out/--output 由本模块统一接管。
TARGETS: dict[str, tuple[str, str, list[str]]] = {
    "second":  ("second_world_verdict.py",  "results/second-world/summary.json",  []),
    "third":   ("third_world_verdict.py",   "results/third-world/summary.json",   []),
    "fourth":  ("fourth_world_verdict.py",  "results/fourth-world/summary.json",  []),
    "fifth":   ("fifth_world_verdict.py",   "results/fifth-world/summary.json",
                ["--classification", str(EXLOOP / "plans/verification/w5-classification-final.json")]),
    "sixth":   ("sixth_world_verdict.py",   "results/sixth-world/summary.json",   []),
    "seventh": ("seventh_world_verdict.py", "results/seventh-world/summary.json",
                ["--classification", "results/seventh-world/classification.json"]),
    "eighth":  ("eighth_world_verdict.py",  "results/eighth-world/summary.json",  []),
    "ninth":   ("ninth_world_verdict.py",   "results/ninth-world/summary.json",   []),
}
KNOWN_BROKEN = "seventh"           # 预注册 §2.3：已知坏的不计入 H0
TIMEOUT = 2400


def sha(p: pathlib.Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def classify(name: str, proc, produced: pathlib.Path, frozen: pathlib.Path) -> dict:
    """四态分类。`unevaluable` 的判据是**产物里的 verdict 变成了 INVALID**
    ——那正是「判据引用的对象已不存在」在本项目里的表现形式（第十个里程碑实测）。"""
    blob = (proc.stdout or "") + (proc.stderr or "")
    if not produced.exists():
        return {"state": "unrunnable", "why": f"未产出产物；exit={proc.returncode}",
                "tail": blob.strip().splitlines()[-1][:120] if blob.strip() else ""}
    new, old = sha(produced), sha(frozen)
    if old is None:
        return {"state": "unrunnable", "why": "冻结产物不存在，无从比对"}
    if new == old:
        return {"state": "reproduced", "sha256": new}
    try:
        doc = json.loads(produced.read_text())
    except json.JSONDecodeError:
        return {"state": "unrunnable", "why": "产物不是合法 JSON"}
    if doc.get("verdict") == "INVALID" or doc.get("invalid") is True:
        return {"state": "unevaluable", "why": "重跑后判定为 INVALID——判据引用的对象已不存在",
                "frozen_sha256": old, "rerun_sha256": new}
    return {"state": "value_changed", "why": "跑得通、判据仍可评估，但产物不同",
            "frozen_sha256": old, "rerun_sha256": new}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    names = args.only or list(TARGETS)

    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            runner, frozen_rel, extra = TARGETS[name]
            outdir = pathlib.Path(tmp) / name
            outdir.mkdir(parents=True, exist_ok=True)
            if name == "second":
                produced = outdir / "summary.json"
                cmd = [sys.executable, f"{CONFORM}/{runner}", "--output", str(outdir)]
            else:
                produced = outdir / "summary.json"
                cmd = [sys.executable, f"{CONFORM}/{runner}", *extra, "--out", str(produced)]
            try:
                proc = subprocess.run(cmd, cwd=REPO, capture_output=True,
                                      text=True, timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                results[name] = {"state": "unrunnable", "why": f"超过 {TIMEOUT}s"}
                print(f"  {name:8s} unrunnable  超时"); continue
            info = classify(name, proc, produced, REPO / frozen_rel)
            info["exit"] = proc.returncode
            results[name] = info
            print(f"  {name:8s} {info['state']:14s} {info.get('why','')[:56]}")

    judged = {k: v for k, v in results.items() if k != KNOWN_BROKEN}
    reproduced = [k for k, v in judged.items() if v["state"] == "reproduced"]
    broken = [k for k, v in judged.items() if v["state"] in ("value_changed", "unevaluable")]
    unrunnable = [k for k, v in judged.items() if v["state"] == "unrunnable"]
    h1 = not broken and not unrunnable and len(reproduced) == len(judged)
    h0 = bool(broken)

    summary = {
        "schema": "newlife.eleventh.verdict.v1",
        "prereg_freeze_commit": "3a2ca54",
        "known_broken_excluded": KNOWN_BROKEN,
        "per_runner": results,
        "reproduced": sorted(reproduced),
        "broken": sorted(broken),
        "unrunnable": sorted(unrunnable),
        "verdict": "H1" if h1 else ("H0" if h0 else "INVALID"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"\nsummary written: {args.out}")
    print(f"  复现 {len(reproduced)} · 坏 {len(broken)} · 跑不了 {len(unrunnable)}"
          f"（已知坏的 {KNOWN_BROKEN} 不计）")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
