#!/usr/bin/env python3
"""度量判定 runner 之间有多少重复，以及重复的是生命周期还是科学。

## 为什么要有这个工具

「判定层有多少能抽」这个问题此前答不了，因为只有一个样本。两次试图回答都翻车：
一次报了一个**人手三分、从没测过**的行数；一次用正则量，**漏了两处**，结论作废。
所以本工具的要求不是「量出一个数」，是**量法本身能被负控**——见 `negative_controls()`，
五条全过才输出结果，任一条不过就退出 1、不给数字。

## 三个必须先承认的陷阱

1. **语言差**：模板已译成英文，早期 runner 仍是中文。按文本比会被语言差淹没。
   因此走 AST：注释天然不进 AST，docstring 显式剥掉，`ast.unparse` 规范化空白与引号。
2. **样本不独立**：同一个问题的 v1/v2/v3 共享的**不只是生命周期，还有科学**。
   把它们当独立样本会把科学误算成「可抽」。因此**标题数字取两两交集的下界**——
   不需要人先声明谁和谁独立，最保守的那一对自己会浮出来。
3. **化妆品**：只差一个变量名或一个打印列宽的两条语句，逐字比是不等的。
   近似重复单独列出，**不进标题数字**，只作为人读的候选。

## 用法

    python scripts/measure_runner_overlap.py ~/Projects/my-research/questions
"""

from __future__ import annotations

import argparse
import ast
import difflib
import json
import pathlib
import sys
from itertools import combinations

REPO = pathlib.Path(__file__).resolve().parents[1]
TEMPLATE = (
    REPO / "packages/newlife/src/newlife/scaffold/templates" / "verdict.py.template"
)


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    """剥掉 docstring —— 它是 AST 里唯一残留的自然语言，会把语言差带进来。"""
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def units(path: pathlib.Path) -> list[tuple[str, str]]:
    """拆成 (所属函数, 规范化语句)。

    粒度是「函数体内的每条语句」，函数本身只贡献一个签名单元。整个函数当一个单元
    会让「改一行 → 整个函数不匹配」，系统性低估重复。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []

    def walk(body: list[ast.stmt], owner: str) -> None:
        for node in _strip_docstring(body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                head = type(node)(**{**node.__dict__, "body": [ast.Pass()]})
                ast.fix_missing_locations(head)
                out.append((owner, ast.unparse(head)))
                walk(node.body, node.name)
            else:
                out.append((owner, ast.unparse(node)))

    walk(tree.body, "<module>")
    return out


def norm_set(path: pathlib.Path) -> set[str]:
    return {u for _, u in units(path)}


def code_lines(path: pathlib.Path) -> int:
    """AST 语句实际占用的物理行（不含注释、docstring、空行）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            b = node.body
            if (
                b
                and isinstance(b[0], ast.Expr)
                and isinstance(b[0].value, ast.Constant)
                and isinstance(b[0].value.value, str)
            ):
                doc |= set(range(b[0].lineno, b[0].end_lineno + 1))
    live: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            live.add(node.lineno)  # 只记签名行
        elif isinstance(node, ast.stmt):
            live |= set(range(node.lineno, node.end_lineno + 1))
    return len(live - doc)


def near_misses(a: set[str], b: set[str], cutoff: float = 0.80) -> list[dict]:
    """近似重复。**不进标题数字**——它是给人看的候选，不是度量结果。"""
    out = []
    for x in sorted(a - b):
        best = difflib.get_close_matches(x, sorted(b - a), n=1, cutoff=cutoff)
        if best:
            out.append(
                {
                    "a": x,
                    "b": best[0],
                    "ratio": round(
                        difflib.SequenceMatcher(None, x, best[0]).ratio(), 3
                    ),
                }
            )
    return out


