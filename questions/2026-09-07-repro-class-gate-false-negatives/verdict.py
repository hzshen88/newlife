"""repro class gate false negatives — verdict runner.

The criteria are frozen in `prereg.md` (see its §2). **The verdict is a mechanical
conjunction of the units and is never written by hand.**

**This runner does not run any other question's runner** (registration F4). There are
exactly two safety lines: self-reproduction and an unchanged environment. Questions are
siblings, not a chain — rerunning someone else's old conclusion adds nothing to the
credibility of this one, and with fifty questions it entangles all of them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from newlife import provenance
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code

HERE = Path(__file__).resolve().parent
INNER = "_NEWLIFE_INNER_RUN"        # marks the inner reproduction run; stops infinite recursion

# ─────────────────────────────────────────────────────────────────────
# YOUR WORLD — 一个可复现性实验台。
#
# 「可复现」在这里是**可执行的定义**，不是形容词：按记录下来的信息（commit、内容摘要、
# 数据校验和）在一个干净的地方重建并重跑，输出与原始相同即为可复现。
# 每个变异因此都能先自证「我确实破坏了东西」，而不是靠散文声称——
# 拿一个不破坏任何东西的变异去判「判据抓住了」，是本项目栽过两次的形状。
#
# **产物里不记 commit hash、不记临时路径。** git 的 commit hash 依赖时间戳，
# 每次跑都不同，写进产物 S0 就永远为假（第十四个里程碑把耗时写进产物栽过同一个跟头）。
# ─────────────────────────────────────────────────────────────────────
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}
MODEL = 'import params\nprint(sum(int(x) for x in open("data.txt").read().split()) * params.seed)\n'


def git(repo: Path, *args: str) -> str:
    """跑一条 git 命令，返回 stdout。失败不抛——调用方要区分「命令失败」和「输出为空」。"""
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                          text=True, env={**os.environ, **GIT_ENV})
    return done.stdout.strip()


def make_baseline(root: Path) -> dict:
    """造一个有 remote、有数据、有可运行模型的仓库，返回运行所需的记录信息。"""
    bare, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], check=True,
                   capture_output=True)
    (work / "params.py").write_text("seed = 7\n")
    (work / "data.txt").write_text("3 1 4 1 5\n")
    (work / "model.py").write_text(MODEL)
    git(work, "add", "-A")
    git(work, "commit", "-qm", "baseline")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    return {"bare": bare, "work": work, "commit": git(work, "rev-parse", "HEAD"),
            "digest": tree_digest(work), "data_sha": file_sha(work / "data.txt")}


def run_model(repo: Path) -> str | None:
    done = subprocess.run([sys.executable, "model.py"], cwd=repo,
                          capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def tree_digest(repo: Path) -> str:
    """工作区里被 git 跟踪的文件的内容摘要——版本号会撒谎，这个不会。"""
    digest = hashlib.sha256()
    for name in sorted(git(repo, "ls-files").splitlines()):
        path = repo / name
        if path.is_file():
            digest.update(name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def rebuild_and_run(record: dict, workdir: Path) -> str | None:
    """按记录的信息重建并重跑。重建不出来（无 URL 可用、clone 失败、commit 不可达）返回 None。

    **URL 从工作区的 remote 配置读，不直接用 bare 仓库的路径。** 第一版绕过了这一步，
    于是「删掉 remote」这个变异照样重建成功——实验台把一个真实的失败建模没了。
    注册里能记下的只有 remote 给出的 URL；没有 remote 就没有 URL。
    """
    url = git(record["work"], "remote", "get-url", "origin")
    if not url:
        return None
    subprocess.run(["git", "clone", "-q", url, str(workdir)], capture_output=True)
    if not (workdir / ".git").exists():
        return None
    if git(workdir, "cat-file", "-t", record["commit"]) != "commit":
        return None
    git(workdir, "checkout", "-q", record["commit"])
    return run_model(workdir)


# ─────────────────────────────────────────────────────────────────────
# 三条判据 —— **逐字对应 docs/writing-a-world.md 的表述**，本轮测的就是它们。
# ─────────────────────────────────────────────────────────────────────
def check_clean(repo: Path, _record: dict) -> bool:
    """`git status --porcelain` 为空。"""
    return git(repo, "status", "--porcelain") == ""


def check_reachable(repo: Path, record: dict) -> bool:
    """`git branch -r --contains <commit>` 非空，**且先 fetch**——
    不 fetch 就是拿过时的本地视图替 remote 回答。"""
    git(repo, "fetch", "-q", "origin")
    return git(repo, "branch", "-r", "--contains", record["commit"]) != ""


def check_digest(repo: Path, record: dict) -> bool:
    """内容摘要与记录的一致。"""
    return tree_digest(repo) == record["digest"]


def check_data(repo: Path, record: dict) -> bool:
    """数据文件校验和与记录的一致。"""
    return file_sha(repo / "data.txt") == record["data_sha"]


CHECKS = {"clean": check_clean, "reachable": check_reachable,
          "digest": check_digest, "data": check_data}


# ─────────────────────────────────────────────────────────────────────
# 变异 —— 本轮只含**已知应被抓**的五个。边缘变异（shallow clone、submodule、
# gitattributes filter、LFS 指针）是登记里标 blind 的那格，实现要等 freeze 之后：
# `newlife pilot` 会把 runner 产出的每个单元记进 ledger 算作 seen。
# ─────────────────────────────────────────────────────────────────────
def m_dirty(record: dict) -> None:
    (record["work"] / "params.py").write_text("seed = 99\n")


def m_no_remote(record: dict) -> None:
    git(record["work"], "remote", "remove", "origin")


def m_unpushed(record: dict) -> None:
    (record["work"] / "params.py").write_text("seed = 55\n")
    git(record["work"], "add", "-A")
    git(record["work"], "commit", "-qm", "unpushed")
    record["commit"] = git(record["work"], "rev-parse", "HEAD")
    record["digest"] = tree_digest(record["work"])


def m_source_edit(record: dict) -> None:
    (record["work"] / "params.py").write_text("seed = 42\n")
    git(record["work"], "add", "-A")
    git(record["work"], "commit", "-qm", "edited")
    git(record["work"], "push", "-q", "origin", "HEAD:refs/heads/main")
    record["commit"] = git(record["work"], "rev-parse", "HEAD")
    # digest 刻意不更新：模拟「代码改了，注册里记的还是旧摘要」


def m_data_edit(record: dict) -> None:
    (record["work"] / "data.txt").write_text("9 9 9 9 9\n")
    git(record["work"], "add", "-A")
    git(record["work"], "commit", "-qm", "data changed")
    git(record["work"], "push", "-q", "origin", "HEAD:refs/heads/main")
    record["commit"] = git(record["work"], "rev-parse", "HEAD")
    record["digest"] = tree_digest(record["work"])
    # data_sha 刻意不更新：模拟「数据换了，注册里记的还是旧校验和」


MUTATIONS = {
    "dirty_worktree": (m_dirty, "改了没提交就跑——最常见的一种"),
    "no_remote": (m_no_remote, "本地 git init 从未 push，mapsim 今天就是这个状态"),
    "unpushed_commit": (m_unpushed, "提交了但忘了 push"),
}
"""**清单只收「真正让重建失败或跑出不同结果」的变异。**

