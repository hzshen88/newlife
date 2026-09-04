"""假扫描扫描器：**名为扫描、实为重复**的推导式。

## 这条门为什么存在

第十九个里程碑的 Z5 是一条**负控**，冻结判据写的是「`yield` 设成 dFBA 某点的产率后
**重扫**，Monod 产率仍逐点恒定」。实现是：

    monod_pinned = [_run(MONOD, "foreign-monod", pinned) for _ in O2_SWEEP]

`O2_SWEEP` 被迭代了，但**循环变量丢掉了**——五次跑的是同一份配置。于是判据
`max - min < 1e-9` 在**任何**物理配置下都为真（实测 yield 从 1e-6 到 1e3 全绿），
判定力为零。它在合取里待了整整一个里程碑没被发现，因为**恒真的判据永远不会红**，
而人只会去查红的东西。

## 判据

对**具名模块级常量**做推导式，而循环变量在元素表达式里未被引用 —— 报。

`range(n)` 这类不报：对它做推导本就是「重复 n 次」，在随机过程里是正当写法。
**具名常量不同**——给一组值起了名字，就是在说这些值本身有意义。

    python3 scripts/gates/vacuous_criterion_scan.py <file.py> ...
    python3 scripts/gates/vacuous_criterion_scan.py --selftest
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys

Finding = tuple[int, str, str]      # 行号 · 常量名 · 循环变量


def _named_constants(tree: ast.Module) -> set[str]:
    """模块级 `NAME = <序列字面量>` 的名字。"""
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List, ast.Set)):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _targets(node: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def scan(source: str) -> list[Finding]:
    tree = ast.parse(source)
    constants = _named_constants(tree)
    findings: list[Finding] = []
    comprehensions = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
    for node in ast.walk(tree):
        if not isinstance(node, comprehensions):
            continue
        # 元素表达式：DictComp 有 key/value，其余有 elt
        parts = ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt])
        used = set().union(*(_targets(p) for p in parts))
        for gen in node.generators:
            if not (isinstance(gen.iter, ast.Name) and gen.iter.id in constants):
                continue
            bound = _targets(gen.target)
            if not (bound & used):
                findings.append((node.lineno, gen.iter.id,
                                 ", ".join(sorted(bound)) or "_"))
    return findings


SELFTEST_RED = "SWEEP = (1, 2, 3)\nxs = [run(cfg) for _ in SWEEP]\n"
SELFTEST_GREEN = ("SWEEP = (1, 2, 3)\n"
                  "xs = [run(cfg(v)) for v in SWEEP]\n"
                  "ys = [make() for _ in range(3)]\n")


def _selftest() -> int:
    """负控：假扫描必须被抓到，真扫描与 `range` 重复必须不报。"""
    ok = True
    if not scan(SELFTEST_RED):
        print("  [失败] 丢弃循环变量的假扫描没有被报出来"); ok = False
    if scan(SELFTEST_GREEN):
        print(f"  [失败] 真扫描/range 重复被误报：{scan(SELFTEST_GREEN)}"); ok = False
    print("  自检通过：假扫描红、真扫描与 range 重复绿。" if ok else "  自检失败。")
    return 0 if ok else 1


KNOWN_VACUOUS = {("newlife/conform/yield_verdict.py", "O2_SWEEP"): 2}
"""**处置已作出（2026-09-04），不是待办。**

第十九个里程碑的预注册已冻结，判定产物逐字节可复现。改 runner 会毁掉那次复现，
所以**不改**——照 `verdict_rot.KNOWN_BROKEN` 的先例：记录，不掩盖，也不重写历史。

两处分别是 Z4 与 Z5 的 Monod 扫描。Z5 因此**恒真、零判定力**（实测 `yield` 从
1e-6 到 1e3 全绿）；Z4 的判据是逐点比对声明值，单点即可成立，不受影响，但它在
产物表格里与氧并列印出，读起来像扫描。结论本身不依赖 Z5——
Z3（dFBA 产率随氧变，幅度 56%）∧ Z4（Monod 产率恒定）已由算术蕴含它。

完整处置见 `docs/worlds/019-yield-input-or-outcome.md`。
**登记的是精确条数**：同一文件同一常量上再多一处假扫描，或这两处消失，都会红——
豁免不会无声累积，也不会变成僵尸。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()

    seen: dict[tuple[str, str], int] = {}
    # 登记项只在**它那个文件真被扫到**时才核对条数——扫描范围小不等于缺陷消失，
    # 拿「没扫到」当「已修好」正是静默降级本身。
    in_scope = {k for k in KNOWN_VACUOUS
                if any(str(q).endswith(k[0]) for q in args.paths)}
    unregistered = 0
    for path in args.paths:
        for lineno, const, target in scan(path.read_text()):
            key = next((k for k in KNOWN_VACUOUS
                        if str(path).endswith(k[0]) and k[1] == const), None)
            if key is not None:
                seen[key] = seen.get(key, 0) + 1
                continue
            unregistered += 1
            print(f"{path}:{lineno}: 对具名常量 {const} 迭代，但循环变量 "
                  f"{target} 未被使用 —— 这不是扫描，是重复 len({const}) 次")

    drifted = [(k, KNOWN_VACUOUS[k], seen.get(k, 0))
               for k in in_scope if seen.get(k, 0) != KNOWN_VACUOUS[k]]
    for (rel, const), want, got in drifted:
        print(f"{rel}: {const} 上登记 {want} 处已知假扫描，实际扫到 {got} 处 —— "
              f"{'登记已过期' if got < want else '出现了新的、未登记的'}")

    for rel, const in in_scope:
        want = KNOWN_VACUOUS[(rel, const)]
        if not any(k == (rel, const) for k, *_ in drifted):
            print(f"[已登记] {rel}: {const} 上 {want} 处，处置见 KNOWN_VACUOUS 文档字符串")

    if unregistered:
        print(f"\n{unregistered} 处未登记的假扫描。判据若建立在它们之上，则**恒真**——"
              f"负控不会红，等于没有负控。")
    return 1 if (unregistered or drifted) else 0


if __name__ == "__main__":
    raise SystemExit(main())
