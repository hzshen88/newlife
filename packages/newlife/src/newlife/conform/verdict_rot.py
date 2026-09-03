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
"""**处置已作出（2026-09-03），不是待办。**

`seventh` 的状态是 `unevaluable`——**不是「H0 判错了」**。它的判定写于 `7e3b7a5`；
`6bbc05c`（第八个里程碑）删掉了它声明表里的 4 个部件（`MoranGenealogyWorld.*`），
于是重跑触发「声明幽灵部件 → INVALID」——那正是原判定 §5 自己测过的负控。

**H0 保留。** 4 个 `unclassified` 全在 `mechanisms/resource_foraging/world.py`，
第八个里程碑没碰；被删的 4 个当初归类是 `simulator`×3 + `frame`×1。稳健性探测
（去掉已不存在的部件后重跑）仍是 H0，同样那 4 个。用 `7e3b7a5` 当时的 runner 跑
今天的代码，结果与新 runner 逐项一致——第十个里程碑的接缝改动被排除。

完整理由见 `docs/worlds/007-harness-generability.md` §6。**不要为了让它变绿而编辑
`results/seventh-world/classification.json`**：预注册 §3.3 明写归类不预先冻结，
它是那一次判定的声明快照，改它就是另做一次实验。
"""
TIMEOUT = 2400


# ── 产物的代码依赖：谁的 summary 由哪些路径决定 ───────────────────────────────
#
# **这是第十一个里程碑之后补的**，起因是一个被误诊的现象：`seventh` 的 verdict 坏了，
# 我最初记成「判据过期」。真实原因是——
#
#   一次改动只被要求保住**它自己那个世界**的产物。第八个里程碑大改了
#   `mechanisms/fourth_world/world.py`，它自己的判据 C3 要求 `fourth-world/summary.json`
#   逐字节不变，也确实做到了；但 `seventh-world/summary.json` **也**依赖那个文件，
#   而没有任何东西要求第八个里程碑保住它。
#
# **依赖是隐式的，所以没人知道还该检查谁。** 声明出来之后，「改了 X 就要重跑依赖 X 的
# 全部 verdict」才成为一条可执行的规则。
#
# 「代码变了旧 verdict 就不再描述它」**不是故障**（用户 2026-09-03 指出，此前我把它
# 当成了需求）。真需求只有一条：**依赖未变时必须逐字节复现**——那是确定性回归检测。
DEPENDS_ON: dict[str, tuple[str, ...]] = {
    "second":  ("mechanisms/second_world/",),
    "third":   ("mechanisms/third_world/",),
    "fourth":  ("mechanisms/fourth_world/", "mechanisms/second_world/mechanisms.py",
                "core/harness.py", "core/runtime.py",
                  "adapters/reference_kernel/world_runtime.py"),
    "fifth":   ("conform/fifth_world_verdict.py",),
    "sixth":   ("conform/sixth_world_verdict.py",),
    # 第七世界枚举四个世界的 harness 文件——依赖面最宽，也正是它被撞坏的原因
    "seventh": ("conform/seventh_world_verdict.py", "mechanisms/resource_foraging/world.py",
                "mechanisms/resource_foraging/assay.py", "mechanisms/second_world/world.py",
                "mechanisms/fourth_world/world.py"),
    "eighth":  ("conform/eighth_world_verdict.py", "mechanisms/fourth_world/",
                "core/harness.py", "core/runtime.py",
                  "adapters/reference_kernel/world_runtime.py"),
    "ninth":   ("conform/ninth_world_verdict.py", "mechanisms/resource_foraging/"),
    # 第十 / 十一 / 十二 / 十三个当时**漏登记**了（2026-09-03 由 scripts/check_record.py
    # 对账查出：4 个产物没有依赖面，改它们的代码不会被提示要重跑——**腐烂检测器
    # 自己有覆盖洞，而当时没有任何东西检查它的覆盖率**）。依赖面按各自 runner 的
    # 真实读取范围补，不是补一个占位。
    "tenth":   ("conform/tenth_verdict.py", "core/verdict_seam.py", "conform/"),
    "eleventh": ("conform/verdict_rot.py",),
    # 第十二个在**只装 pyproject.toml 声明依赖**的全新 venv 里重放了五个判定，
    # 所以它的依赖面是**打包声明**，不是某个 src 文件。
    "twelfth": ("packages/newlife/pyproject.toml", "uv.lock"),
    "thirteenth": ("conform/dep_declaration.py", "mechanisms/second_world/ms_binary.py",
                   "conform/second_world_verdict.py", "conform/third_world_verdict.py",
                   "conform/eighth_world_verdict.py"),
    # 第十四个横跨两个运行时：改任一侧都要重跑
    "fourteenth": ("conform/cross_runtime_verdict.py", "core/harness.py", "core/runtime.py",
                   "adapters/process_bigraph/world_runtime.py",
                   "adapters/process_bigraph/lowering.py",
                   "adapters/reference_kernel/world_runtime.py",
                   "mechanisms/fourth_world/"),
    # 第十五个接的是 vendor 代码：改降级表或代写声明都要重跑
    "fifteenth": ("conform/foreign_process_verdict.py",
                  "adapters/process_bigraph/foreign.py",
                  "adapters/process_bigraph/bare_control.py",
                  "adapters/process_bigraph/lowering.py",
                  "mechanisms/foreign_growth/"),
    # 第十六个接的是独立发行的第三方包：降级表与代写声明都在依赖面上
    "sixteenth": ("conform/external_package_verdict.py",
                  "adapters/process_bigraph/foreign.py",
                  "adapters/process_bigraph/bare_control.py",
                  "adapters/process_bigraph/lowering.py",
                  "mechanisms/foreign_monod/"),
    # 第十七个背后是 LP 求解器：接线表、降级表、代写声明都在依赖面上
    "seventeenth": ("conform/solver_backed_verdict.py",
                    "adapters/process_bigraph/foreign.py",
                    "adapters/process_bigraph/bare_control.py",
                    "adapters/process_bigraph/lowering.py",
                    "mechanisms/foreign_dfba/"),
    # 第十八个推导权限声明：动推导器或三份手写声明都要重跑
    "eighteenth": ("conform/derive_authority_verdict.py",
                   "adapters/process_bigraph/derive.py",
                   "mechanisms/foreign_growth/", "mechanisms/foreign_monod/",
                   "mechanisms/foreign_dfba/"),
}
SRC_PREFIX = "packages/newlife/src/newlife/"


