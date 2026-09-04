#!/usr/bin/env python3
"""预注册声明的判定单元，与 runner 实际算出的，必须逐个对上。

## 这条门为什么存在

用户仓库形态第一次实测走通时，有一步是**手工**做的：把 `prereg.md` §2 表格里的
单元名，和 runner 输出的 `units` 键一个一个对上。**没有任何东西检查这件事。**

于是这个洞是敞开的：

    预注册写  verdict = S0 ∧ S1 ∧ S2 ∧ S3
    runner 只算了三个 —— **没人会发现**

这与第十九个里程碑的 Z5 同一族：**判据在纸上，判定力不在代码里**。
Z5 是「算了但恒真」，这是「声明了但没算」。两者都让合取看起来更强。

反向同样要查：**产物里有一个预注册没声明的单元** —— 那是事后加进来的判据，
即 HARKing 的单元版本。

## 三条检查

1. `prereg.md` §2 表格里的单元 == 合取式 `verdict = …` 里的单元
2. 声明的单元 == 产物里实际算出的单元
3. `S0` 特殊：它落在 `reproduction.json`，不在 `summary.json`（自我复现的记录
   不能放进被它复现的那份文件）——两处合起来算「产物里有的」

    python -m newlife.gates.unit_alignment <问题文件夹>
    python -m newlife.gates.unit_alignment --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Iterable

TABLE_ROW = re.compile(r"^\|\s*\*\*([A-Z]+\d+)\*\*\s*\|")
CONJUNCTION = re.compile(r"verdict\s*=\s*([^。\n]*)")
UNIT_TOKEN = re.compile(r"\b([A-Z]+\d+)\b")        # 散文里：S0 ∧ S1 ∧ …
# JSON 键里：`S1_env_unchanged`。**不能用 `\b`**——`1` 与 `_` 之间没有词边界，
# 于是一个都匹配不到，而「产物里一个单元都没有」看起来像是 runner 没算。
# 起草时就是这么错的，四条单元全被报成缺失。**检查太笨和检查太弱是同一个病的两面。**
UNIT_KEY = re.compile(r"^([A-Z]+\d+)(?:_|$)")


def declared(prereg_text: str) -> tuple[set[str], set[str]]:
    """(表格里声明的单元, 合取式里出现的单元)。"""
    # silent-degradation: ok —— 逐行筛选：不是表格行就跳过是本函数的正常分支。
    # 「一行都没匹配上」这个聚合结果由 `check()` 显式硬报（空表格 → 直接红）。
    table = {m.group(1) for line in prereg_text.splitlines()
             if (m := TABLE_ROW.match(line))}
    conj: set[str] = set()
    # silent-degradation: ok —— 同上，找不到合取式由 `check()` 报成「表格有而合取式没有」。
    for m in CONJUNCTION.finditer(prereg_text):
        conj |= set(UNIT_TOKEN.findall(m.group(1)))
    return table, conj


def units_in(keys: Iterable[str]) -> set[str]:
    """从一批 JSON 键里认出单元名。**单独抽出来，好让自检直接测它。**"""
    # silent-degradation: ok —— `schema`/`provenance` 这些键本来就不是单元名。
    # 「一个都没认出来」由 `check()` 显式硬报，且措辞刻意区别于「判据没算」。
    return {m.group(1) for k in keys if (m := UNIT_KEY.match(k))}


def produced(folder: pathlib.Path) -> set[str]:
    """产物里实际算出的单元。**两个文件合起来看**，S0 在 reproduction 那边。"""
    found: set[str] = set()
    for name in ("summary.json", "reproduction.json"):
        path = folder / "results" / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        found |= units_in(list(data.get("units", {})) + list(data))
    return found


def check(table: set[str], conj: set[str], made: set[str]) -> list[str]:
    """**纯谓词** —— 所以能拿合成输入证明它会红（见 `_selftest`）。"""
    problems = []
    if not table:
        problems.append("prereg.md §2 里一个判定单元都没解析到 —— "
                        "表格行的形状必须是 `| **S1** | … |`。**空集上「全都对上了」恒真。**")
        return problems
    for missing in sorted(table - conj):
        problems.append(f"{missing}：表格里声明了，**合取式 `verdict = …` 里没有**"
                        f" —— 它不参与判定，等于没写")
    for extra in sorted(conj - table):
        problems.append(f"{extra}：合取式里出现，**表格里没有定义** —— 没人知道它是什么")
    if not made:
        problems.append("产物里一个判定单元都没解析到 —— 要么 runner 还没跑过，"
                        "要么 `units` 的键不是 `S1_…` 这种形状。**这不等于"
                        "「每条判据都没算」**：起草时解析器错了一个字符，"
                        "四条单元全被报成缺失，诊断把人指向了完全错的地方。")
        return problems
    for missing in sorted(table - made):
        problems.append(f"{missing}：预注册声明了，**产物里没有** —— "
                        f"判据在纸上，判定力不在代码里")
    for extra in sorted(made - table):
        problems.append(f"{extra}：产物里算了，**预注册没声明** —— "
                        f"事后加进来的判据，即 HARKing 的单元版本")
    return problems


SELFTEST_PREREG = """
| **S0** | 自我复现 | … |
| **S1** | 环境未变 | … |
| **S2** | 正控 | … |

