"""`newlife` 命令行。**一个问题一个文件夹，从建到审。**

    newlife init <slug>      建骨架并提交（prereg.md 除外，见 scaffold 模块文档）
    newlife freeze <folder>  冻结判据——这个提交就是「判据早于结果」的时间证明
    newlife run <folder>     跑判定
    newlife check <folder>   三条门：假扫描 · 静默退化 · 预注册↔runner 单元对齐
    newlife blocks           列出这个环境里可接入的第三方积木
    newlife skills install   把提问与写判据的 skill 装进你的 AI 配置目录
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


SKILLS = Path(__file__).resolve().parent / "skills"


def _blocks() -> int:
    """列出可接入的积木。**装完 wheel 之后用户无从知道手上有什么**，这是补那个洞。"""
    from newlife.adapters.process_bigraph import discovery   # 惰性：没装 extra 也能用别的子命令

    count = 0
    for top, module, names in discovery.blocks():
        if not names:
            print(f"[{top}] {module}")            # import 失败，照实报
            continue
        count += len(names)
        print(f"  {module:52s} {', '.join(names)}")
    print(f"\n{count} 个可接入的 Process/Step。**能不能接进来还要看它的 `update` "
          f"返回什么形状**——那由 admit() 在运行时硬失败，这里不假装检查过。")
    return 0


def _skills(args) -> int:
    """把 skill 拷进 AI 的配置目录。**逐字拷贝，不做任何变换**——

    母本与部署副本是同一份文件。「两份会漂移」是这个项目反复付过学费的形状：
    skill 教用户跑一个库还没有的命令，而没有任何机械防线能发现。
    """
    sources = sorted(p for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())
    if args.action == "path":
        for s in sources:
            print(s / "SKILL.md")
        return 0

    args.dest.mkdir(parents=True, exist_ok=True)
    skipped = []
    for src in sources:
        target = args.dest / src.name / "SKILL.md"
        body = (src / "SKILL.md").read_bytes()
        if target.exists() and target.read_bytes() != body and not args.force:
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        print(f"  装好 {target}")
    for t in skipped:
        print(f"  跳过 {t} —— 已存在且内容不同。**不覆盖你改过的东西**；"
              f"确认要覆盖就加 --force")
    print(f"\n用别的 AI 的话：`newlife skills path` 打印母本路径，整份贴进去即可。")
    return 1 if skipped else 0


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
    sub.add_parser("blocks", help="列出可接入的第三方积木")
    p_sk = sub.add_parser("skills", help="装 skill 到 AI 配置目录")
    p_sk.add_argument("action", choices=("install", "path"))
    p_sk.add_argument("--dest", type=Path, default=Path.home() / ".claude/skills",
                      help="装到哪（默认 ~/.claude/skills）")
    p_sk.add_argument("--force", action="store_true",
                      help="目标已存在且内容不同时才需要——**默认不覆盖你改过的东西**")

    args = ap.parse_args(argv)
    cwd = Path.cwd()

    if args.cmd == "blocks":
        return _blocks()
    if args.cmd == "skills":
        return _skills(args)
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
