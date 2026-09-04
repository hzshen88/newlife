#!/usr/bin/env python3
"""扫出「解析失败 → 静默退化为默认值」这一类缺陷。

这一类在本项目已经出现两次，两次都表现为 gate 因为**错误的原因**显示绿色：

1. `mutation_scan.py` 用固定前缀正则抽 check 标签，抽不到时 `all_checks` 成空集，
   于是「每个 check 都被抓住」在空集上恒真——`moran_plan_grid.py` 长期显示假绿。
2. `gate_coverage_check.py` 写成 `int(m.group(1)) if m else 0`，正则不中就把
   「未触及计数」记成 0，覆盖率被系统性高估。

出现两次就不该再靠人读代码发现。本工具只做一条**精确**规则，宁可漏报不误报：

  R1（语法，高置信）：形如 `<expr> if <name> else <常量>` 的条件表达式，其中
      `<name>` 在同一函数里由 `re.search` / `re.match` / `re.fullmatch` 赋值。

  R2（语义，广覆盖）：函数里绑定了正则匹配结果，却**不存在任何针对该名字的硬失败
      路径**（raise / assert / sys.exit / 非零 return）。

  R3（吞异常）：`except Exception:`（或裸 `except:`）的处理体**只有一个 `pass`**。
      这是「尝试失败 → 什么都不做 → 继续往下走」的最直白写法。第十三个里程碑实测出的
      那处 `silent_output` 就是它：`git` 不在时异常被吞掉，进程照常产出一份格式完好的
      判定，**理由写成「基线不可得」而真实原因是 git 不在**——不是没报警，是报错了案由。
      **规则刻意窄**：只认处理体恰好是 `pass` 的，`except ...: return False` 之类不报
      （`probes.py` 里两个分支返回同值的探测器是正当的，报了就是误报）。

**为什么需要 R2**：第二轮外审构造了 5 个语义完全等价的变体，R1 只抓住 1 个——
`if/else` 语句、命名常量做默认值、`or` 惯用法、`try/except` 全部逃逸。其中「把魔法
数字提成命名常量」恰恰是最常见的评审建议：一次善意重构就能让代码对 R1 隐身，语义
一字未改。**R1 保证的只是「不再犯这两个历史坑的字面写法」，不是「这一类被盯住了」。**

R2 不看默认值长什么样，只问一句：解析失败时，有没有一条会**炸**的路。没有就报。

**误报怎么办——声明，不是沉默。** 有些函数里「匹配不上」本就是正常分支（过滤、
探测）。这种情况在函数体里写一行：

    # silent-degradation: ok —— <为什么匹配不上是正常的>

豁免因此是**写出来**的，和项目其他地方一样（run_gates 的 EXEMPT、covers 的
UNVERIFIABLE）；沉默的豁免不算豁免。

命中即 exit 1。
"""

from __future__ import annotations

import argparse
import ast
import io
import pathlib
import re
import tokenize
import sys

# `findall`/`finditer` 也算：F14 那个假绿正是 `set(re.findall(...))` 返回空集，
# 于是「每个 check 都被抓住」在空集上恒真。空结果同样是「解析失败的默认值」。
REGEX_FUNCS = {"search", "match", "fullmatch", "findall", "finditer"}


def _compiled_pattern_names(tree: ast.AST) -> set[str]:
    """由 `re.compile(...)` 赋值的名字（模块级或函数级都算）。

    第三轮外审的盲区之一：`PAT = re.compile(...)` 之后 `PAT.search(t)`，
    调用的 base 不叫 `re`，旧实现完全看不见。
    """
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            call = node.value
            if not isinstance(call, ast.Call):
                continue
            f = call.func
            if (
                isinstance(f, ast.Attribute)
                and f.attr == "compile"
                and isinstance(f.value, ast.Name)
                and f.value.id == "re"
            ):
                for t in targets:
                    if isinstance(t, ast.Name):
                        out.add(t.id)
    return out


def _is_regex_call(call: ast.AST, compiled: set[str]) -> bool:
    """这个调用是不是一次正则匹配（`re.search(...)` 或 `<已编译>.search(...)`）。"""
    if not isinstance(call, ast.Call):
        return False
    f = call.func
    if not isinstance(f, ast.Attribute) or f.attr not in REGEX_FUNCS:
        return False
    base = f.value
    if isinstance(base, ast.Name):
        return base.id == "re" or base.id in compiled
    # `re.compile(...).search(...)` 这种链式写法
    return _is_compile_call(base)


