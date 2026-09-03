"""第八世界的 verdict runner：通用 harness 有没有把 World 4 的手写代码吃到零。

判据冻结于 exloop 的预注册（freeze commit `6f2bc25`）。三条合取，机械算出，从不手填：

1. §3.1 的 4 个部件在 `mechanisms/fourth_world/` 下**全部消失**（AST 枚举，挪到别处也算没消失）
2. 配置通过 §3.2 的纯数据检查（无 lambda / 函数定义 / eval 类构造）
3. verdict 逐字节不变——**改写前的内容从 git 历史取，不在代码里写死 sha**
   （写死等于允许我抄错）
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import subprocess
import sys

# --- 预注册 §3.1 的冻结对象，逐字抄入 ---
ABSORBED_PARTS = (
    "MoranGenealogyWorld.__init__",
    "MoranGenealogyWorld._run_stage",
    "MoranGenealogyWorld.run",
    "MoranGenealogyWorld.reuse_trace",
)
KEPT_PARTS = ("build_mechanism_specs", "genealogy_step")
WORLD_DIR = "packages/newlife/src/newlife/mechanisms/fourth_world"
CONFIG = f"{WORLD_DIR}/spec.py"
SUMMARY = "results/fourth-world/summary.json"
PREREG_FREEZE = "6f2bc25"
REPO = pathlib.Path(__file__).resolve().parents[5]


def enumerate_parts(directory: pathlib.Path) -> set[str]:
    out: set[str] = set()
    for path in sorted(directory.glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.add(node.name)
            elif isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.add(f"{node.name}.{sub.name}")
    return out


def baseline_summary_sha() -> tuple[str | None, str]:
    """改写前 `summary.json` 的 sha256。

    **不从预注册的 freeze commit 取**——那个 commit 在 exloop，而本文件在 newlife，
    跨仓库解析不了（首版就是这么写错的，触发 IC-1：实现 bug 而非抽象装不下）。
    改从本仓最后一次触及该文件的 commit 取；改写尚未提交时，那正是改写前的版本。
    提交之后由 `--baseline-sha` 传入本次判定已记录的值。
    """
    # `except Exception: pass` 曾把「git 不在」和「那个 commit 里确实没这个文件」
    # 混成同一个 "unavailable"——第十三个里程碑实测出的 silent_output：进程照常产出一份
    # 格式完好的 verdict: INVALID，理由写成「基线不可得」，而真实原因是 git 不在。
    # **不是没报警，是报错了案由。** 现在两者分开：环境缺失硬失败并指名，
    # 「历史里确实没有」才返回 None。
    try:
        rev = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", SUMMARY],
            cwd=REPO, capture_output=True, text=True, timeout=60)
    except FileNotFoundError as exc:
        raise SystemExit(
            "git 不可用——归档基线取不到。这是环境缺失，不是「基线不存在」；"
            f"非 Python 依赖见 conform/dep_declaration.py。原始错误：{exc}"
        ) from exc
    if rev.returncode != 0 or not rev.stdout.strip():
        return None, "no-history"
    blob = subprocess.run(
        ["git", "show", f"{rev.stdout.strip()}:{SUMMARY}"],
        cwd=REPO, capture_output=True, timeout=60)
    if blob.returncode != 0 or not blob.stdout:
        return None, "no-history"
    return hashlib.sha256(blob.stdout).hexdigest(), f"git:{rev.stdout.strip()[:8]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--baseline-sha", help="改写前 summary 的 sha256（git 取不到时提供）")
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()

    sys.path.insert(0, str(REPO / "packages/newlife/src"))
    from newlife.core.harness import config_is_pure_data  # noqa: PLC0415

    # 判据 1：部件消失
    present = enumerate_parts(REPO / WORLD_DIR)
    still_there = sorted(p for p in ABSORBED_PARTS if p in present)
    kept_ok = sorted(p for p in KEPT_PARTS if p in present)
    c1 = not still_there and len(kept_ok) == len(KEPT_PARTS)

    # 判据 2：配置是纯数据
    pure, offenders = config_is_pure_data(str(REPO / CONFIG))

    # 判据 3：逐字节不变
    baseline, source = baseline_summary_sha()
    if baseline is None and args.baseline_sha:
        baseline, source = args.baseline_sha, "argument"
    current = hashlib.sha256((REPO / SUMMARY).read_bytes()).hexdigest()
    c3 = baseline is not None and baseline == current
    invalid = baseline is None

    h1 = c1 and pure and c3 and not invalid
    summary = {
        "schema": "newlife.eighth-world.verdict.v1",
        "prereg_freeze_commit": PREREG_FREEZE,
        "c1_parts_absorbed": {"absorbed": list(ABSORBED_PARTS),
                              "still_present": still_there,
                              "kept_model_parts": kept_ok, "passed": c1},
        "c2_config_pure_data": {"config": CONFIG, "offenders": offenders,
                                "passed": pure},
        "c3_verdict_bit_identical": {"baseline_sha256": baseline,
                                     "baseline_source": source,
                                     "current_sha256": current, "passed": c3},
        "invalid": invalid,
        "verdict": "INVALID" if invalid else ("H1" if h1 else "H0"),
    }
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"summary written: {args.out}")

    print(f"  C1 部件消失: {'PASS' if c1 else 'FAIL'}  残留={still_there or '无'}  保留 model={kept_ok}")
    print(f"  C2 配置纯数据: {'PASS' if pure else 'FAIL'}  {offenders or ''}")
    print(f"  C3 逐位不变: {'PASS' if c3 else 'FAIL'}  基线来源={source}")
    print(f"\nverdict: {summary['verdict']}")
    return 0 if h1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
