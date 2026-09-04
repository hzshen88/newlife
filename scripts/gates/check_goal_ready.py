#!/usr/bin/env python3
"""goal 冻结前的门：检查「跳过了看不出来」的那几步有没有做。

**只查有没有做，不查做得对不对。** 判断仍然是人的（L3 不让渡），但「有没有做」
必须是机械的——否则就是这次踩到的那个坑：skill 里写了「对通过 gate 的假设做文献检索」，
执行时三次抓取全部 ECONNRESET，于是跳过继续，**下游没有任何东西发现**。

那和 `re.search` 匹配不上就返回默认值是同一个形状：**尝试失败 → 静默取默认 →
看起来一切正常**。代码那一侧已经有 `silent_degradation_scan` 挡着；这是流程那一侧。

选择规则（不是什么都要 gate）：**只 gate「跳过之后无痕」的步骤。**
跑 verdict runner 跳过了会没有 summary.json，看得见，不用管；文献检索跳过了什么都不会少，
必须管。

三个必填锚：

    <!--@evidence: literature_searched=yes, sources=3, verdict=未知-->
    <!--@counterparty: 会有人押反面，理由是 ...-->
    <!--@size_estimate: impl_lines=200, criteria=2, failure_modes=1-->

**失败必须留痕，不许静默跳过。** 真的做不了，就显式豁免并写理由：

    <!--@evidence: literature_searched=no, reason=..., waived_by=人-->

**`failure_modes` 必须是 1。** 一个里程碑只应该有一个可判定的失败方式；会想在世界文档里
分开报告的失败 A 和失败 B，就是两个里程碑。确实要多于 1，显式写 `split_waived=<理由>`。
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ANCHOR = re.compile(r"<!--@([A-Za-z0-9_.\-]+):\s*([^>]*?)-->")
PLACEHOLDERS = {"", "TODO", "TBD", "待填", "...", "…", "PENDING"}


def parse(text: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for m in ANCHOR.finditer(text):
        fields: dict[str, str] = {}
        for kv in m.group(2).split(","):
            if "=" in kv:
                k, _, v = kv.partition("=")
                fields[k.strip()] = v.strip()
        if fields:
            out.setdefault(m.group(1), {}).update(fields)
        else:
            out.setdefault(m.group(1), {})["_text"] = m.group(2).strip()
    return out


def check(path: pathlib.Path) -> list[str]:
    text = path.read_text()
    a = parse(text)
    problems: list[str] = []

    if "goal_gate" in a and a["goal_gate"].get("_text", "").startswith("not_applicable"):
        return []                                    # 显式豁免，理由写在锚里

    ev = a.get("evidence")
    if ev is None:
        problems.append("缺 @evidence —— 文献检索做没做，跳过了看不出来，必须留痕")
    elif ev.get("literature_searched") == "no":
        if not ev.get("reason") or not ev.get("waived_by"):
            problems.append("@evidence 声明未做检索，但没写 reason= 与 waived_by= "
                            "——「明确豁免」可以，「悄悄没做」不行")
    elif ev.get("literature_searched") != "yes":
        problems.append("@evidence 的 literature_searched 必须是 yes 或 no")
    elif not ev.get("sources") or not ev.get("verdict"):
        problems.append("@evidence 说做了检索，但没写 sources= 与 verdict=（已知/未知）")

    cp = a.get("counterparty")
    if cp is None:
        problems.append("缺 @counterparty —— 说不出谁会押反面，就说明结果在预期之内、"
                        "信息量为零（七个 H1 零个 H0 的根子在这里）")
    else:
        body = cp.get("_text", "") or ",".join(f"{k}={v}" for k, v in cp.items())
        if body.strip() in PLACEHOLDERS or len(body.strip()) < 15:
            problems.append(f"@counterparty 内容太短或是占位符：{body!r}"
                            "——必须写出对方会拿什么理由押反面")

    # --- decidable-question skill 的三个锚（2026-09-04 起）---
    #
    # **早于本日期的已冻结 goal 没有这三个锚，会红——这是对的，不要回溯补。**
    # 冻结文档不许事后编辑；它们红，恰好如实反映「当时没有这道门」。
    # 这道门是给**新** goal 用的。
    # --- decidable-question skill 的三个锚 ---
    # 都属于「跳过之后看不出来」那一类：不填，goal 照样写得出来、下游照样跑得动、
    # verdict 照样能出——而问题可能根本不该问。**只 gate 这一类。**
    dec = a.get("decides")
    if dec is None:
        problems.append("缺 @decides —— 答案由设计决定还是由运行决定？"
                        "不分清就会把工具问题当成关于世界的结论")
    elif a["decides"].get("_text", "").strip() not in {"design", "run"}:
        problems.append("@decides 必须是 design 或 run")

    layer = a.get("attack_layer")
    if layer is None:
        problems.append("缺 @attack_layer —— 对手方攻的是结论、前提、还是问题本身？"
                        "攻前提时模拟裁定不了，产出只能是判别预测")
    elif a["attack_layer"].get("_text", "").strip() not in {
            "conclusion", "premise", "definition"}:
        problems.append("@attack_layer 必须是 conclusion / premise / definition")
    elif a["attack_layer"].get("_text", "").strip() == "definition":
        problems.append("@attack_layer=definition —— 定义之争，不该用模拟回答")

    who = a.get("who_changes_behavior")
    if who is None:
        problems.append("缺 @who_changes_behavior —— 说不出具体的人和具体的决定，"
                        "就是「不重要但可判定」那一档：它能过后面所有的门，而它不值得问")
    else:
        body = who.get("_text", "").strip()
        if len(body) < 12 or body in {"TODO", "待填", "?"}:
            problems.append(f"@who_changes_behavior 太短或是占位符：{body!r}"
                            "——要指名具体的人与具体的决定")

    sz = a.get("size_estimate")
    if sz is None:
        problems.append("缺 @size_estimate —— 没有事前估计就没法校准，"
                        "未来也无从判断该不该拆")
    else:
        for k in ("impl_lines", "criteria", "failure_modes"):
            if not sz.get(k, "").strip().isdigit():
                problems.append(f"@size_estimate 缺数值字段 {k}=")
        fm = sz.get("failure_modes", "")
        if fm.isdigit() and int(fm) > 1 and not sz.get("split_waived"):
            problems.append(
                f"@size_estimate 声明了 {fm} 个可判定的失败方式。"
                "一个里程碑只应该有一个——会想分开报告的失败就是不同的里程碑。"
                "确实要合并，写 split_waived=<理由>")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("goal", type=pathlib.Path)
    args = ap.parse_args()

    problems = check(args.goal)
    for p in problems:
        print(f"[FAIL] {args.goal.name}: {p}")
    if problems:
        print(f"\ngoal 未就绪：{len(problems)} 项。这些步骤跳过之后没有痕迹，所以由 gate 管。")
        return 1
    print(f"goal 就绪：{args.goal.name} 的六项必填证据齐全（文献 · 对手方 · 攻击层 · 设计还是运行 · 谁改变做法 · 规模）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