def _is_compile_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "compile"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "re"
    )


def _guarding_calls(fn: ast.AST) -> set[int]:
    """直接用在「会 raise 的条件」里的调用（按 id 记）。

    `if not PAT.match(x): raise ...` —— 匹配结果没绑定到名字，但它**就是**那道硬失败。
    首版 R2 把这种也报了（proofroot 的 `RngBank.__init__` 是实例），**那是误报**：
    误报会把 gate 训练成忽略，比漏报更糟（F9 的教训）。
    """
    out: set[int] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        raises = any(isinstance(n, (ast.Raise, ast.Assert)) for n in ast.walk(node))
        if not raises:
            continue
        for inner in ast.walk(node.test):
            if isinstance(inner, ast.Call):
                out.add(id(inner))
    return out


def _loop_iterated_calls(fn: ast.AST) -> set[int]:
    """直接作为 `for` 迭代对象的调用（按 id 记）。

    `for m in PAT.finditer(text):` 结构上**不可能**代入默认值——没有匹配就是循环不
    执行，不存在「猜一个对自己有利的值」。这与 F14 那个真 bug 不同：那里是
    `set(re.findall(...))` 的空集流进了一个全称量词，「每个 check 都被抓住」于是恒真。
    区别在于空结果有没有被当成一个**值**继续用下去。
    """
    return {
        id(node.iter)
        for node in ast.walk(fn)
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.iter, ast.Call)
    } | {
        id(gen.iter)
        for node in ast.walk(fn)
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp))
        for gen in node.generators
        if isinstance(gen.iter, ast.Call)
    }


def _regex_call_sites(fn: ast.AST, compiled: set[str]) -> list[tuple[int, str | None]]:
    """函数内**每一处**正则匹配调用 → (行号, 结果被绑到的名字或 None)。

    识别的不再是「哪种赋值语句」，而是「哪里发生了一次匹配」——绑定形式有多少种，
    这里就覆盖多少种。第三轮外审用三个地道写法证明了按赋值形式识别必然漏：

    - `if (m := re.search(...))` —— walrus，`ast.NamedExpr` 不是 `ast.Assign`，
      整个函数被跳过。**这是现代 Python 写这个 bug 最地道的方式。**
    - `PAT.search(t)` —— 预编译，调用 base 不叫 `re`。
    - `f(re.search(...))` —— 结果直接传进别的函数，压根没有名字。

    最后一种绑不到名字，因此**无法被任何守卫检查**，一律报出：拿不到引用就没法在
    失败时炸。
    """
    bound: dict[int, str | None] = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            if isinstance(node.targets[0], ast.Name) and _is_regex_call(
                node.value, compiled
            ):
                bound[id(node.value)] = node.targets[0].id
        elif isinstance(node, ast.NamedExpr):
            if isinstance(node.target, ast.Name) and _is_regex_call(
                node.value, compiled
            ):
                bound[id(node.value)] = node.target.id

    iterated = _loop_iterated_calls(fn) | _guarding_calls(fn)
    sites: list[tuple[int, str | None]] = []
    for node in ast.walk(fn):
        if _is_regex_call(node, compiled) and id(node) not in iterated:
            sites.append((node.lineno, bound.get(id(node))))
    return sites


def _references(node: ast.AST, name: str) -> bool:
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def _hard_fail_lines(fn: ast.AST, name: str) -> list[int]:
    """函数内针对 `name` 的硬失败行号。

    两种形态都算，只认第一种会误报——真实的守卫通常写成
    `if m is None and ...: raise SystemExit(...)`，`raise` 本身并不提到 `m`，
    引用在 `if` 的条件里：

    1. `raise` / `assert` 语句自身引用了 `name`
    2. `if <条件里引用了 name>:` 且分支体内有 `raise` / `assert` / `sys.exit`
    """
    lines = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.Raise, ast.Assert)) and _references(node, name):
            lines.append(node.lineno)
        elif isinstance(node, ast.Match) and _references(node.subject, name):
            # `match m: case None: raise ...` 是正确的守卫写法。第四轮外审把它标为误报
            # ——误报会把 gate 训练成被忽略，比漏报更该修（同 F9 的教训）。
            for case in node.cases:
                if any(
                    isinstance(inner, (ast.Raise, ast.Assert))
                    for inner in ast.walk(case)
                ):
                    lines.append(node.lineno)
                    break
        elif isinstance(node, ast.If) and _references(node.test, name):
            for inner in ast.walk(node):
                if isinstance(inner, (ast.Raise, ast.Assert)):
                    lines.append(node.lineno)
                    break
                if isinstance(inner, ast.Call):
                    f = inner.func
                    if isinstance(f, ast.Attribute) and f.attr == "exit":
                        lines.append(node.lineno)
                        break
    return lines


