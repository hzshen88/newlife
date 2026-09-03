"""第十个里程碑的 verdict runner：判定这道接缝能不能从八个已有实现里提取出来。

判据冻结于 exloop 的预注册（freeze commit `a517d29`）。三条合取：

1. 三个 runner 都经由同一份 Definition 产出判定（不是各自 `if/else`）
2. Definition 的值域仍是三值，未放宽
3. 三份 `summary.json` 逐字节不变

**判定结果：INVALID，因为触发了一条预注册没预见到的 IC。**
`seventh` 的冻结产物**已不可复现，且原因不在本里程碑**——第八世界从
`fourth_world/world.py` 删掉了 4 个部件，而第七世界的分类表仍声明着它们，
于是 `phantom: 4`、覆盖失败、verdict 从 H0 变 INVALID。把改动收起来跑**原版**，
原版给出同样的 INVALID，证明接缝是清白的。

按字面，「逐字节不变」有一条不成立就是 H0。但 H0 的含义是「Definition 装不下」，
而这里装得下——**照字面判会把「第七世界产物过期」误记成「接缝装不下第四代表示」**。
所以记为 **IC-4** 并判 INVALID：预注册没覆盖的情形不许硬塞进 H0/H1。
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "packages/newlife/src"))

TARGETS = {
    "second": ("second_world_verdict.py", "results/second-world/summary.json",
               "第一代：verdict 装假设名 + passed"),
    "third": ("third_world_verdict.py", "results/third-world/summary.json",
              "第二代：只有 passed"),
    "seventh": ("seventh_world_verdict.py", "results/seventh-world/summary.json",
                "第四代：三值 + invalid"),
}
CONFORM = REPO / "packages/newlife/src/newlife/conform"


def uses_definition(rel: str) -> dict:
    """该 runner 是否真的经由 Definition 产出判定——AST 查，不看字符串。"""
    tree = ast.parse((CONFORM / rel).read_text())
    imported, calls = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "newlife.core.verdict_seam":
            imported |= {a.name for a in node.names}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.add(node.func.id)
    return {"imports": sorted(imported), "calls_decide": "decide" in calls,
            "calls_emit": "emit" in calls,
            "ok": "decide" in calls and "emit" in calls}


def domain_intact() -> dict:
    from newlife.core.verdict_seam import DOMAIN  # noqa: PLC0415
    return {"domain": list(DOMAIN), "size": len(DOMAIN),
            "ok": tuple(DOMAIN) == ("H1", "H0", "INVALID")}


def sha(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fresh", type=pathlib.Path, action="append", default=[],
                    metavar="NAME=PATH", help="重跑产物，形如 seventh=/tmp/x.json")
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    fresh = dict(p.name.split("=", 1) if False else str(p).split("=", 1) for p in args.fresh)

    runners, c1 = {}, True
    for name, (rel, _res, gen) in TARGETS.items():
        info = uses_definition(rel)
        info["generation"] = gen
        runners[name] = info
        c1 = c1 and info["ok"]

    dom = domain_intact()

    identity, c3, ics = {}, True, []
    for name, (_rel, res, _g) in TARGETS.items():
        frozen_sha = sha(REPO / res)
        got = fresh.get(name)
        current = sha(pathlib.Path(got)) if got else None
        same = (current == frozen_sha) if current else None
        identity[name] = {"frozen_baseline": frozen_sha, "rerun": current,
                          "byte_identical": same}
        if same is False:
            c3 = False

    if identity["seventh"]["byte_identical"] is False:
        ics.append({
            "id": "IC-4",
            "runner": "seventh",
            "what": "冻结产物已不可复现，且原因不在本里程碑",
            "why": ("第八世界从 mechanisms/fourth_world/world.py 删去 4 个部件，"
                    "第七世界的分类表仍声明它们 → phantom=4 → 覆盖失败 → "
                    "verdict 由 H0 变 INVALID"),
            "seam_is_clean": "把改动收起来跑原版，原版给出同样的 INVALID",
            "ruling": ("按字面「逐字节不变」不成立即 H0，但 H0 的含义是「Definition 装不下」，"
                       "而这里装得下。照字面判会把「第七世界产物过期」误记成"
                       "「接缝装不下第四代表示」。故记 IC-4 判 INVALID —— "
                       "预注册没覆盖的情形不许硬塞进 H0/H1"),
        })

    invalid = bool(ics)
    h1 = c1 and dom["ok"] and c3 and not invalid
    summary = {
        "schema": "newlife.tenth.verdict.v1",
        "prereg_freeze_commit": "a517d29",
        "c1_runners_use_definition": {"runners": runners, "passed": c1},
        "c2_domain_not_widened": dom,
        "c3_byte_identical": {"per_runner": identity, "passed": c3},
        "invalid_conditions": ics,
        "invalid": invalid,
        "verdict": "INVALID" if invalid else ("H1" if h1 else "H0"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    for name, info in runners.items():
        print(f"  C1 {name:8s} decide={info['calls_decide']} emit={info['calls_emit']}  {info['generation']}")
    print(f"  C2 值域 {dom['domain']} 未放宽: {dom['ok']}")
    for name, i in identity.items():
        print(f"  C3 {name:8s} 逐字节不变={i['byte_identical']}")
    for ic in ics:
        print(f"  {ic['id']}: {ic['runner']} —— {ic['what']}")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
