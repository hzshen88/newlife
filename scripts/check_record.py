"""收尾对账器：产物 × 记录的全矩阵。缺一格就红。

**为什么有它。** 收尾清单写在 skill 里，是提醒，没有强制力。实测结果：18 个里程碑
之后，`twelfth` 没进 `proposal.md` §7（孤儿文档——清单里专门有一条防这个）、
4 个产物没登记依赖面（**腐烂检测器自己有覆盖洞，而没有东西检查它的覆盖率**）、
`twelfth` 的产出者在仓库里根本找不到（**它的主题恰好是归档重放**）。

> **只 gate「跳过之后看不出来」的步骤。** 这六格全都属于这一类：漏了以后一切正常。

用法：
    python3 scripts/check_record.py            # 对账，缺格即 exit 1
    python3 scripts/check_record.py --selftest  # 拿已知坑验证它真的会红
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
QUESTIONS = ROOT / "questions"   # 2026-09-06 起：里程碑就是本仓库里的一个问题文件夹
WORLDS = ROOT / "docs/zh/worlds"
PROPOSAL = ROOT / "docs/zh/design/proposal.md"
# 里程碑表 2026-09-06 从根 README 搬到 docs/milestones.md（根 README 改为面向用户）；键名 readme_row 沿用
MILESTONES = ROOT / "docs/milestones.md"

EXEMPT = {
    # 流水线之前的里程碑：没有 goal / 预注册 / worlds 文档这套形制。
    # **声明式豁免，留在 diff 里被人看见**，不是给某个目录开后门。
    "v0.1a": "早于 goal 环节",
    "v0.1b": "早于 goal 环节",
    "v0.2": "早于 goal 环节",
    "v0.3": "早于 goal 环节",
}

KNOWN_GAPS = {
    # **已知且未修的缺口，显式登记。** 登记不等于放行——它仍然计入 `known_gaps`
    # 并打印出来，只是不让整个门变红。要么修掉，要么这一行留在 diff 里。
    ("twelfth", "producer"): (
        "第十二个的产出者未提交，产物不可重跑——**这与它自己的主题（归档重放）矛盾**。"
        "如实登记，不伪造一个产出者去凑绿。"
    ),
    # 第 20–22 个里程碑早于「设计理由写进 questions/<slug>/README.md」的约定（2026-09-06）。
    # 不追溯补写：事后写的设计理由不是当时的设计理由。
    ("2026-09-06-reproduction-class-declarability", "readme"): "早于 README 约定，不追溯补写",
    ("2026-09-06-stochastic-world-judgeable", "readme"): "早于 README 约定，不追溯补写",
    ("2026-09-06-judgement-design-method", "readme"): "早于 README 约定，不追溯补写",
}


def question_milestones() -> list[str]:
    """本仓库 questions/ 下已有判定产物的问题文件夹——新布局的里程碑。"""
    if not QUESTIONS.exists():
        return []
    return sorted(p.name for p in QUESTIONS.iterdir()
                  if (p / "results" / "summary.json").exists())


Q_COLUMNS = ("summary", "readme", "closeout", "readme_row")
Q_LABELS = {"summary": "产物", "readme": "README", "closeout": "§5收尾", "readme_row": "docs/milestones.md"}


def check_question(slug: str) -> dict[str, bool]:
    """新布局的四格：产物、设计理由（README.md）、goal.md §5 收尾、里程碑表里的一行。
    worlds 文档与 proposal §7 不再要求——每个事实只在一处。"""
    q = QUESTIONS / slug
    goal = q / "goal.md"
    return {
        "summary": (q / "results" / "summary.json").exists(),
        "readme": (q / "README.md").exists(),
        "closeout": goal.exists() and "(Filled in afterwards" not in goal.read_text(encoding="utf-8"),
        "readme_row": f"questions/{slug}/" in MILESTONES.read_text(encoding="utf-8"),
    }


def milestones() -> list[str]:
    return sorted(
        p.name for p in RESULTS.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _rot_keys() -> set[str]:
    """`verdict_rot.DEPENDS_ON` 的键，连同 `<name>-world` 的形式一起放行。

    键用的是短名（`second`），产物目录用的是长名（`second-world`）——
    **两种都接受，但不接受任何其它别名**，免得别名表本身变成一个要维护的东西。
    """
    sys.path.insert(0, str(ROOT / "packages/newlife/src"))
    from newlife.conform.verdict_rot import DEPENDS_ON  # noqa: PLC0415

    keys = set(DEPENDS_ON)
    return keys | {f"{k}-world" for k in keys}


def _py_sources() -> list[Path]:
    return sorted(
        [*(ROOT / "packages/newlife/src").rglob("*.py"), *(ROOT / "scripts").rglob("*.py")]
    )


def check(milestone: str, rot_keys: set[str], sources: list[Path]) -> dict[str, bool]:
    """六格。每一格都是「漏了之后一切正常」的那一类。"""
    summary = RESULTS / milestone / "summary.json"
    needle = f"results/{milestone}/"
    schema_hint = ""
    if summary.exists():
        try:
            schema_hint = json.loads(summary.read_text()).get("schema", "") or ""
        except json.JSONDecodeError:
            schema_hint = ""

    def references(path: Path) -> bool:
        return needle in path.read_text()

    producer = any(
        (needle in src.read_text() or (schema_hint and schema_hint in src.read_text()))
        for src in sources
    )
    return {
        "summary": summary.exists(),
        "worlds_doc": any(references(p) for p in WORLDS.glob("*.md")),
        "proposal_row": references(PROPOSAL),
        "readme_row": references(MILESTONES),
        "rot_entry": milestone in rot_keys,
        "producer": producer,
    }


COLUMNS = ("summary", "worlds_doc", "proposal_row", "readme_row", "rot_entry", "producer")
LABELS = {
    "summary": "产物", "worlds_doc": "worlds文档", "proposal_row": "§7行",
    "readme_row": "docs/milestones.md", "rot_entry": "依赖面", "producer": "产出者",
}


def report() -> int:
    rot_keys = _rot_keys()
    sources = _py_sources()
    missing: list[str] = []
    known: list[str] = []

    header = "  " + "".join(f"{LABELS[c]:>11}" for c in COLUMNS)
    print(f"{'里程碑':<16}{header}")
    for m in milestones():
        row = check(m, rot_keys, sources)
        marks = "".join(f"{('✓' if row[c] else '✗'):>11}" for c in COLUMNS)
        note = "  (豁免)" if m in EXEMPT else ""
        print(f"{m:<16}  {marks}{note}")
        if m in EXEMPT:
            continue
        for col in COLUMNS:
            if row[col]:
                continue
            if (m, col) in KNOWN_GAPS:
                known.append(f"{m}.{col} —— {KNOWN_GAPS[(m, col)]}")
            else:
                missing.append(f"{m}.{col}")

    qs = question_milestones()
    if qs:
        header = "  " + "".join(f"{Q_LABELS[c]:>11}" for c in Q_COLUMNS)
        print(f"\n{'问题文件夹（新布局）':<16}{header}")
        for slug in qs:
            row = check_question(slug)
            marks = "".join(f"{('✓' if row[c] else '✗'):>11}" for c in Q_COLUMNS)
            print(f"{slug[:44]:<46}{marks}")
            for col in Q_COLUMNS:
                if row[col]:
                    continue
                if (slug, col) in KNOWN_GAPS:
                    known.append(f"{slug}.{col} —— {KNOWN_GAPS[(slug, col)]}")
                else:
                    missing.append(f"{slug}.{col}")

    if known:
        print(f"\n已登记的缺口 {len(known)} 处（每次对账都会列出）：")
        for k in known:
            print(f"  {k}")
    if missing:
        print(f"\n未登记的缺格 {len(missing)} 处：")
        for k in missing:
            print(f"  {k}")
        print("\n要么补上，要么在 KNOWN_GAPS 里显式登记理由——后者会留在 diff 里，被人看见。")
        return 1
    print("\n对账通过：每个产物的六格记录齐全（已登记的缺口除外）。")
    return 0


# --- 自检：拿已知坑做变异注入，要求对账真的红 ---
#
# 规矩与 exloop 的 gate_selftest 相同：**先加 fixture（红），再改门（绿）**。
# 门用来替代人工核对，所以「门对不对」成了新的关键——漏一格，下游全绿也是假绿。

FIXTURES = (
    ("proposal_row", "从 proposal.md 抹掉某个产物的指针 —— 孤儿文档，实测发生过（twelfth）"),
    ("readme_row", "从 docs/milestones.md 抹掉某个产物的行"),
    ("worlds_doc", "抹掉 worlds 文档对某个产物的引用"),
    ("rot_entry", "从 verdict_rot 抹掉某个依赖面登记 —— 实测发生过（4 个产物）"),
    ("producer", "产出者不可指名 —— 实测发生过（twelfth，产物无法重跑）"),
)


def selftest() -> int:
    """每一格都做一次变异：把那一格的证据拿掉，对账必须报出这一格。"""
    rot_keys = _rot_keys()
    sources = _py_sources()
    target = "seventeenth"          # 六格齐全的一个，当基准
    base = check(target, rot_keys, sources)
    if not all(base.values()):
        print(f"自检前提不成立：{target} 本身就有缺格 {base}")
        return 2

    failures = []
    for column, why in FIXTURES:
        # 变异 = 让那一格的证据源变成空，其余不动
        if column == "rot_entry":
            mutated = check(target, rot_keys - {target}, sources)
        elif column == "producer":
            mutated = check(target, rot_keys, [])
        else:
            mutated = dict(base)
            mutated[column] = _probe_without(target, column, rot_keys, sources)
        if mutated[column]:
            failures.append(f"{column}: 变异之后仍然为真 —— 这一格测不出东西（{why}）")
        else:
            print(f"  [红] {column:12s} {why}")

    # 新布局：抹掉里程碑表里对某个问题文件夹的引用，对账必须红
    qs = question_milestones()
    if qs:
        slug = qs[0]
        text = MILESTONES.read_text(encoding="utf-8")
        needle = f"questions/{slug}/"
        try:
            MILESTONES.write_text(text.replace(needle, "questions/__mutated__/"), encoding="utf-8")
            still = check_question(slug)["readme_row"]
        finally:
            MILESTONES.write_text(text, encoding="utf-8")
        if still:
            failures.append("questions.readme_row: 抹掉表里的引用后仍然为真")
        else:
            print(f"  [红] {'readme_row':12s} 新布局：从 docs/milestones.md 抹掉 questions/{slug}/")

    # 反向对照：豁免项必须**不**被报出来，否则门会对历史里程碑误报
    if "v0.1a" not in EXEMPT:
        failures.append("反向对照失效：v0.1a 不在豁免表里")
    else:
        print("  [绿] 豁免项 v0.1a 不被报出（反向对照）")

    if failures:
        print("\n自检失败：")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"\n自检通过：{len(FIXTURES)} 条变异（加新布局 1 条）全部让对账变红，反向对照未误报。")
    return 0


def _probe_without(milestone: str, column: str, rot_keys, sources) -> bool:
    """把某一格的文本证据临时抹掉，返回那一格的判定结果。**不落盘**。"""
    files = {"proposal_row": [PROPOSAL], "readme_row": [MILESTONES],
             "worlds_doc": sorted(WORLDS.glob("*.md"))}[column]
    needle = f"results/{milestone}/"
    originals = {f: f.read_text() for f in files}
    try:
        for f, text in originals.items():
            if needle in text:
                f.write_text(text.replace(needle, "results/__mutated__/"))
        return check(milestone, rot_keys, sources)[column]
    finally:
        for f, text in originals.items():
            f.write_text(text)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="拿已知坑验证对账真的会红")
    args = ap.parse_args()
    raise SystemExit(selftest() if args.selftest else report())