EXEMPTION_RE = re.compile(r"#\s*silent-degradation:\s*ok\s*(?:——|--|—)?\s*(.*)$")
MIN_REASON_CHARS = 12


def _comment_lines(src: str) -> dict[int, str]:
    """真正的注释 token → 行号。**不是**按原始文本行匹配。

    首版按 `src_lines` 逐行找标记，结果本函数自己的 docstring 里提到那个标记，
    它就把自己判成了已豁免——与第三轮外审刚指出的 `@frozen:` 整行子串绕过是同一类
    （匹配粒度对了不看上下文，字符串/注释不分），而且是在学过那一课之后写出来的。
    用 tokenize 把注释和字符串分开，同类错误就不可能再犯。
    """
    out: dict[int, str] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                out[tok.start[0]] = tok.string
    except (tokenize.TokenError, IndentationError):
        pass  # 语法有问题的文件，AST 解析那步会先炸，这里不猜
    return out


def _exemption(fn: ast.AST, comments: dict[int, str]) -> tuple[bool, str | None]:
    """函数体范围内的豁免声明，返回 (是否豁免, 理由)。

    豁免是这套机制里唯一的逃逸路径，所以它自己要有约束，否则「写一行注释即可脱管」：

    - **必须带理由**，且理由不能是敷衍的几个字（`MIN_REASON_CHARS`）。裸写
      `# silent-degradation: ok` 不生效，并且会被报成一条 FAIL——比静默失效更好，
      因为写的人会立刻知道它没起作用。
    - **每一条豁免每次扫描都会被列出来**（见 main()）。豁免可以有，但不可以看不见：
      看不见的豁免会累积成沉默的免检区。
    """
    start = fn.lineno
    end = max(
        [getattr(n, "end_lineno", fn.lineno) or fn.lineno for n in ast.walk(fn)]
        + [fn.lineno]
    )
    # silent-degradation: ok —— 本函数就是豁免探测器，「这一行没有豁免标记」是它最常见的正常返回
    for lineno in range(start, end + 1):
        comment = comments.get(lineno)
        if not comment:
            continue
        m = EXEMPTION_RE.search(comment)
        if m:
            reason = m.group(1).strip()
            return (len(reason) >= MIN_REASON_CHARS), reason
    return False, None