**verdict = S0 ∧ S1 ∧ S2。**
"""


def _selftest() -> int:
    """负控：四种错各造一次都要红，全对的绿；**外加两条解析器自身的断言**。

    第一版只测 `check()`，不测解析器——而起草时真正犯的错在 `produced()` 里
    （`\b` 在 `S1_env_unchanged` 的 `1` 与 `_` 之间不成立，一个键都认不出，
    四条单元全被报成缺失）。**只测判定逻辑、不测解析，就是检查太弱。**
    """
    ok = True
    if units_in(["S1_env_unchanged", "S0_byte_identical_on_rerun", "schema"]) != {"S0", "S1"}:
        print("  [失败] 认不出 JSON 键里的单元名"); ok = False
    if declared(SELFTEST_PREREG) != ({"S0", "S1", "S2"}, {"S0", "S1", "S2"}):
        print("  [失败] 认不出 prereg 表格或合取式里的单元名"); ok = False
    print(f"  [{'绿' if ok else '红'}] 解析器：JSON 键与 prereg 表格/合取式")

    full = {"S0", "S1", "S2"}
    cases = [
        ("全部对上", full, full, full, False),
        ("声明了但没算", full, full, {"S0", "S1"}, True),
        ("算了但没声明", {"S0", "S1"}, {"S0", "S1"}, full, True),
        ("表格有而合取式没有", full, {"S0", "S1"}, full, True),
        ("解析不到任何单元", set(), full, full, True),
        ("产物里一个单元都没有", full, full, set(), True),
    ]
    for name, table, conj, made, want_red in cases:
        red = bool(check(table, conj, made))
        mark = "红" if red else "绿"
        if red != want_red:
            print(f"  [失败] {name}：得到{mark}，应为{'红' if want_red else '绿'}")
            ok = False
        else:
            print(f"  [{mark}] {name}")
    print("  自检通过：解析器正确，四种错都红，全对的绿。" if ok else "  自检失败。")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.folder is None:
        ap.error("要么给一个问题文件夹，要么 --selftest")

    prereg = args.folder / "prereg.md"
    if not prereg.exists():
        print(f"{prereg} 不存在 —— 这不是一个问题文件夹。")
        return 1
    table, conj = declared(prereg.read_text())
    made = produced(args.folder)
    problems = check(table, conj, made)
    for p in problems:
        print(f"{args.folder}: {p}")
    if problems:
        print(f"\n{len(problems)} 处不对齐。**预注册说的和代码做的必须一字对上**——"
              f"差一个单元，合取就比它看起来的弱。")
        return 1
    print(f"{args.folder}: 判定单元对齐 —— 声明 {len(table)} 个"
          f"（{' '.join(sorted(table))}），产物里逐个都在。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