起草时还放了 `source_edited` 与 `data_edited`，pilot 显示两者 `breaks=False`：
它们都 push 了、commit 也更新了，重建者能得到自洽的结果——**它们破坏的不是能不能
重建，而是注册里记的和实际不符**。若把「破坏」的定义扩成「或记录与实际不符」，
就成了用判据自己定义破坏、再看判据抓不抓得住，一个恒真的圈。

那两条降级为 `criteria_can_fail` 里的合成演示：它们证明 digest / data 两条判据能红，
这本来就是 S3 该管的事，不是变异清单该管的。
"""


def evaluate_mutation(name: str) -> dict:
    """一个变异跑一轮：先证明它确实破坏可复现性，再看哪条判据抓住了它。"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        record = make_baseline(root)
        original = run_model(record["work"])
        MUTATIONS[name][0](record)
        after = run_model(record["work"])
        rebuilt = rebuild_and_run(record, root / "rebuild")
        # 破坏可复现性 = 按记录重建后跑不出实际在跑的那个东西（或重建不出来）。
        # **两种破坏方式都算**：改了输出（dirty / source_edited / data_edited），
        # 或输出没变但重建不出来（no_remote / unpushed_commit）——后者 rebuilt is None。
        breaks = rebuilt is None or rebuilt != after
        caught_by = sorted(k for k, fn in CHECKS.items() if not fn(record["work"], record))
        return {"breaks_reproducibility": breaks, "caught_by": caught_by,
                # 变异到底生没生效——本项目栽过两次「用一个测不出问题的变异去判通过」
                "changed_behaviour": after != original,
                "rebuild_failed": rebuilt is None,
                "outcome": ("not_a_mutation" if not breaks
                            else "caught" if caught_by else "false_negative"),
                "why_it_happens": MUTATIONS[name][1]}