def scan(path: pathlib.Path, exemptions: list | None = None) -> list[tuple[int, str]]:
    src = path.read_text()
    tree = ast.parse(src)
    findings: list[tuple[int, str]] = []
    if exemptions is None:
        exemptions = []
    compiled = _compiled_pattern_names(tree)
    comments = _comment_lines(src)
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        sites = _regex_call_sites(fn, compiled)
        bound = {name: ln for ln, name in sites if name is not None}
        exempt, reason = _exemption(fn, comments)
        _skip_regex_rules = not sites
        if reason is not None:
            if exempt:
                exemptions.append((fn.lineno, f"{fn.name}(): {reason}"))
            else:
                findings.append((
                    fn.lineno,
                    f"{fn.name}(): 豁免声明的理由太短或缺失"
                    f"（{len(reason)} < {MIN_REASON_CHARS} 字符）——**豁免不生效**。"
                    f"写清楚为什么「匹配不上」在这里是正常的，否则请改成硬失败",
                ))
        r2_hit: set[str] = set()

        # --- R3：吞异常（处理体只有一个 pass）---
        if not exempt:
            for node in ast.walk(fn):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                broad = node.type is None or (
                    isinstance(node.type, ast.Name) and node.type.id == "Exception")
                only_pass = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                if broad and only_pass:
                    findings.append((
                        node.lineno,
                        f"{fn.name}(): `except Exception: pass` —— 尝试失败后什么都不做，"
                        f"流程照常往下走。缺失的原因会被后面的代码写成别的案由",
                    ))

        # --- R2：整个函数里没有任何针对匹配结果的硬失败路径 ---
        if not exempt and not _skip_regex_rules:
            unbound = [ln for ln, name in sites if name is None]
            if unbound:
                findings.append((
                    unbound[0],
                    f"{fn.name}(): 正则匹配的结果**没有被绑定到任何名字**"
                    f"（直接传给别的调用），因此无法在失败时检查它——"
                    f"先接住它，再决定失败时炸还是声明豁免",
                ))
            for name, assigned_at in sorted(bound.items()):
                if not _hard_fail_lines(fn, name):
                    r2_hit.add(name)
                    findings.append((
                        assigned_at,
                        f"{fn.name}(): {name} 由正则赋值，但函数里**没有任何**针对它的"
                        f"硬失败路径（raise/assert/sys.exit/非零 return）——"
                        f"解析失败时无论用哪种写法给默认值都不会报错。"
                        f"若「匹配不上」在此确属正常，写一行 "
                        f"`# silent-degradation: ok —— 理由` 声明豁免",
                    ))
        for node in ast.walk(fn):
            if _skip_regex_rules or not isinstance(node, ast.IfExp):
                continue
            test = node.test
            if not (isinstance(test, ast.Name) and test.id in bound):
                continue
            if not isinstance(node.orelse, ast.Constant):
                continue
            # R2 已经就这个名字报过了，不重复
            if test.id in r2_hit:
                continue
            guards = [ln for ln in _hard_fail_lines(fn, test.id) if ln < node.lineno]
            if guards or exempt:
                continue
            findings.append((
                node.lineno,
                f"{fn.name}(): `… if {test.id} else {node.orelse.value!r}` —— "
                f"{test.id} 由正则赋值（L{bound[test.id]}），不中即静默退化为 "
                f"{node.orelse.value!r}，且此前无引用它的硬失败",
            ))
    return findings


# 覆盖面的性质检查：语义等价、语法不同的变体必须**全部**被报出来。
# 锁住的是「广度」——R1 曾经只挡得住三元表达式那一种外壳，一次善意重构
# （把字面量提成命名常量）就能让代码隐身。这里把广度变成可证伪的断言。
_MUST_FLAG = {
    "ternary": "    m = re.search(p, t)\n    return int(m.group(1)) if m else 0\n",
    "if_else": "    m = re.search(p, t)\n    if m:\n        n = 1\n    else:\n        n = 0\n    return n\n",
    "named_const": "    m = re.search(p, t)\n    return int(m.group(1)) if m else D\n",
    "or_idiom": "    m = re.search(p, t)\n    return (m and int(m.group(1))) or 0\n",
    "try_except": "    m = re.search(p, t)\n    try:\n        return int(m.group(1))\n    except AttributeError:\n        return 0\n",
    "dict_dispatch": "    m = re.search(p, t)\n    return {True: 1, False: 0}[bool(m)]\n",
    "getattr_fallback": "    m = re.search(p, t)\n    return getattr(m, 'group', lambda _: 0)(1)\n",
    # 豁免是唯一的逃逸路径，它自己的约束也要可证伪：
    # 第三轮外审的三个盲区（按「绑定形式」识别必然漏掉的）：
    "walrus": "    if (m := re.search(p, t)):\n        return int(m.group(1))\n    return 0\n",
    "precompiled": "    m = PAT.search(t)\n    return int(m.group(1)) if m else 0\n",
    "unbound": "    return int(getattr(re.search(p, t), 'group', lambda _: 0)(1))\n",
    # 我另造的两个（只过红队举的例子就是换皮）：
    "chained_compile": "    m = re.compile(p).search(t)\n    return int(m.group(1)) if m else 0\n",
    "walrus_while": "    n = 0\n    while (m := PAT.search(t)):\n        n += 1\n        t = t[m.end():]\n    return n\n",
    # F14 的原始形态：findall 的空集流进全称量词
    "findall_empty_set": "    s = set(re.findall(p, t))\n    return all(x for x in s)\n",
    # R3：吞异常（第十三个里程碑实测出的那处 silent_output）
    "swallow_pass": "    try:\n        m = re.search(p, t)\n    except Exception:\n        pass\n    return 0\n",
    "swallow_bare": "    try:\n        m = re.search(p, t)\n    except:\n        pass\n    return 0\n",
    "bare_exemption": "    # silent-degradation: ok\n    m = re.search(p, t)\n    return int(m.group(1)) if m else 0\n",
    "short_reason": "    # silent-degradation: ok —— 没事\n    m = re.search(p, t)\n    return int(m.group(1)) if m else 0\n",
}
_MUST_NOT_FLAG = {
    "guarded": "    m = re.search(p, t)\n    if m is None:\n        raise SystemExit('no match')\n    return int(m.group(1))\n",
    "walrus_guarded": "    if (m := PAT.search(t)) is None:\n        raise SystemExit('no match')\n    return int(m.group(1))\n",
    "match_case_guarded": "    m = PAT.search(t)\n    match m:\n        case None:\n            raise SystemExit('no match')\n        case _:\n            return int(m.group(1))\n",
    # 正当：两个分支返回同值的探测器（probes.py 的形状），报了就是误报
    "except_returns_same": "    try:\n        m = PAT.search(t)\n        raise SystemExit(1) if m is None else None\n    except Exception:\n        return False\n    return False\n",
    "unbound_in_raising_guard": "    if not PAT.match(t):\n        raise SystemExit('bad name')\n    return 1\n",
    "finditer_loop": "    n = 0\n    for _ in PAT.finditer(t):\n        n += 1\n    return n\n",
    "declared_exempt": "    # silent-degradation: ok —— 探测器，匹配不上本就是正常分支\n    m = re.search(p, t)\n    return bool(m) if m else False\n",
}


