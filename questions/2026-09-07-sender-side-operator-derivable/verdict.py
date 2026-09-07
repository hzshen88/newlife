"""sender side operator derivable — verdict runner.

The criteria are frozen in `prereg.md` (see its §2). **The verdict is a mechanical
conjunction of the units and is never written by hand.**

**This runner does not run any other question's runner** (registration F4). There are
exactly two safety lines: self-reproduction and an unchanged environment. Questions are
siblings, not a chain — rerunning someone else's old conclusion adds nothing to the
credibility of this one, and with fifty questions it entangles all of them.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from process_bigraph.processes.growth_division import Grow

import newlife.mechanisms.foreign_dfba.declaration as DFBA
import newlife.mechanisms.foreign_growth.declaration as GROW
import newlife.mechanisms.foreign_monod.declaration as MONOD
from newlife import provenance
from newlife.adapters.process_bigraph.derive import allocate_probe_core
from newlife.adapters.process_bigraph.foreign import resolve_foreign
from newlife.conform import yield_verdict as YV
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code

HERE = Path(__file__).resolve().parent
INNER = "_NEWLIFE_INNER_RUN"        # marks the inner reproduction run; stops infinite recursion

# ─────────────────────────────────────────────────────────────────────
# YOUR WORLD — 发送端算符的行为探针。
#
# 探针只看 `update` 的返回值随 interval 怎么变，**不读任何声明侧信息**（登记 F6）：
# 读了 `PortBinding.operation` 就等于把答案抄进来，S4 会变成恒真。
# ─────────────────────────────────────────────────────────────────────
DT1, DT2 = 0.5, 1.0
REL_EPS = 1e-6                      # 相对裕度低于此值即判 indeterminate，不猜
OPS = ("add", "set", "indeterminate", "AMBIGUOUS")   # 登记 F7：词表封闭，不许扩


class LevelGrow(Grow):
    """已知**绝对值**语义的对照物：同样的动力学，但返回新的绝对质量而非增量。

    S2 靠它和 `Grow`（已知增量语义）一起证明探针有分辨力——第十八个里程碑的
    `probe_selftest` 用 `SetFloat` / `PositiveFloat` 做同一件事。
    """

    def update(self, state, interval):
        return {"mass": state["mass"] + state["mass"] * self.config["rate"] * interval}


def classify(v1: float, v2: float, current: float) -> dict:
    """两点外推回 interval=0：趋近 0 是增量，趋近当前状态值是绝对值。

    **裕度不足时返回 `indeterminate` 而不是硬猜。** 第一版没有这一支，
    在一个状态全为 0 的端口上让 `a if x < y else b` 静默落进 else，
    于是「什么都没测到」被输出成一个确定的判定——一个永远不会红的分支。
    """
    v0 = v1 - (v2 - v1) / (DT2 - DT1) * DT1
    d_zero, d_state = abs(v0), abs(v0 - current)
    scale = max(abs(v0), abs(current), 1e-12)
    margin = abs(d_zero - d_state) / scale
    op = "indeterminate" if margin < REL_EPS else ("add" if d_zero < d_state else "set")
    return {"operation": op, "v0": v0, "state": current, "rel_margin": margin}


def _walk(roots, path):
    value = roots
    for segment in path:
        value = value[segment]
    return value


def probe_state_from(decl) -> tuple[dict, list[str]]:
    """按接线把 STATE_ROOTS 映射成 端口名 -> 值，返回 (状态, 合成过的端口)。

    接线有两种形态：端口 -> 路径，或 端口 -> 键到路径的映射（DFBA 的 substrates）。
    值为 None 的是占位（真实运行时由 build_composite 的参数覆盖），探针合成 1.0
    并把该端口记进第二个返回值——**产物里必须看得见哪些状态不是读来的**。
    """
    wiring = getattr(decl, "IN_WIRING", None) or decl.WIRING
    state: dict = {}
    synthesized: list[str] = []
    for port, path in wiring.items():
        if isinstance(path, dict):
            state[port] = {k: _walk(decl.STATE_ROOTS, p) for k, p in path.items()}
            continue
        value = _walk(decl.STATE_ROOTS, path)
        if value is None:
            value = 1.0
            synthesized.append(port)
        state[port] = dict(value) if isinstance(value, dict) else value
    return state, synthesized


def probe(cls, config: dict, core, state: dict) -> dict:
    """探一个 process 的每个输出端口。**每次全新实例**（登记 F5：避免探测污染）。"""
    seen: dict = {}
    for dt in (DT1, DT2):
        instance = cls(dict(config), core)
        seen[dt] = instance.update(
            {k: (dict(v) if isinstance(v, dict) else v) for k, v in state.items()}, dt
        )
    # **键一律排序输出。** 第三方 `update` 返回的 dict 键顺序逐进程不稳定，
    # 数值完全相同而字节不同，S0 因此为假——pilot 第一次跑就抓到了这个。
    result: dict = {}
    for port, first in sorted(seen[DT1].items()):
        second = seen[DT2][port]
        if isinstance(first, dict):
            per_key = {
                k: classify(float(first[k]), float(second[k]),
                            float(state.get(port, {}).get(k, 0.0)))
                for k in sorted(first)
            }
            # indeterminate 是弃权不是反对：只看有裕度的键有没有共识
            decided = {d["operation"] for d in per_key.values()
                       if d["operation"] != "indeterminate"}
            result[port] = {"per_key": per_key, "operation": (
                "indeterminate" if not decided
                else decided.pop() if len(decided) == 1 else "AMBIGUOUS")}
        else:
            result[port] = classify(float(first), float(second),
                                    float(state.get(port, 0.0)))
    return result


CASES = (
    ("Grow", GROW, {"rate": 0.1}),
    ("MonodKinetics", MONOD, YV._monod_config()),
    ("DynamicFBA", DFBA, YV._dfba_config(20.0)),
)


def probe_all(core) -> dict:
    """三个真实第三方 process 各探一次。声明侧信息只用于**事后比对**，不进探针。"""
    out: dict = {}
    for label, decl, config in CASES:
        state, synthesized = probe_state_from(decl)
        probed = probe(resolve_foreign(decl.FOREIGN), config, core, state)
        out[label] = {
            "probed": {port: probed[port]["operation"] for port in sorted(probed)},
            "hand_written": {b.port: b.operation for b in sorted(decl.BINDINGS,
                                                                 key=lambda b: b.port)},
            "synthesized_state_ports": synthesized,
            "detail": probed,
        }
    return out


# ─────────────────────────────────────────────────────────────────────
# CRITERIA. 每条都是纯谓词——这才让 runner 能用合成输入证明它会红（登记 F1）。
# ─────────────────────────────────────────────────────────────────────
def selftest_distinguishes(core) -> dict:
    """S2：已知增量的判 add、已知绝对值的判 set，且两者都要有裕度。"""
    out: dict = {}
    for label, cls, expected in (("Grow", Grow, "add"), ("LevelGrow", LevelGrow, "set")):
        got = probe(cls, {"rate": 0.1}, core, {"mass": 1.0})["mass"]
        out[label] = {"expected": expected, "got": got["operation"],
                      "rel_margin": got["rel_margin"],
                      "ok": got["operation"] == expected and got["rel_margin"] > REL_EPS}
    return out


def agrees_with_hand_written(probed_all: dict) -> dict:
    """S4：每个端口的探针判定与手写声明相同；indeterminate / AMBIGUOUS 一律算不通过。"""
    out: dict = {}
    for label, entry in probed_all.items():
        hand, probed = entry["hand_written"], entry["probed"]
        out[label] = {port: {"probed": probed.get(port), "hand_written": op,
                             "ok": probed.get(port) == op and op in ("add", "set")}
                      for port, op in sorted(hand.items())}
    return out


FLIP = {"add": "set", "set": "add"}


def negative_control(probed_all: dict) -> dict:
    """S5（冻结判据的字面实现）：把手写算符取反后，探针判定必须与之不符。"""
    out: dict = {}
    for label, entry in probed_all.items():
        probed = entry["probed"]
        out[label] = {
            port: {"flipped_declaration": FLIP[op], "probed": probed.get(port),
                   "caught": probed.get(port) != FLIP[op]}
            for port, op in sorted(entry["hand_written"].items()) if op in FLIP
        }
    return out


def s5_vacuity_diagnosis() -> dict:
    """**机械证明 S5 被 S4 逻辑蕴含**，因而判定力为零——由代码算，不由散文断言。

    穷举 (探针判定, 手写声明) 的每一种组合，找「S4 真而 S5 假」的反例。
    一个都找不到，就说明 S5 在 S4 成立时必真，不携带独立信息。

    根因是结构性的，记在这里供收尾引用：登记 F6 要求探针**不得读取声明**，
    所以声明的任何改动都影响不到探针的输出——「取反声明」这种负控对它无效。
    **真正的负控必须改变被探对象的行为**（例如把 process 包一层使其返回绝对值，
    S2 的 `LevelGrow` 正是这么做的），而不是改变声明。
    """
    counterexamples = [
        {"probed": probed, "hand_written": hand}
        for probed in OPS
        for hand in ("add", "set")
        if (probed == hand) and not (probed != FLIP[hand])
    ]
    return {
        "claim": "S5 is implied by S4; it cannot go red unless S4 is already red",
        "search_space": {"probed": list(OPS), "hand_written": ["add", "set"]},
        "counterexamples_where_s4_true_and_s5_false": counterexamples,
        "implied_by_s4": not counterexamples,
    }


def s5_can_go_red() -> bool:
    """S5 能不能红——在 S4 为真的前提下。**返回 False 就是 F1 被违反的证据。**"""
    return not s5_vacuity_diagnosis()["implied_by_s4"]


def criteria_can_fail() -> dict:
    """**F1：每条判据都要能红。** 用合成输入在运行时证明，不靠散文断言。

    三个合成场景直接打在 `classify` 上——它是 S2 与 S4 共同的判定核心。
    """
    delta_like = classify(0.05, 0.10, 1.0)      # 正比于 interval
    level_like = classify(1.05, 1.10, 1.0)      # 几乎不随 interval 变
    flat_zero = classify(0.0, 0.0, 0.0)         # 什么都没测到
    return {
        "classify 对增量样本不返回 set": delta_like["operation"] == "add",
        "classify 对绝对值样本不返回 add": level_like["operation"] == "set",
        "classify 在零裕度时拒绝给答案": flat_zero["operation"] == "indeterminate",
        "S4 谓词对不一致的输入为假": agrees_with_hand_written(
            {"synthetic": {"probed": {"p": "set"}, "hand_written": {"p": "add"}}}
        )["synthetic"]["p"]["ok"] is False,
        # **这一项会返回 False，而且是刻意让它返回 False 的。** S5 被 S4 逻辑蕴含，
        # 永远不会红；F1 要求每条判据都能红，所以 S3 必须因此为假。
        # 判据已冻结不得修改（登记的规矩），正确处置是让判定体系自己抓住它、
        # 在产物里输出分类，而不是回头把 S5 改成能红的样子。
        "S5 能红（恒真则为假）": s5_can_go_red(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    core = allocate_probe_core("process_bigraph:register_types")
    probed_all = probe_all(core)
    selftest = selftest_distinguishes(core)
    agreement = agrees_with_hand_written(probed_all)

    can_fail = criteria_can_fail()
    # S1: the packages installed *now* are exactly the ones `env.lock` recorded at the
    # freeze. **The first version of this line compared the file's digest with a digest of
    # the same file taken a moment earlier — true by construction, and it shipped in every
    # early question.** `newlife freeze` rewrites env.lock from the live environment and
    # pins its hash into the registration; `newlife audit` proves the file never changed
    # afterwards; this line proves the run happened in that environment.
    s1 = provenance.env_text() == (HERE / "env.lock").read_text(encoding="utf-8")
    s2 = all(entry["ok"] for entry in selftest.values())
    s4 = all(port["ok"] for case in agreement.values() for port in case.values())
    negative = negative_control(probed_all)
    s5 = all(port["caught"] for case in negative.values() for port in case.values())
    # **"the criteria can fail" is its own visible slot in the conjunction, not a
    # detail nested inside another unit.** The first version folded it into a sub-field
    # of S2, so the registration read S0∧S1∧S2∧S3 while the code computed three —
    # the unit-alignment check in `newlife run` caught exactly this the first time it
    # ran against a real question folder.
    units = {"S1_env_unchanged": {"passed": s1},
             "S2_probe_distinguishes": {"passed": s2, "selftest": selftest},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail},
             "S4_probe_matches_hand_written": {"passed": s4, "agreement": agreement},
             # S5 照冻结的字面实现，同时把它恒真这件事作为分类输出在旁边——
             # 冻结的判据不许为了让它变绿而修改。
             "S5_negative_control": {"passed": s5, "per_case": negative,
                                     "vacuity_diagnosis": s5_vacuity_diagnosis()}}

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-07-sender-side-operator-derivable.v1", "provenance": prov,
               "probe": {"dt_pair": [DT1, DT2], "rel_eps": REL_EPS, "vocabulary": list(OPS)},
               "probed": probed_all, "units": units}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # **The key name says "S0 not counted yet".** S0 cannot be written into the file it
    # reproduces — doing so would make the two runs differ by construction — so the final
    # verdict can only live in reproduction.json. Calling this one `verdict` too would
    # make the artifact show H1 while S0 was false: **one layer passing itself off as the
    # whole conjunction.**
    summary, _ = emit(verdict, summary,
                      RenderSpec(verdict_key="verdict_before_reproduction"), args.out)

    if os.environ.get(INNER):
        return exit_code(verdict)

    # ── S0: run this file again in a separate process, compare bytes ────────────
    # **The record goes in a different file.** Written into summary.json itself, the two
    # runs would necessarily differ and "byte-identical" could never hold — the record of
    # a reproduction cannot live inside the artifact being reproduced.
    probe = args.out.parent / ".reproduction-probe.json"   # beside --out: a pilot never touches results/
    subprocess.run([sys.executable, __file__, "--out", str(probe)],
                   env={**os.environ, INNER: "1"}, capture_output=True, check=False)
    s0 = probe.exists() and probe.read_bytes() == args.out.read_bytes()
    probe.unlink(missing_ok=True)
    final = verdict if s0 else "INVALID"     # S0 false = this run had no discriminating power
    (args.out.parent / "reproduction.json").write_text(json.dumps(
        {"schema": "self-reproduction.v1", "S0_byte_identical_on_rerun": s0,
         "verdict": final, "verdict_before_reproduction": verdict,
         "of": args.out.name, "sha256": provenance.file_digest(args.out)},
        indent=2, ensure_ascii=False) + "\n")

    for name, unit in units.items():
        print(f"  {name:34s} {unit['passed']}")
    print(f"  {'S0_byte_identical_on_rerun':34s} {s0}")
    # A pilot prints the same conjunction, but must never look like a verdict on screen.
    label = ("PILOT (exploratory, no evidential weight)" if os.environ.get("NEWLIFE_PILOT")
             else "verdict")
    print(f"\n{label}: {final}"
          + ("" if s0 else "   <- the two runs disagreed; this run has no power"))
    return exit_code(final)


if __name__ == "__main__":
    raise SystemExit(main())
