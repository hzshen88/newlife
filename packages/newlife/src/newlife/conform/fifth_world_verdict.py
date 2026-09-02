"""第五世界的 verdict runner：从 47 行分类表机械合取出 H1 / H0 / Invalid。

判据冻结于 exloop 的 plan §1 与 question §2.3：

- **H1**：47 个 check 全部落入 `auto` / `hand` / `anchored`，`hollow` 计数为 **0**
- **H0**：至少一个 `hollow`
- **Invalid**：出现未讨清的 `IC-1`，或分类不覆盖全部 47 个

**verdict 从合取机械算出，从不手填。** goal 的达成判定是另一回事，不在这里产生。
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

VALID = {"auto", "hand", "anchored", "hollow", "IC-1"}
EXPECTED_TOTAL = 47


def compute(rows: list[dict]) -> dict:
    counts = Counter(r["class"] for r in rows)
    unknown = sorted({r["class"] for r in rows} - VALID)
    ic1 = [r for r in rows if r["class"] == "IC-1"]
    hollow = [r for r in rows if r["class"] == "hollow"]

    complete = len(rows) == EXPECTED_TOTAL
    every_row_has_evidence = all(r.get("evidence") for r in rows)
    no_unknown_class = not unknown
    no_ic1 = not ic1

    invalid = not (complete and every_row_has_evidence and no_unknown_class and no_ic1)
    h1 = bool(not invalid and not hollow)
    h0 = bool(not invalid and hollow)

    return {
        "schema": "newlife.fifth-world.gate.v1",
        "total_checks": len(rows),
        "expected_total": EXPECTED_TOTAL,
        "counts": dict(sorted(counts.items())),
        "unknown_classes": unknown,
        "completeness": complete,
        "every_row_has_evidence": every_row_has_evidence,
        "no_unresolved_ic1": no_ic1,
        "hollow": [{"script": r["script"], "check": r["check"],
                    "evidence": r["evidence"]} for r in hollow],
        "verdict": "Invalid" if invalid else ("H0" if h0 else "H1"),
        "passed": h1,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--classification", required=True, type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    rows = json.loads(args.classification.read_text())["rows"]
    summary = compute(rows)

    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    for k, v in summary["counts"].items():
        print(f"  {k:10s} {v}")
    print(f"  完整性 {summary['completeness']} · 每行有证据 {summary['every_row_has_evidence']}"
          f" · 无未讨清 IC-1 {summary['no_unresolved_ic1']}")
    for h in summary["hollow"]:
        print(f"  hollow → {h['script']}:{h['check']} —— {h['evidence']}")
    print(f"verdict: {summary['verdict']}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
