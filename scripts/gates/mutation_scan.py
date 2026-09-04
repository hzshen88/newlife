#!/usr/bin/env python3
"""变异扫描 —— 找出「不可能失败」的 check。

## 为什么有这个脚本

三轮红队里，作者反复犯同一类错：写出**形状像检查、但什么都验证不了**的 check。
`check 3` 两侧调用同一个函数，比较必然相等；`check 12` 的合并数由字面量 1/0 决定，
把判据换成与合并无关的东西仍然全绿；一次「修复」把 `F(1)` 改成 `F(2)`，归一化后
任何常数都一样，`F(7)` 照样通过。

共同点：判断一个 check 好不好，不能看**它断言了什么**，要看**什么能让它失败**。
这件事可以机械化，不必等红队来发现。

做法：对被测脚本每个生产函数的每条 `return` 注入变异，跑全套 check，记录每个 check
被多少变异抓住。**从不被任何变异抓住的 check 就是空洞嫌疑**——它可能仍然有意义
（例如断言的是一个与所有生产函数都无关的常量），但需要作者显式说明凭什么。

这不能取代红队：变异只覆盖「生产函数返回值出错」这一类，覆盖不了建模假设整体错、
判据选错、或文档与脚本不符。它的价值是把最机械的一类一次性清干净。

## 跑法

    cd docs/science-superpowers
    python3 verification/mutation_scan.py questions/verification/moran_genealogy_check.py
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import re
import subprocess
import sys
import tempfile

# 每种变异是一个 (名字, 把原返回表达式包装成新表达式的模板)。
# 模板里的 {e} 会被替换成原表达式。
MUTATIONS = [
    ("×2", "({e}) * 2"),
    ("+1", "({e}) + 1"),
    ("常数 1", "__import__('fractions').Fraction(1)"),
    ("常数 0", "__import__('fractions').Fraction(0)"),
    # 依赖某个整数参数——常数/均匀类断言只有这种变异能破坏。没有整数参数的函数跳过。
    ("依赖参数 {arg}", "({e}) + __import__('fractions').Fraction({arg} % 3)"),
]


def instrumented_names(src: str) -> list[str]:
    """读脚本自己的 _INSTRUMENTED 清单——生产函数由脚本声明，不由本工具猜。"""
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_INSTRUMENTED" for t in node.targets
        ):
            return [el.value for el in node.value.elts if isinstance(el, ast.Constant)]
    return []


def return_sites(src: str, names: list[str]):
    """(函数名, 行, 起列, 止列, 原表达式, 可用的整数参数名) —— 只取生产函数里的 return。"""
    tree = ast.parse(src)
    lines = src.split("\n")
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in names):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return) and sub.value is not None:
                v = sub.value
                if v.lineno != v.end_lineno:  # 只处理单行返回，多行的跳过
                    continue
                expr = lines[v.lineno - 1][v.col_offset : v.end_col_offset]
                # 猜一个整数参数：名字像索引/规模的优先
                argnames = [a.arg for a in node.args.args]
                intish = next(
                    (
                        a
                        for a in argnames
                        if a in ("i", "j", "n", "k", "N", "reproducer", "dier")
                    ),
                    None,
                )
                out.append(
                    (node.name, v.lineno, v.col_offset, v.end_col_offset, expr, intish)
                )
    return out


def run_and_collect(script: pathlib.Path) -> tuple[int, set[str]]:
    """跑脚本，返回 (exit code, 红掉的 check id 集合)。"""
    proc = subprocess.run(
        [sys.executable, script.name],
        cwd=script.parent,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # 标签不假定 `check N` 前缀：plan 侧脚本用 `grid-computed` 这类具名 id，
    # 写死前缀会让 all_checks 变成空集，于是「每个 check 都被抓住」在空集上恒真
    # ——gate 因为错误的原因显示绿色。
    # 空集有歧义：可能是「没有 check 变红」，也可能是「输出格式变了、一条都没解析出来」。
    # 后者会让每个变异体都显示成逃逸，而原因完全不在被测代码上。用「至少解析出一条
    # 带状态的标签行」把两者分开——这是 F14 那个假绿的同族，同一个文件里的第二例。
    labelled = re.findall(r"^\[([^\]]+)\].*--\s*(PASS|FAIL)$", proc.stdout, re.M)
    # 只在**干净退出却一条都没解析出来**时炸。变异体崩溃（非零退出、stdout 为空）是
    # 变异扫描的正常情形，不是格式变了；把两者混在一起会让第一个崩溃的变异体中断整轮。
    if proc.returncode == 0 and not labelled:
        raise SystemExit(
            f"{script.name}: 输出里一条带状态的 check 标签都解析不出来。"
            f"格式可能变了——硬失败，不把「解析不出」当成「没有失败」。\n"
            f"--- 实际输出（末 400 字）---\n{proc.stdout[-400:]}"
        )
    failed = {label for label, status in labelled if status == "FAIL"}
    return proc.returncode, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("script", type=pathlib.Path)
    ap.add_argument("--quiet", action="store_true", help="只打印结论，不逐条列出变异")
    args = ap.parse_args()

    src = args.script.read_text()
    names = instrumented_names(src)
    if not names:
        print(f"{args.script}: 找不到 _INSTRUMENTED 清单，无法确定生产函数")
        return 2
    sites = return_sites(src, names)

    baseline_code, baseline_failed = run_and_collect(args.script)
    if baseline_code != 0:
        print(f"基线就没通过（exit {baseline_code}），先修好再扫描")
        return 2
    all_checks = set(
        re.findall(
            r"^\[([^\]]+)\].*--\s*(?:PASS|FAIL)$",
            subprocess.run(
                [sys.executable, args.script.name],
                cwd=args.script.parent,
                capture_output=True,
                text=True,
            ).stdout,
            re.M,
        )
    )

    if not all_checks:
        print(
            f"{args.script}: 基线输出里解析不出任何 check 标签。"
            "扫描无意义——空集上「每个 check 都被抓住」恒真，会给出假绿。"
        )
        return 2

    print(
        f"生产函数 {len(names)} 个，单行 return {len(sites)} 处，"
        f"变异 {len(MUTATIONS)} 种 → {len(sites) * len(MUTATIONS)} 个变异体\n"
    )

    caught_by: dict[str, set[str]] = {c: set() for c in all_checks}
    escaped = []
    lines = src.split("\n")

    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp) / args.script.name
        for fn, lineno, c0, c1, expr, intish in sites:
            for mut_name, template in MUTATIONS:
                if "{arg}" in template and not intish:
                    continue
                new_lines = list(lines)
                new_expr = template.format(e=expr, arg=intish or "0")
                label_mut = mut_name.format(arg=intish or "-")
                new_lines[lineno - 1] = (
                    new_lines[lineno - 1][:c0] + new_expr + new_lines[lineno - 1][c1:]
                )
                work.write_text("\n".join(new_lines))
                label = f"{fn}:{lineno} {label_mut}"
                try:
                    code, failed = run_and_collect(work)
                except Exception as exc:  # 崩溃也算被抓住
                    code, failed = 1, set()
                    if not args.quiet:
                        print(f"  [crash ] {label}: {type(exc).__name__}")
                if code == 0:
                    escaped.append(label)
                    if not args.quiet:
                        print(f"  [ESCAPED] {label} — 全部 check 仍绿")
                else:
                    for c in failed:
                        caught_by[c].add(label)

    print(f"\n{'check':12s} 被多少变异抓住")
    suspects = []
    for c in sorted(all_checks):
        n = len(caught_by[c])
        flag = ""
        if n == 0:
            flag = "  ← 本工具的变异未能触及（见下方说明）"
            suspects.append(c)
        print(f"  {c:12s} {n:3d}{flag}")

    print()
    if escaped:
        # 「预期豁免」= 变异打在故意写错的 `*_wrong` 上，本就不该让任何 check 红。
        # 这一类机械可判，先摘出去；剩下的必须**一条不落**地打印。
        #
        # 原来是 `escaped[:10]` 截断 + 一句「逃逸 ≠ 缺陷」的免责声明。第四轮红队里
        # 这个组合直接造成了漏检：18 条逃逸里前 8 条全是 `*_wrong` 的预期豁免，
        # 而仅有的两条真缺陷（`moran_step_lineage_update` 的 `return new * 2`，
        # 暴露了 check 12 只看标签个数、看不见槽位配置）排在第 17、18 位，
        # 正好落在被 “… 另有 8 个” 吞掉的部分里。截断把结论藏在了噪声后面。
        # silent-degradation: ok —— 这里的正则是分类过滤器，匹配不上表示「这条逃逸不是 *_wrong 的预期豁免」，是正常分支，不是解析失败
        expected = [e for e in escaped if re.match(r"^\w*_wrong:", e)]
        needs_eyes = [e for e in escaped if e not in expected]
        print(f"逃逸的变异 {len(escaped)} 个（没有任何 check 红）：")
        if expected:
            print(f"  预期豁免 {len(expected)} 个：变异打在故意写错的 *_wrong 函数上")
        if needs_eyes:
            print(f"  需人工判定 {len(needs_eyes)} 个（全部列出，不截断）：")
            for e in needs_eyes:
                print(f"    {e}")
    if suspects:
        print(f"\n未被触及的 check {len(suspects)} 个：{', '.join(suspects)}")
        print("**这不等于空洞**。本工具只变异单行 `return` 表达式，碰不到 if 分支里的")
        print("逻辑，也生成不出破坏「均匀性」以外性质的变异。对每个未触及的 check，")
        print("作者必须手工构造一个应当抓住它的变异并验证会红——做不到才是空洞。")
    if escaped:
        print("\n**逃逸 ≠ 缺陷**：变异到故意写错的函数（`*_wrong`）、或变异后被断言的")
        print("性质没有真正改变（常数权重归一化后仍均匀），本就不该让 check 红。")
        print("要看的是「本该被抓却没被抓」的那些。")
    if not suspects and not escaped:
        print("每个 check 都至少被一个变异抓住，且没有变异逃逸。")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
