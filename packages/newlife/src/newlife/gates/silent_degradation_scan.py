#!/usr/bin/env python3
"""Scan for the defect class "parse failed -> silently fall back to a default".

It has surfaced twice in this project, both times as a gate showing green **for the wrong
reason**:

1. a scanner extracted check labels with a fixed-prefix regex; when nothing matched,
   `all_checks` became the empty set, and "every check was caught" is true by construction
   on an empty set — one script showed false green for a long time.
2. a coverage check written as `int(m.group(1)) if m else 0` recorded "untouched count" as
   0 whenever the regex missed, systematically overstating coverage.

Twice is enough that it should not depend on someone reading the code. This tool applies
one **precise** rule set, preferring false negatives to false positives:

  R1 (syntactic, high confidence): a conditional expression shaped
      `<expr> if <name> else <constant>`, where `<name>` was bound in the same function by
      `re.search` / `re.match` / `re.fullmatch`.

  R2 (semantic, broad): a function binds a regex match result but **has no hard-failure
      path for that name at all** (raise / assert / sys.exit / non-zero return).

  R3 (swallowed exception): an `except Exception:` (or bare `except:`) whose body is
      **exactly one `pass`**. This is the most direct spelling of "the attempt failed, do
      nothing, carry on". A measured instance: with `git` absent the exception was
      swallowed and the process still emitted a well-formed verdict, **giving the reason as
      "baseline unavailable" when the real cause was that git was missing** — not a missing
      alarm, a misattributed one.
      **The rule is deliberately narrow**: only a body that is exactly `pass`. Something
      like `except ...: return False` is not reported — a probe whose two branches return
      the same value is legitimate, and reporting it would be a false positive.

**Why R2 is needed**: an external review constructed five semantically equivalent variants;
R1 caught one. `if/else` statements, a named constant as the default, the `or` idiom and
`try/except` all escaped it. And "lift the magic number into a named constant" is among the
most common review suggestions — one well-meant refactor makes the code invisible to R1
with the semantics unchanged. **R1 only guarantees "the literal spelling of those two
historical pits is not repeated", not "this class is being watched".**

R2 does not look at what the default is. It asks one question: when parsing fails, is there
a path that **blows up**? If not, it reports.

**False positives — declare them, do not go quiet.** In some functions "no match" is the
normal branch (filtering, probing). Write one line inside the function body:

    # silent-degradation: ok -- <why not matching is normal here>

An exemption is therefore **written down**, as everywhere else in this project; a silent
exemption is not an exemption.

Exit 1 on any hit.
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
                    f"{fn.name}(): the exemption's reason is missing or too short "
                    f"({len(reason)} < {MIN_REASON_CHARS} chars) — the exemption does "
                    f"not take effect. Spell out why 'no match' is normal here, or "
                    f"turn it into a hard failure",
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
                        f"{fn.name}(): `except Exception: pass` — the attempt failed, nothing "
                        f"was done, and the flow carried on. Downstream code will report "
                        f"some other cause for what is missing",
                    ))

        # --- R2：整个函数里没有任何针对匹配结果的硬失败路径 ---
        if not exempt and not _skip_regex_rules:
            unbound = [ln for ln, name in sites if name is None]
            if unbound:
                findings.append((
                    unbound[0],
                    f"{fn.name}(): the regex match result is never bound to a name "
                    f"(passed straight into another call), so nothing can check it on "
                    f"failure — bind it first, then decide between raising and declaring "
                    f"an exemption",
                ))
            for name, assigned_at in sorted(bound.items()):
                if not _hard_fail_lines(fn, name):
                    r2_hit.add(name)
                    findings.append((
                        assigned_at,
                        f"{fn.name}(): {name} is bound from a regex match, but the function "
                        f"has no hard-failure path at all for it "
                        f"(raise/assert/sys.exit/non-zero return) — however the default is "
                        f"spelled, a parse failure raises nothing. If 'no match' really is "
                        f"normal here, declare it with a line "
                        f"`# silent-degradation: ok -- reason`",
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
                f"{test.id} is bound from a regex match (L{bound[test.id]}); a miss "
                f"degrades silently to {node.orelse.value!r}, with no hard failure "
                f"referencing it beforehand",
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
            failures.append(f"{label}: should have been reported and was not — coverage narrowed")
        if not should and hits:
            failures.append(f"{label}: reported when it should not be — a gate that cries wolf "
                            f"gets trained into being ignored")

    for f in failures:
        print(f"[FAIL] coverage: {f}")
    if failures:
        print(f"\ncoverage selftest: {len(failures)} case(s) failed")
        return 1
    print(
        f"coverage selftest: all {len(_MUST_FLAG)} equivalent spellings reported, "
        f"all {len(_MUST_NOT_FLAG)} legitimate ones passed over"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true", help="test the scanner's own coverage")
    ap.add_argument(
        "--max-exemptions",
        type=int,
        default=0,
        metavar="N",
        help="maximum number of declared exemptions (default: 0, deny by default); "
             "allowing exemptions requires an explicit limit",
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
        print(f"\n{len(all_exemptions)} declared exemption(s) (listed on every scan):")
        for path, lineno, msg in all_exemptions:
            print(f"  {path}:{lineno}: {msg}")
    if len(all_exemptions) > args.max_exemptions:
        print(
            f"\n{len(all_exemptions)} declared exemption(s), above the limit of "
            f"{args.max_exemptions}. A new exemption means either changing the code so it "
            f"is no longer needed, or raising the limit explicitly — the latter stays in "
            f"the diff, where people can see it."
        )
        return 1

    if total:
        print(
            f"\n{total} occurrence(s) of 'parse failed -> silent fallback'. On a regex miss, fail "
            f"hard and print what was actually seen, "
            "rather than guessing a default that happens to suit you."
        )
        return 1
    print(f"scanned {len(args.paths)} file(s); no silent-degradation pattern found "
          f"(R1 syntactic + R2 semantic + R3 swallowed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
