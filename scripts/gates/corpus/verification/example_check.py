"""示例验证脚本 —— 门的自检语料，同时是给用户抄的最小样板。

**它故意很小很笨**：一个生产函数 + 四条 check。真实问题的脚本会更大，
但形状就是这个：`report()` 带 `facts=`（值取自 check 自己算出的变量，不重新推导）、
生产函数过运行时插桩（`covers` 由观测得出，不是手写声明）、`--emit-json` 无时间戳
（确定性，可 commit、diff 干净）。

    python3 example_check.py                       # 人看
    python3 example_check.py --emit-json checks.json   # 给门看
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

_INSTRUMENTED = ["drift", "endpoint"]
"""生产函数由脚本**自己声明**，不由 mutation_scan 猜——它据此做变异注入。"""

OBSERVED: set[str] = set()
CHECKS: list[dict] = []


def _instrument(*names: str) -> None:
    """把生产函数包一层，被调用就记下来——`covers` 因此是**观测**不是声明。"""
    module = sys.modules[__name__]
    for name in names:
        original = getattr(module, name)

        def wrapped(*a, _f=original, _n=name, **k):
            OBSERVED.add(_n)
            return _f(*a, **k)

        setattr(module, name, wrapped)


# ── 生产代码：一个只有两行的「模型」 ──────────────────────────────
def drift(start: int, steps: int) -> list[int]:
    """每步 +2 的确定性漂移。**故意平凡**——语料要的是形状，不是科学。"""
    return [start + 2 * i for i in range(steps + 1)]


def endpoint(start: int, steps: int) -> int:
    return drift(start, steps)[-1]


def report(cid: str, passed: bool, detail: str, facts: dict[str, str]) -> None:
    CHECKS.append({"id": cid, "passed": passed, "detail": detail,
                   "facts": facts, "covers": sorted(OBSERVED)})
    OBSERVED.clear()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-json", type=pathlib.Path)
    args = ap.parse_args()
    _instrument("drift", "endpoint")

    path = drift(0, 12)
    report("check-1", len(path) == 13, f"轨迹长度 {len(path)}",
           {"path_len": str(len(path))})

    end = endpoint(0, 12)
    report("check-2", end == 24, f"末态 {end}", {"endpoint": str(end)})

    # **三条，不是四条。** 原本有第四条「起点平移后的末态」，但 mutation_scan
    # 报它「未被触及」——本工具只变异单行 return，而那条判据无论怎么改都能同变。
    # **判据要挑变异碰得到的**；碰不到就得手工构造一个会红的变异，做不到才是空洞。
    gaps = {b - a for a, b in zip(path, path[1:])}
    report("check-3", gaps == {2}, f"步长集合 {sorted(gaps)}",
           {"distinct_gaps": str(len(gaps))})

    source = pathlib.Path(__file__).read_text()
    ledger = {
        "schema": "newlife.verification.checks.v1",
        "script": pathlib.Path(__file__).name,
        "script_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "all_passed": all(c["passed"] for c in CHECKS),
        "failed": [c["id"] for c in CHECKS if not c["passed"]],
        "checks": CHECKS,
    }
    for c in CHECKS:
        print(f"[{c['id']}] {c['detail']} -- {'PASS' if c['passed'] else 'FAIL'}")
    if args.emit_json:
        args.emit_json.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
        print(f"ledger: {args.emit_json}")
    return 0 if ledger["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
