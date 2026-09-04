"""门的自检：拿已知的坑做变异注入，要求门真的红。

**门用来替代人工核对，所以「门对不对」成了新的关键**——漏一类检查，下游全绿也是假绿。
规矩：**新坑出现时先把它加进 FIXTURES（红），再改门（绿）。** 就是 TDD，
只不过被测对象是审核本身。

## 覆盖面，写明边界

本文件覆盖 **12 条工具层 fixture**（`doc` 与 `gate` 两层）——测的是**门的机制**：
锚解析、台账比对、追溯链、冻结哈希、词表封闭、goal 就绪。它们打在
`scripts/gates/corpus/` 这份随库发布的最小语料上。

**另有 9 条 `script` 层 fixture 留在 `exloop`**（重放那个仓库几个验证脚本的历史
科学 bug：Moran 网格 ceil/floor、pair-weight 同函数比较、`moran_plan_grid` 的 IC-1
hollow）。**它们测的是那些脚本，不是这些门**，所以不随库发布。
**这不是省略，是归属**——本文件末尾会把这条打印出来。

## 边界，必须写明

FIXTURES 只包含**已经犯过的错**。全新类型的错误，门抓不住，这里也没有——
任何基于历史的防御都有这个性质，不可消除。

    python3 scripts/gates/gate_selftest.py
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
GATES = ROOT / "scripts/gates"
CORPUS = pathlib.Path(__file__).resolve().parent / "corpus"   # **不能放 examples/**：那层有条冻结的 v0.2 门——
                            # 应用层是配置数据，任何 Python 都算违规。语料带脚本。
QUESTION = "questions/example.md"
GOAL = "goals/example.md"
LEDGER = "verification/checks.json"

# ── 12 条工具层 fixture。origin 是它在本项目真实发生过的那次 ──────────
FIXTURES = [
    dict(id="F3", origin="第 5、6 轮红队：文档声称某 check 覆盖了 A 函数，"
                         "而运行时观测到的是 B——covers 是观测，不是声明。",
         mutate=(QUESTION, "covers=drift-->", "covers=endpoint-->"), red="claims"),
    dict(id="F4", origin="v0.3 冻结的 prereg 把 '7 units' 写成 9——数字抄错，"
                         "冻结后只能靠 implementation-log 更正。",
         mutate=(QUESTION, "path_len=13", "path_len=12"), red="claims"),
    dict(id="F5", origin="引用一个不存在的 check——手滑，或脚本重构后编号变了"
                         "而文档没跟。",
         mutate=(QUESTION, "<!--@check-1:", "<!--@check-99:"), red="claims"),
    dict(id="F6", origin="第三世界正文里真躺过一个过期的 SHA-256：锚里是新的，"
                         "散文里是旧的。同一事实写了两遍，第二遍漂移了。",
         # **不写死哈希字面量**——语料一改它就失配，起草时正是这么断的。
         mutate=(QUESTION, "<!--@script: sha256=", "<!--@script: sha256=dead"),
         red="claims"),
    dict(id="F7", origin="goal 的某条达成判据没有任何下游落点——这一层没兑现上一层，"
                         "而收尾时才发现。",
         mutate=(QUESTION, "<!--@goal: C3-->", ""), red="trace"),
    dict(id="F8", origin="World 2 的 plan 在第二轮红队时补进了 prereg 里没有的东西，"
                         "两份文档从此说了不一样的话。",
         mutate=(QUESTION, "<!--@goal: C2-->", "<!--@goal: C2--><!--@goal: C9-->"),
         red="trace"),
    dict(id="F17", origin="外审发现：goal 写「取值只有四个」，下游却又定义了第五种"
                          "结局——词表被下游偷偷扩了。",
         mutate=(QUESTION, "<!--@outcome: C1=constant-->",
                 "<!--@outcome: C1=constant--><!--@outcome: C1=deferred-->"),
         red="vocab"),
    dict(id="F15", origin="外审用 git log 实测发现：goal 状态行写着 frozen，"
                          "而内容在冻结之后被改过。",
         mutate=(GOAL, "**封闭意味着不许扩。**",
                 "**封闭意味着不许扩。** # MUTANT：冻结后偷偷加了一句"),
         red="frozen"),
    dict(id="F21", origin="用户追问「skill 里写了为什么没执行」：选题第 3 步文献检索"
                          "抓取全部失败，于是跳过继续，**下游没有任何东西发现**。"
                          "skill 是提醒，没有强制力。",
         mutate=(GOAL, "<!--@evidence:", "<!--@evidence_REMOVED:"), red="goal_ready"),
    dict(id="F21b", origin="2026-09-04 新增三个锚时的负控：说不出「谁会改变做法」，"
                           "就是「不重要但可判定」那一档——它能过后面所有的门。",
         mutate=(GOAL, "<!--@who_changes_behavior:", "<!--@who_REMOVED:"),
         red="goal_ready"),
    dict(id="F14", origin="第五世界选题时发现：mutation_scan 的正则抽不到 check 标签，"
                          "**空集上「每个 check 都被抓住」恒真**——假绿。",
         mutate=("__gate__/mutation_scan.py",
                 'r"^\\[([^\\]]+)\\].*--\\s*(?:PASS|FAIL)$"', 'r"^\\[(check [^\\]]+)\\]"'),
         red="mutscan_selftest"),
    dict(id="F18", origin="第二轮外审直接调用 frozen_normalise 做出了真实哈希碰撞："
                          "首版按「整行含 @frozen 子串就整行剔除」，任何含该串的行都被吞。",
         # **忠实重现那次的错**：整行剔除，不是 span 剔除。
         # 起草时先写成「剔掉全部锚」——那仍是 span 精确的，P1/P2 都还成立，
         # 于是这条 fixture 打了空。**用一个检测不出东西的变异去判定通过，
         # 正是本项目栽过两次的那件事。**
         mutate=("__gate__/verify_doc_claims.py",
                 "    return ANCHOR_RE.sub(",
                 '    return "\\n".join(  # MUTANT：退回整行剔除\n'
                 '        ln for ln in text.splitlines() if "@frozen:" not in ln)\n'
                 "    return ANCHOR_RE.sub("),
         red="frozen_selftest"),
]

# ── 反向对照：下游还没起草时，追溯链必须报 PENDING 且 exit 0 ────────
GREEN_FIXTURE = dict(
    id="F9",
    origin="第四世界干跑当场发现：goal 刚写完、question 还没起草时，追溯链把每条 "
           "criterion 报成 FAIL。**一个总是红的检查会训练人忽略红色，那比漏检更危险。**",
    red=None)


def _run(component: str, work: pathlib.Path) -> int:
    gates = work / "__gate__"
    q, g, led = work / QUESTION, work / GOAL, work / LEDGER
    cmds = {
        "claims": [gates / "verify_doc_claims.py", "--ledger", led, q],
        "trace": [gates / "verify_doc_claims.py", "--trace", f"goal={g}", q],
        # `--vocabulary` 是独立 flag，不在 `--trace` 里；`frozen` 锚只在带 `--ledger`
        # 的那条路径上被检查。**起草时两处都调错了，于是两条 fixture 打了空——
        # 「变异之后仍然绿」当场把它报出来了，这正是这套自检存在的理由。**
        "vocab": [gates / "verify_doc_claims.py", "--vocabulary", f"goal={g}", q],
        "frozen": [gates / "verify_doc_claims.py", "--ledger", led, g],
        "goal_ready": [gates / "check_goal_ready.py", g],
        "frozen_selftest": [gates / "verify_doc_claims.py", "--selftest"],
        # **必须传目标脚本**。起草时写成 `--selftest`（它没有这个 flag），
        # 于是 F14 是靠 argparse 报错变红的，不是靠变异被抓住——
        # 「用一个检测不出东西的东西判定通过」的又一次。
        "mutscan_selftest": [gates / "mutation_scan.py",
                              work / "verification/example_check.py", "--quiet"],
    }[component]
    return subprocess.run([sys.executable, *map(str, cmds)],
                          cwd=work, capture_output=True, text=True).returncode


def _workspace() -> pathlib.Path:
    work = pathlib.Path(tempfile.mkdtemp(prefix="_gate_selftest_"))
    shutil.copytree(CORPUS, work, dirs_exist_ok=True)
    shutil.copytree(GATES, work / "__gate__", dirs_exist_ok=True)
    return work


def main() -> int:
    failures: list[str] = []

    # 前提：未变异时全绿。不成立就谈不上「变异让它变红」。
    base = _workspace()
    for comp in ("claims", "trace", "frozen", "goal_ready"):
        if _run(comp, base) != 0:
            failures.append(f"前提不成立：未变异时 {comp} 就是红的")
    shutil.rmtree(base)

    for fx in FIXTURES:
        work = _workspace()
        path, old, new = fx["mutate"]
        target = work / path
        text = target.read_text()
        if old not in text:
            failures.append(f"{fx['id']}: 变异锚点在语料里找不到 —— {old[:40]!r}")
            shutil.rmtree(work)
            continue
        target.write_text(text.replace(old, new, 1))
        code = _run(fx["red"], work)
        if code == 0:
            failures.append(f"{fx['id']}: 变异之后 {fx['red']} 仍然绿 —— 这一格测不出东西")
        else:
            print(f"  [红] {fx['id']:5s} {fx['red']:18s} {fx['origin'][:44]}")
        shutil.rmtree(work)

    # 反向对照：下游缺席时必须 PENDING 而不是 FAIL
    work = _workspace()
    (work / QUESTION).unlink()
    code = subprocess.run(
        [sys.executable, str(work / "__gate__/verify_doc_claims.py"),
         "--trace", f"goal={work / GOAL}", str(work / GOAL)],
        cwd=work, capture_output=True, text=True).returncode
    if code != 0:
        failures.append(f"{GREEN_FIXTURE['id']}: 下游缺席时追溯链报红 —— "
                        "总是红的检查会训练人忽略红色")
    else:
        print(f"  [绿] {GREEN_FIXTURE['id']:5s} {'trace(下游缺席)':18s} "
              f"{GREEN_FIXTURE['origin'][:44]}")
    shutil.rmtree(work)

    print(f"\n随库发布的工具层 fixture：{len(FIXTURES)} 条变异 + 1 条反向对照")
    print("另有 9 条 script 层 fixture 留在 exloop —— 它们重放的是那个仓库几个验证"
          "脚本的历史科学 bug，测的是那些脚本，不是这些门。**归属，不是省略。**")
    if failures:
        print("\n自检失败：")
        for f in failures:
            print(f"  {f}")
        return 1
    print("\n自检通过：全部变异让门变红，反向对照未误报。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