def impacted_by(paths: list[str]) -> dict[str, list[str]]:
    """改了这些路径，哪些 verdict 的产物必须被保住（或重跑）。

    **这是第八个里程碑漏掉的那一步。** 它改了 `mechanisms/fourth_world/world.py`，
    自己的判据 C3 要求 `fourth-world/summary.json` 逐字节不变——做到了；
    但 `seventh-world/summary.json` **也**依赖那个文件，而**没人算过这个集合**，
    于是它被撞坏而无人知晓。

    用法：改动前跑一次，把返回的世界全部列进本次里程碑的「逐字节不变」判据。
    """
    hit: dict[str, list[str]] = {}
    for world, deps in DEPENDS_ON.items():
        for dep in deps:
            for path in paths:
                rel = path.split(SRC_PREFIX, 1)[-1]
                if rel.startswith(dep) or dep.startswith(rel):
                    hit.setdefault(world, []).append(dep)
    return hit


def summary_path(world: str) -> str:
    """该 verdict 的产物路径。**目录命名不统一**：前九个里程碑是 `<name>-world/`，
    第十个起是 `<name>/`。两个都试，**都不存在就硬失败**——不许猜一个继续。

    这个 bug 由第七世界的腐烂处置顺带查出：`fourteenth` / `fifteenth` 在陈旧扫描里
    硬失败，说明它们的产物一直不在 `verdict_commit` 的视野里。**硬失败救了它**——
    若当初写成「找不到就当没变动」，这两个世界会永远显示「无变动」。
    """
    for candidate in (f"results/{world}-world/summary.json", f"results/{world}/summary.json"):
        if (REPO / candidate).exists():
            return candidate
    raise SystemExit(f"{world}: 两种命名下都找不到 summary 产物，不许猜")


def verdict_commit(world: str) -> str:
    """产出该 verdict 的**本仓** commit——即最后一次写它 summary 的那次提交。

    **不能用预注册的冻结 commit**：那个 commit 在 exloop，在 newlife 里解析不了。
    这个坑第八个里程碑踩过（IC-1）、写进了 skill，**然后我又踩了一次**——所以这里
    不只是修，还要硬失败：解析不出就抛，不许退回「没有变动」。
    """
    import subprocess  # noqa: PLC0415

    out = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", summary_path(world)],
        cwd=REPO, capture_output=True, text=True,
    )
    rev = out.stdout.strip()
    if out.returncode != 0 or not rev:
        raise SystemExit(
            f"{world}: 找不到产出它 summary 的本仓 commit——不许当成「没有变动」继续"
        )
    return rev


def dependencies_changed(world: str) -> list[str]:
    """自该 verdict 产出以来，它声明的依赖里哪些动过。空 = 必须逐字节复现。

    **解析失败一律硬失败**，不退回「没变」——那正是让我误诊 `seventh` 的那个形状。
    """
    import subprocess  # noqa: PLC0415

    since = verdict_commit(world)
    changed = []
    for rel in DEPENDS_ON.get(world, ()):
        out = subprocess.run(
            ["git", "log", "--oneline", f"{since}..HEAD", "--", SRC_PREFIX + rel],
            cwd=REPO, capture_output=True, text=True,
        )
        if out.returncode != 0:
            raise SystemExit(
                f"{world}: 解析 {since[:8]}..HEAD 失败（{out.stderr.strip()[:60]}）"
                "——硬失败，不猜"
            )
        if out.stdout.strip():
            changed.append(rel)
    return changed


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