def run_selftest() -> int:
    import tempfile  # noqa: PLC0415

    failures = []
    for label, body in list(_MUST_FLAG.items()) + list(_MUST_NOT_FLAG.items()):
        src = f"import re\np = 'x'\nD = 0\nPAT = re.compile(p)\n\n\ndef f(t):\n{body}"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write(src)
            tmp = pathlib.Path(fh.name)
        hits = scan(tmp)
        tmp.unlink()
        should = label in _MUST_FLAG
        if should and not hits:
            failures.append(f"{label}: 应被报出却漏掉了——覆盖面被收窄了")
        if not should and hits:
            failures.append(f"{label}: 不该被报却报了——会误报的 gate 会被训练成忽略")

    for f in failures:
        print(f"[FAIL] coverage: {f}")
    if failures:
        print(f"\n覆盖面自检：{len(failures)} 条不成立")
        return 1
    print(
        f"覆盖面自检：{len(_MUST_FLAG)} 种等价写法全部报出，"
        f"{len(_MUST_NOT_FLAG)} 种正当写法全部放过"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true", help="检验覆盖面本身")
    ap.add_argument(
        "--max-exemptions",
        type=int,
        default=0,
        metavar="N",
        help="声明的豁免上限，**默认 0（default-deny）**。要放行豁免必须显式写出数字。"
             "首版默认 None（无限），第四轮外审把它记为「新保护默认关闭」的第三次出现："
             "同一份文件，走 run_gates 会红、直接跑却全绿。保护的默认值必须是严的那一端。",
    )
    args = ap.parse_args(argv)          # None → 读 sys.argv，当脚本跑时不变

    if args.selftest:
        return run_selftest()

    total = 0
    all_exemptions: list[tuple[pathlib.Path, int, str]] = []
    for path in args.paths:
        exemptions: list[tuple[int, str]] = []
        for lineno, msg in scan(path, exemptions):
            total += 1
            print(f"[FAIL] {path}:{lineno}: {msg}")
        all_exemptions += [(path, ln, m) for ln, m in exemptions]

    # 豁免每次都列出来。豁免可以有，看不见不行——看不见的豁免会累积成沉默的免检区。
    if all_exemptions:
        print(f"\n声明的豁免 {len(all_exemptions)} 处（每次扫描都会列出）：")
        for path, lineno, msg in all_exemptions:
            print(f"  {path}:{lineno}: {msg}")
    if len(all_exemptions) > args.max_exemptions:
        print(
            f"\n声明的豁免 {len(all_exemptions)} 处，超过上限 {args.max_exemptions}。"
            f"新增豁免要么改掉代码不再需要它，要么显式提高上限——"
            f"后者会留在 diff 里，被人看见。"
        )
        return 1

    if total:
        print(
            f"\n{total} 处「解析失败静默退化」。正则不中时应硬失败并打印实际输出，"
            "不要猜一个对自己有利的默认值。"
        )
        return 1
    print(f"扫描 {len(args.paths)} 个文件，未发现静默退化模式（R1 语法 + R2 语义）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