def mismatch_demo() -> dict:
    """合成演示：记录与实际不符时，digest / data 两条判据必须变红。

    这两种情形不是「重建失败」，所以不属于变异清单；但判据得能抓住它们，
    否则那两条判据本身是恒真的。
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        record = make_baseline(root)
        m_source_edit(record)
        digest_caught = not check_digest(record["work"], record)
        m_data_edit(record)
        record["data_sha"] = file_sha(root / "work" / "data.txt")
        (root / "work" / "data.txt").write_text("1 1 1\n")
        data_caught = not check_data(record["work"], record)
    return {"digest_caught": digest_caught, "data_caught": data_caught}



# ─────────────────────────────────────────────────────────────────────
# S5 — 边缘变异。**登记冻结后才实现**（fb4883d7）。
#
# 与前三个不同：它们改的是工作区内容，这些改的是**仓库形态**，所以各自要造场景。
# 重建流程一律按注册记得下的信息走（remote URL + commit），**不得依赖注册之外的知识**
# ——比如「这个仓库有 submodule，要 --recursive」这句话，注册里没有地方写。
# ─────────────────────────────────────────────────────────────────────
def _seed_repo(work: Path, extra: str = "") -> None:
    (work / "params.py").write_text("seed = 7\n")
    (work / "data.txt").write_text("3 1 4 1 5\n")
    (work / "model.py").write_text(extra + MODEL)


def edge_shallow(root: Path) -> dict:
    """工作副本本身是 shallow clone —— CI runner 默认 depth=1 就是这个形态。"""
    bare, seed, work = root / "origin.git", root / "seed", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(seed)], capture_output=True)
    _seed_repo(seed)
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "first")
    (seed / "params.py").write_text("seed = 7\n# second commit\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "second")
    git(seed, "push", "-q", "origin", "HEAD:refs/heads/main")
    subprocess.run(["git", "clone", "-q", "--depth=1", str(bare), str(work)],
                   capture_output=True)
    return {"bare": bare, "work": work, "commit": git(work, "rev-parse", "HEAD"),
            "digest": tree_digest(work), "data_sha": file_sha(work / "data.txt")}


def edge_submodule(root: Path) -> dict:
    """依赖放在 submodule 里，而重建时没有 --recursive —— 注册里没有地方写这件事。"""
    subbare, subwork = root / "sub.git", root / "subwork"
    subprocess.run(["git", "init", "-q", "--bare", str(subbare)], check=True)
    subprocess.run(["git", "clone", "-q", str(subbare), str(subwork)], capture_output=True)
    (subwork / "helper.py").write_text("factor = 1\n")
    git(subwork, "add", "-A")
    git(subwork, "commit", "-qm", "sub")
    git(subwork, "push", "-q", "origin", "HEAD:refs/heads/main")

    bare, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], capture_output=True)
    _seed_repo(work, "import sys; sys.path.insert(0, 'lib')\nimport helper\n")
    subprocess.run(["git", "-C", str(work), "-c", "protocol.file.allow=always",
                    "submodule", "add", "-q", str(subbare), "lib"],
                   capture_output=True, env={**os.environ, **GIT_ENV})
    git(work, "add", "-A")
    git(work, "commit", "-qm", "with submodule")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    return {"bare": bare, "work": work, "commit": git(work, "rev-parse", "HEAD"),
            "digest": tree_digest(work), "data_sha": file_sha(work / "data.txt")}


def edge_filter(root: Path) -> dict:
    """`.gitattributes` 的 smudge filter 使 checkout 出的内容不等于仓库里存的内容。

    filter driver 配在**本地 git config 里，不在仓库里** —— 重建者没有它。
    """
    bare, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], capture_output=True)
    _seed_repo(work)
    (work / ".gitattributes").write_text("params.py filter=tweak\n")
    git(work, "config", "filter.tweak.smudge", "sed s/seed=7/seed=13/")
    git(work, "config", "filter.tweak.clean", "cat")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "with filter")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    (work / "params.py").unlink()
    git(work, "checkout", "--", "params.py")
    return {"bare": bare, "work": work, "commit": git(work, "rev-parse", "HEAD"),
            "digest": tree_digest(work), "data_sha": file_sha(work / "data.txt")}


def edge_lfs(root: Path) -> dict:
    """数据文件由 LFS 管理，而重建时指针没被拉取成内容。"""
    bare, work = root / "origin.git", root / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(work)], capture_output=True)
    _seed_repo(work)
    subprocess.run(["git", "-C", str(work), "lfs", "install", "--local"],
                   capture_output=True, env={**os.environ, **GIT_ENV})
    subprocess.run(["git", "-C", str(work), "lfs", "track", "data.txt"],
                   capture_output=True, env={**os.environ, **GIT_ENV})
    git(work, "add", "-A")
    git(work, "commit", "-qm", "lfs")
    git(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    return {"bare": bare, "work": work, "commit": git(work, "rev-parse", "HEAD"),
            "digest": tree_digest(work), "data_sha": file_sha(work / "data.txt")}


EDGE_MUTATIONS = {
    "shallow_clone": (edge_shallow, "CI runner 默认 depth=1"),
    "submodule_uninitialised": (edge_submodule, "clone 时忘了 --recursive"),
    "gitattributes_filter": (edge_filter, "filter driver 在本地 config，不随仓库走"),
    "lfs_pointer_not_fetched": (edge_lfs, "没装 git-lfs 或没 lfs pull"),
}


def evaluate_edge(name: str) -> dict:
    """边缘变异：造场景 → 自证破坏可复现性（F5）→ 看哪条判据抓住。

    构造本身失败时如实记 `construction_failed`：**它既不是 caught 也不是假阴性**，
    把构造失败当成任何一种结论都是在拿测不出问题的东西下判断。
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            record = EDGE_MUTATIONS[name][0](root)
        except Exception as error:  # noqa: BLE001 —— 构造失败本身是要交代的事实
            return {"outcome": "construction_failed", "detail": type(error).__name__,
                    "why_it_happens": EDGE_MUTATIONS[name][1]}
        after = run_model(record["work"])
        rebuilt = rebuild_and_run(record, root / "rebuild")
        breaks = rebuilt is None or rebuilt != after
        caught_by = sorted(k for k, fn in CHECKS.items() if not fn(record["work"], record))
        return {"breaks_reproducibility": breaks, "caught_by": caught_by,
                "rebuild_failed": rebuilt is None,
                "outcome": ("not_a_mutation" if not breaks
                            else "caught" if caught_by else "false_negative"),
                "why_it_happens": EDGE_MUTATIONS[name][1]}


