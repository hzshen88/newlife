"""`newlife` 命令行。**一个问题一个文件夹，从建到审。**

    newlife init <slug>      建骨架并提交（prereg.md 除外，见 scaffold 模块文档）
    newlife freeze <folder>  冻结判据——这个提交就是「判据早于结果」的时间证明
    newlife run <folder>     跑判定
    newlife check <folder>   三条门：假扫描 · 静默退化 · 预注册↔runner 单元对齐
    newlife audit <folder>   判据没被改过，且产物晚于冻结

**顺序即纪律**：先写判据、再冻结、再跑、最后审。跳过冻结那一步，
结果好不好看都可以事后调判据去迎合——那是 HARKing，且事后无法分辨。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from newlife import scaffold
from newlife.gates import (
    silent_degradation_scan, unit_alignment, vacuous_criterion_scan,
)


def _check(folder: Path) -> int:
    """三条打在**用户自己文件**上的门。

    其余留在 newlife 仓库：`check_goal_ready` 认的是另一套 goal 锚点格式、
    `verify_doc_claims` 要一份验证脚本台账、`run_gates` 的参数是 goal/question/ledger
    三件套——**它们假定了另一套文档流水线**。这不是省略，是归属。
    """
    runner = folder / "verdict.py"
    checks = [
        ("判据恒真（假扫描）", lambda: vacuous_criterion_scan.main([str(runner)])),
        ("静默退化", lambda: silent_degradation_scan.main([str(runner)])),
        ("预注册↔runner 单元对齐", lambda: unit_alignment.main([str(folder)])),
    ]
    failed = []
    for name, run in checks:
        print(f"── {name} " + "─" * max(0, 46 - len(name)))
        if run() != 0:
            failed.append(name)
    print()
    if failed:
        print(f"{len(failed)}/{len(checks)} 条门红：{'、'.join(failed)}")
        return 1
    print(f"全部 {len(checks)} 条门通过。")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="newlife", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="建一个问题文件夹")
    p_init.add_argument("slug", help="如 2026-09-05-yield-input-or-outcome")
    p_init.add_argument("--no-commit", action="store_true",
                        help="不自动提交骨架。**注意：随后 `git add -A` 会锁死冻结能力**")
    for name, help_ in (("freeze", "冻结判据"), ("run", "跑判定"),
                        ("check", "跑门"), ("audit", "审计")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("folder", type=Path, help="问题文件夹")

    args = ap.parse_args(argv)
    cwd = Path.cwd()

    if args.cmd == "init":
        folder = scaffold.init(args.slug, cwd=cwd, commit=not args.no_commit)
        rel = folder.relative_to(scaffold.repo_root(cwd))
        print(f"已建 {rel}/ —— 骨架{'已提交' if not args.no_commit else '未提交'}，"
              f"**prereg.md 刻意没有提交**。\n"
              f"接下来：\n"
              f"  1. 编辑 {rel}/prereg.md 写判据。**每条都要能红。**\n"
              f"  2. newlife freeze {rel}      ← 冻结之前不要提交它\n"
              f"  3. 编辑 {rel}/verdict.py 换成你的世界\n"
              f"  4. newlife run {rel} && git add {rel}/results && git commit\n"
              f"  5. newlife audit {rel}")
        return 0

    folder = args.folder.resolve()
    if not folder.is_dir():
        raise SystemExit(f"{args.folder} 不是一个目录。")
    if args.cmd == "freeze":
        return scaffold.freeze(folder, cwd=cwd)
    if args.cmd == "audit":
        return scaffold.audit(folder, cwd=cwd)
    if args.cmd == "check":
        return _check(folder)
    return subprocess.run([sys.executable, str(folder / "verdict.py")]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