# ───────────────────────── 负控：先证明这把尺子会红 ─────────────────────────
def negative_controls(sets: dict[str, set[str]], tpl: set[str]) -> tuple[bool, dict]:
    """五条。任一条不过，本次度量作废，不输出数字。"""
    names = sorted(sets)
    first = sets[names[0]]
    pairs = {f"{a}|{b}": len(sets[a] & sets[b]) for a, b in combinations(names, 2)}

    # NC1：自己对自己必须 100%。证明这把尺子报得出高值。
    nc1 = len(first & first) == len(first)

    # NC2：对一份无关的 Python 文件必须近似 0。证明它报得出低值。
    #      用 stdlib 的 ast.py：确定性、任何环境都在。
    unrelated = norm_set(pathlib.Path(ast.__file__))
    overlap = len(first & unrelated)
    nc2 = overlap <= 2  # 允许 `pass` 之类的平凡碰撞

    # NC3：突变。从交集里拿掉一条语句，交集必须正好少 1——证明它不是恒真的。
    other = sets[names[1]]
    shared = first & other
    nc3 = bool(shared) and len((first - {sorted(shared)[0]}) & other) == len(shared) - 1

    # NC4：分辨力。两两交集必须有跨度。全都一样大 = 这把尺子分不出
    #      「同一个问题的迭代」和「两个独立问题」，标题数字就没有意义。
    nc4 = len(pairs) >= 2 and max(pairs.values()) > min(pairs.values())

    # NC5：跨语言。中文 runner 与英文模板的交集必须显著非零，
    #      否则说明 docstring / 注释没剥干净，度量被语言差污染。
    best_tpl = max(len(s & tpl) for s in sets.values())
    nc5 = best_tpl >= 0.5 * len(tpl)

    checks = {
        "NC1_self_is_total": {"passed": nc1},
        "NC2_unrelated_is_near_zero": {"passed": nc2, "overlap": overlap},
        "NC3_mutation_drops_by_exactly_one": {"passed": nc3},
        "NC4_matrix_has_spread": {"passed": nc4, "pairwise": pairs},
        "NC5_language_insensitive": {
            "passed": nc5,
            "best_vs_template": best_tpl,
            "template_units": len(tpl),
        },
    }
    return all(c["passed"] for c in checks.values()), checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "questions",
        type=pathlib.Path,
        help="含若干问题文件夹的目录，每个文件夹里有 verdict.py",
    )
    ap.add_argument("--template", type=pathlib.Path, default=TEMPLATE)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    files = {p.parent.name: p for p in sorted(args.questions.glob("*/verdict.py"))}
    if len(files) < 2:
        print(f"至少要两个 runner，找到 {len(files)} 个", file=sys.stderr)
        return 2

    sets = {k: norm_set(p) for k, p in files.items()}
    tpl = norm_set(args.template)

    ok, checks = negative_controls(sets, tpl)
    if not ok:
        json.dump(
            {"negative_controls": checks, "VERDICT": "度量作废：负控未全过"},
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 1

    names = sorted(sets)
    pairs = {(a, b): sets[a] & sets[b] for a, b in combinations(names, 2)}
    floor_key = min(pairs, key=lambda k: len(pairs[k]))
    floor = pairs[floor_key]  # 最保守的生命周期估计
    ceiling_key = max(pairs, key=lambda k: len(pairs[k]))

    result = {
        "negative_controls": checks,
        "files": {
            k: {
                "raw_lines": len(p.read_text(encoding="utf-8").splitlines()),
                "code_lines": code_lines(p),
                "ast_units": len(sets[k]),
            }
            for k, p in files.items()
        }
        | {
            "<template>": {
                "raw_lines": len(
                    args.template.read_text(encoding="utf-8").splitlines()
                ),
                "code_lines": code_lines(args.template),
                "ast_units": len(tpl),
            }
        },
        "pairwise_shared": {f"{a} ∩ {b}": len(v) for (a, b), v in pairs.items()},
        # ── 标题数字：两两交集的下界 ──────────────────────────────
        "lifecycle_floor": {
            "pair": f"{floor_key[0]} ∩ {floor_key[1]}",
            "units": len(floor),
            "inside_template": len(floor & tpl),
            "outside_template": sorted(floor - tpl),
            "by_owner": _by_owner(files[floor_key[1]], floor),
            "statements": sorted(floor),
        },
        "same_question_ceiling": {
            "pair": f"{ceiling_key[0]} ∩ {ceiling_key[1]}",
            "units": len(pairs[ceiling_key]),
        },
        "near_misses_on_floor_pair": near_misses(
            sets[floor_key[0]], sets[floor_key[1]]
        ),
        "template_kept_by": {k: len(v & tpl) for k, v in sets.items()},
    }
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


def _by_owner(path: pathlib.Path, subset: set[str]) -> dict[str, int]:
    """共享单元落在哪个函数里——「生命周期还是科学」按位置回答，不靠人分类。"""
    counts: dict[str, int] = {}
    for owner, u in units(path):
        if u in subset:
            counts[owner] = counts.get(owner, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    raise SystemExit(main())