def git_version() -> str:
    """结论绑定在这个 git 版本上，不是永久事实——边缘行为随版本变。"""
    return subprocess.run(["git", "--version"], capture_output=True,
                          text=True).stdout.strip()


def baseline_is_reproducible() -> bool:
    """对照组：没有任何变异时，重建必须跑出同样的东西。**否则整个实验台没有判定力。**"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        record = make_baseline(root)
        return run_model(record["work"]) == rebuild_and_run(record, root / "rebuild")


# ─────────────────────────────────────────────────────────────────────
# CRITERIA
# ─────────────────────────────────────────────────────────────────────
def criteria_can_fail(results: dict) -> dict:
    """**F1：每条判据都要能红。** 用合成输入在运行时证明。"""
    synthetic_fn = {"outcome": "false_negative", "breaks_reproducibility": True,
                    "caught_by": []}
    edited = mismatch_demo()
    return {
        "对照组可复现（实验台有判定力）": baseline_is_reproducible(),
        "digest 判据对「代码改了摘要没更新」变红": edited["digest_caught"],
        "data 判据对「数据换了校验和没更新」变红": edited["data_caught"],
        "outcome 谓词对无人抓住的破坏返回 false_negative":
            (synthetic_fn["outcome"] == "false_negative"),
        "S4 谓词对 false_negative 为假":
            all_caught({"synthetic": synthetic_fn}) is False,
        "至少一条判据在某个变异上真的红过":
            any(r["caught_by"] for r in results.values()),
    }


def all_caught(results: dict) -> bool:
    return all(r["outcome"] == "caught" for r in results.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    results = {name: evaluate_mutation(name) for name in sorted(MUTATIONS)}
    edges = {name: evaluate_edge(name) for name in sorted(EDGE_MUTATIONS)}

    can_fail = criteria_can_fail(results)
    # S1: the packages installed *now* are exactly the ones `env.lock` recorded at the
    # freeze. **The first version of this line compared the file's digest with a digest of
    # the same file taken a moment earlier — true by construction, and it shipped in every
    # early question.** `newlife freeze` rewrites env.lock from the live environment and
    # pins its hash into the registration; `newlife audit` proves the file never changed
    # afterwards; this line proves the run happened in that environment.
    s1 = provenance.env_text() == (HERE / "env.lock").read_text(encoding="utf-8")
    s2 = all(r["breaks_reproducibility"] for r in results.values())
    s4 = all_caught(results)
    # F5：construction_failed 与 not_a_mutation 都不进分子分母——不得拿测不出问题的
    # 变异去判「判据抓住了」。判定的只是真的破坏了可复现性的那些。
    judged = {k: v for k, v in edges.items() if v["outcome"] in ("caught", "false_negative")}
    s5 = bool(judged) and all(v["outcome"] == "caught" for v in judged.values())
    # **"the criteria can fail" is its own visible slot in the conjunction, not a
    # detail nested inside another unit.** The first version folded it into a sub-field
    # of S2, so the registration read S0∧S1∧S2∧S3 while the code computed three —
    # the unit-alignment check in `newlife run` caught exactly this the first time it
    # ran against a real question folder.
    units = {"S1_env_unchanged": {"passed": s1},
             "S2_mutations_really_break_it": {"passed": s2, "per_mutation": results},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail},
             "S4_known_mutations_caught": {"passed": s4},
             "S5_edge_mutations_caught": {"passed": s5, "per_mutation": edges,
                                          "judged": sorted(judged)}}

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-07-repro-class-gate-false-negatives.v1",
               "provenance": prov, "git_version": git_version(), "units": units}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # **The key name says "S0 not counted yet".** S0 cannot be written into the file it
    # reproduces — doing so would make the two runs differ by construction — so the final
    # verdict can only live in reproduction.json. Calling this one `verdict` too would
    # make the artifact show H1 while S0 was false: **one layer passing itself off as the
    # whole conjunction.**
    summary, _ = emit(verdict, summary,
                      RenderSpec(verdict_key="verdict_before_reproduction"), args.out)

    if os.environ.get(INNER):
        return exit_code(verdict)

    # ── S0: run this file again in a separate process, compare bytes ────────────
    # **The record goes in a different file.** Written into summary.json itself, the two
    # runs would necessarily differ and "byte-identical" could never hold — the record of
    # a reproduction cannot live inside the artifact being reproduced.
    probe = args.out.parent / ".reproduction-probe.json"   # beside --out: a pilot never touches results/
    subprocess.run([sys.executable, __file__, "--out", str(probe)],
                   env={**os.environ, INNER: "1"}, capture_output=True, check=False)
    s0 = probe.exists() and probe.read_bytes() == args.out.read_bytes()
    probe.unlink(missing_ok=True)
    final = verdict if s0 else "INVALID"     # S0 false = this run had no discriminating power
    (args.out.parent / "reproduction.json").write_text(json.dumps(
        {"schema": "self-reproduction.v1", "S0_byte_identical_on_rerun": s0,
         "verdict": final, "verdict_before_reproduction": verdict,
         "of": args.out.name, "sha256": provenance.file_digest(args.out)},
        indent=2, ensure_ascii=False) + "\n")

    for name, unit in units.items():
        print(f"  {name:34s} {unit['passed']}")
    print(f"  {'S0_byte_identical_on_rerun':34s} {s0}")
    # A pilot prints the same conjunction, but must never look like a verdict on screen.
    label = ("PILOT (exploratory, no evidential weight)" if os.environ.get("NEWLIFE_PILOT")
             else "verdict")
    print(f"\n{label}: {final}"
          + ("" if s0 else "   <- the two runs disagreed; this run has no power"))
    return exit_code(final)


if __name__ == "__main__":
    raise SystemExit(main())
