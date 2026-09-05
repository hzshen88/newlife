#!/usr/bin/env python3
"""文档断言对账器 —— 让流水线文档不再手抄验证脚本的数字与覆盖范围。

## 为什么有这个脚本

第三世界 question 文档的第 5、6 轮评审（`8e48835`、`767c077`）修的全是同一类
问题：文档描述的 check 覆盖范围与数字，和脚本实际做的对不上。脚本是对的，
散文抄错了。这类错误此前只能靠人通读整份文档发现——而文档每轮都在变长，
通读成本随轮数累积，返工是平方级的。

对账器把这一类从「读」变成「跑」：验证脚本用 `--emit-json` 输出机器可读台账
（`newlife.verification.checks.v1`），文档在断言旁放一个 HTML 注释锚，本脚本
逐条比对。文档抄错数字、引用不存在的 check、或声称的函数覆盖与运行时观测
不符，都会在几秒内红掉，不占用评审的注意力。

## 锚点语法

紧跟在断言所在句子之后，单行 HTML 注释（渲染时不可见，git diff 友好）：

    ...asserting exactly 14/110 kernels and 8/40 chains differ.
    <!--@check-11: kernel_diffs=14, kernel_total=110, chain_diffs=8, chain_total=40-->

    ...check 12 guards at the `grid_prob_lt()` level.
    <!--@check-12: covers=grid_prob_lt-->

    脚本自身的哈希：
    <!--@script: sha256=a85e8fb7...-->

`covers` 多个函数用 `|` 分隔。同一个锚可同时带 facts 与 covers。

## covers 只支持正向断言，这是刻意的

台账的 `covers` 语义是「自上一次 report() 起新观测到的生产函数调用」。共享
一次计算循环的 check（如 check-9b、9c 复用 9a 算好的数据）自身 span 内没有
新调用，covers 因此为空——空不等于「没调用过」。

所以本脚本只支持 `covers=X`（必须调用到 X）这种**正向**断言：观测到就是观测
到了，是硬事实。**不提供** 「必须没调用 X」的负向断言——在这个观测模型下它
无法可靠成立，与其提供一个会给出假证明的检查，不如不提供。锚点声称的 covers
落在一个 covers 为空的 check 上时，报 UNVERIFIABLE 而非 PASS。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

# <!--@check-11: kernel_diffs=14, chain_diffs=8; covers=grid_transitions-->
ANCHOR_RE = re.compile(r"<!--@\s*([A-Za-z0-9_.-]+)\s*:\s*(.*?)\s*-->", re.DOTALL)

PASS, FAIL, UNVERIFIABLE, PENDING = "PASS", "FAIL", "UNVERIFIABLE", "PENDING"

# 追溯链用的锚，不是台账 check —— 由 verify_trace() 处理，verify() 必须跳过
TRACE_ANCHORS = {"criterion", "goal", "question", "plan", "prereg"}
# 值域闭包：上游用 @vocabulary 声明某判据的合法取值，下游用 @outcome 声明它
# 实际会产生的结局。下游多出来的那些即「未声明的新增结局」。
VOCAB_ANCHORS = {"vocabulary", "outcome"}
# goal 冻结前的门用的锚，由 check_goal_ready.py 检查，不是 check 台账的条目。
GOAL_GATE_ANCHORS = {"goal_gate", "evidence", "counterparty", "size_estimate",
                     # 2026-09-04 newlife-goal 加的三个。**漏登记会让对账器
                     # 把它们当成 check 锚去台账里找**——门自检当场报出来的。
                     "decides", "attack_layer", "who_changes_behavior"}


def parse_anchor_body(body: str) -> tuple[dict[str, str], list[str]]:
    """把锚点正文解析成 (facts, covers)。`;` 分段，`,` 分项。"""
    facts: dict[str, str] = {}
    covers: list[str] = []
    for segment in body.split(";"):
        for item in segment.split(","):
            item = item.strip()
            if not item or "=" not in item:
                continue
            key, _, value = item.partition("=")
            key, value = key.strip(), value.strip()
            if key == "covers":
                covers.extend(f.strip() for f in value.split("|") if f.strip())
            else:
                facts[key] = value
    return facts, covers


def load_ledger(path: pathlib.Path) -> dict:
    ledger = json.loads(path.read_text())
    schema = ledger.get("schema", "")
    if not schema.startswith("newlife.verification.checks."):
        raise SystemExit(f"{path}: unexpected schema {schema!r}")
    return ledger


def frozen_normalise(text: str) -> str:
    """冻结内容的归一形式：**精确**剔除 `@frozen` 锚注释本身占据的字符区间。

    冻结标记是在冻结之后才写进文件的（冻结提交的内容里没有它），把它算进哈希会让
    任何冻结标记都自相矛盾。所以要剔——但只能剔锚本身。

    第一版按「整行含子串 `@frozen:` 就整行丢弃」实现，被第二轮外审用本函数做出了
    真实的哈希碰撞：两份判据文字**完全不同**、但都在同一行里带有字面文本
    `@frozen:` 的内容，哈希相同（782ebda7… == 782ebda7…）。这份文档群本来就习惯在
    行内讨论「这里该不该加 @frozen 锚」，一句善意的旁注就能让那一行**永久**跳出
    冻结保护，而且不报任何红。

    现在用 ANCHOR_RE 做定点 span 替换，只吃掉 `<!--@frozen: ...-->` 这段注释，
    同一行上的其余文字照常进哈希。
    """
    return ANCHOR_RE.sub(
        lambda m: "" if m.group(1) == "frozen" else m.group(0), text
    )


def verify(doc: pathlib.Path, ledger: dict, ledger_path: pathlib.Path) -> list[tuple]:
    """返回 (status, doc, target, message) 列表。"""
    results: list[tuple] = []
    checks = {c["id"]: c for c in ledger["checks"]}
    text = doc.read_text()

    def add(status, target, message):
        results.append((status, doc.name, target, message))

    for match in ANCHOR_RE.finditer(text):
        target, body = match.group(1), match.group(2)
        line_no = text[: match.start()].count("\n") + 1
        where = f"{target} (L{line_no})"
        if (target in TRACE_ANCHORS or target in VOCAB_ANCHORS
                or target in GOAL_GATE_ANCHORS):
            continue
        facts, covers = parse_anchor_body(body)

        # --- 冻结锚：文档自称冻结于某 commit，内容就不许再变 ---
        #
        # 由外审（2026-09-02）找出的坑：goal 状态行写着「frozen（e0d0875）」，而磁盘
        # 内容已经不等于该 commit 的内容。对账器此前只保护验证脚本的哈希，不保护
        # 文档自己的冻结哈希，所以这种漂移只能靠人翻 git log 发现。
        #
        # 刻意**不**用 `git show` 比对：gate 自检把文档树拷到临时目录、不带 `.git`，
        # 依赖 git 会让这条检查在自检里失效；而且冻结的意义不该依赖历史是否完整。
        # 锚里同时存 commit（给人看）与内容哈希（给机器判），自包含。
        if target == "frozen":
            claimed_sha = facts.get("sha256")
            claimed_commit = facts.get("commit")
            unknown = [k for k in facts if k not in ("sha256", "commit")]
            if unknown:
                add(FAIL, where, f"unknown key(s) on @frozen anchor: {unknown}")
            elif not claimed_sha:
                add(FAIL, where, "@frozen anchor has no sha256= — nothing is enforced")
            else:
                actual = hashlib.sha256(
                    frozen_normalise(text).encode()
                ).hexdigest()
                if actual != claimed_sha:
                    add(
                        FAIL,
                        where,
                        f"frozen content changed: doc claims {claimed_sha[:16]}... "
                        f"but current content hashes to {actual[:16]}... "
                        f"(claimed frozen at {claimed_commit or '?'}) — either revert "
                        f"the change or re-freeze and update this anchor",
                    )
                else:
                    add(
                        PASS,
                        where,
                        f"frozen content intact ({claimed_sha[:16]}..., "
                        f"commit {claimed_commit or '?'})",
                    )
            continue

        # --- 脚本自身的哈希锚 ---
        if target == "script":
            script = ledger_path.parent / ledger["script"]
            for key, claimed in facts.items():
                if key != "sha256":
                    add(FAIL, where, f"unknown key {key!r} on @script anchor")
                    continue
                if claimed != ledger["script_sha256"]:
                    add(
                        FAIL,
                        where,
                        f"sha256 in doc {claimed[:16]}... != ledger "
                        f"{ledger['script_sha256'][:16]}...",
                    )
                elif script.exists():
                    # 台账可能是旧的：再对一次磁盘上的真实文件
                    actual = hashlib.sha256(script.read_bytes()).hexdigest()
                    if actual != claimed:
                        add(
                            FAIL,
                            where,
                            f"sha256 in doc {claimed[:16]}... != file on disk "
                            f"{actual[:16]}... (ledger is stale — re-run the script)",
                        )
                    else:
                        add(PASS, where, f"sha256 {claimed[:16]}...")
                else:
                    add(
                        PASS, where, f"sha256 {claimed[:16]}... (script file not found)"
                    )
            continue

        # --- check 锚 ---
        check = checks.get(target)
        if check is None:
            add(FAIL, where, f"no such check in ledger (have: {sorted(checks)})")
            continue
        if not check["passed"]:
            add(FAIL, where, "check FAILED in the ledger — doc cites a failing check")

        for key, claimed in facts.items():
            if key not in check["facts"]:
                add(
                    FAIL,
                    where,
                    f"no fact {key!r} (have: {sorted(check['facts'])})",
                )
            elif check["facts"][key] != claimed:
                add(
                    FAIL,
                    where,
                    f"{key}: doc says {claimed!r}, script says {check['facts'][key]!r}",
                )
            else:
                add(PASS, where, f"{key}={claimed}")

        for fn in covers:
            if fn in check["covers"]:
                add(PASS, where, f"covers {fn}()")
            elif not check["covers"]:
                add(
                    UNVERIFIABLE,
                    where,
                    f"claims covers {fn}() but this check observed no calls of its "
                    f"own — its computation likely happened inside an earlier "
                    f"check's span; the claim can neither be confirmed nor refuted",
                )
            else:
                add(
                    FAIL,
                    where,
                    f"claims covers {fn}() but observed calls were {check['covers']}",
                )

    return results


def verify_trace(
    stage: str, upstream: pathlib.Path, docs: list[pathlib.Path]
) -> list[tuple]:
    """追溯链检查：下游文档是否逐条兑现了上游文档的判据。

    上游用 `<!--@criterion: C1-->` 声明条目；下游用 `<!--@<stage>: C1-->` 认领。
    三件事必须同时成立，缺一即失败：

    - **无遗漏** —— 上游每个条目都有下游落点。漏了就是这一层没兑现上一层。
    - **无孤儿** —— 下游认领的条目在上游存在。指向不存在的判据 = 手滑或上游改了。
    - **无新增** —— 下游没有上游之外的判据。这条最值钱：World 2 的 plan 在第二轮
      红队时补进了 prereg 里没有的东西，两份文档从此说了不一样的话，代价记在
      `results/second-world/implementation-log.json` 第 3 条。
    """
    results: list[tuple] = []
    up_text = upstream.read_text()
    declared = [
        m.group(2).strip()
        for m in ANCHOR_RE.finditer(up_text)
        if m.group(1) == "criterion"
    ]
    if not declared:
        return [
            (FAIL, upstream.name, "trace", "no <!--@criterion: ...--> anchors found")
        ]

    downstream = [d for d in docs if d.resolve() != upstream.resolve()]
    if not downstream:
        # 上游刚写完、下游还没起草。报 PENDING 而不是 FAIL：一个「总是红」的
        # 检查会训练人忽略红色，那是 gate 最危险的失效模式。
        #
        # 代价说明白：忘记把已存在的下游文档传进来，这里会误报 PENDING 而不是
        # 抓到遗漏。收尾清单要求跑完整命令（所有阶段文档一起传），那一步才是
        # 这个漏洞的兜底。
        return [
            (PENDING, upstream.name, f"{stage}:{cid}",
             "no downstream document provided yet — pass it once it exists")
            for cid in declared
        ]

    claimed: dict[str, list[str]] = {}
    for doc in downstream:
        for m in ANCHOR_RE.finditer(doc.read_text()):
            if m.group(1) == stage:
                cid = m.group(2).strip()
                claimed.setdefault(cid, []).append(doc.name)

    for cid in declared:
        if cid in claimed:
            where = ", ".join(sorted(set(claimed[cid])))
            results.append(
                (PASS, upstream.name, f"{stage}:{cid}", f"claimed in {where}")
            )
        else:
            results.append(
                (
                    FAIL,
                    upstream.name,
                    f"{stage}:{cid}",
                    "MISSING — no downstream doc claims to satisfy it",
                )
            )
    for cid in sorted(claimed):
        if cid not in declared:
            results.append(
                (
                    FAIL,
                    ", ".join(sorted(set(claimed[cid]))),
                    f"{stage}:{cid}",
                    f"ORPHAN/NEW — not declared upstream (have: {declared})",
                )
            )
    return results


def verify_vocabulary(upstream: pathlib.Path, docs: list[pathlib.Path]) -> list[tuple]:
    """下游产生的结局，不得超出上游声明的值域。

    由外审（2026-09-02）找出的坑：goal 的 C1 写「取值只有四个」，question 却又定义了
    第五种结局 IC-1 来处理界定失败，且没说它算不算「有明确归类」——一个 check 落进去
    就既不触发整改义务、也不出现在统计里。两份文档说了不一样的话，而这只能靠人对照
    才能发现。

    与追溯链的「无新增」是同一条纪律，只是作用在**值**上而不是**条目**上。
    """
    results: list[tuple] = []
    vocab: dict[str, set[str]] = {}
    for m in ANCHOR_RE.finditer(upstream.read_text()):
        if m.group(1) != "vocabulary":
            continue
        body = m.group(2).strip()
        if "=" not in body:
            results.append((FAIL, upstream.name, "vocabulary",
                            f"malformed @vocabulary body {body!r} (want `C1=a|b|c`)"))
            continue
        cid, values = body.split("=", 1)
        vocab[cid.strip()] = {v.strip() for v in values.split("|") if v.strip()}
    if not vocab:
        return [(PENDING, upstream.name, "vocabulary",
                 "no <!--@vocabulary: ...--> anchors — nothing to close over")]

    used: dict[str, dict[str, str]] = {}
    for doc in docs:
        if doc.resolve() == upstream.resolve():
            continue
        for m in ANCHOR_RE.finditer(doc.read_text()):
            if m.group(1) != "outcome":
                continue
            body = m.group(2).strip()
            if "=" not in body:
                results.append((FAIL, doc.name, "outcome",
                                f"malformed @outcome body {body!r} (want `C1=value`)"))
                continue
            cid, value = (x.strip() for x in body.split("=", 1))
            used.setdefault(cid, {})[value] = doc.name

    for cid, allowed in sorted(vocab.items()):
        seen = used.get(cid, {})
        if not seen:
            results.append((PENDING, upstream.name, f"vocab:{cid}",
                            "no downstream @outcome declared yet"))
            continue
        for value, where in sorted(seen.items()):
            if value in allowed:
                results.append((PASS, where, f"vocab:{cid}",
                                f"outcome {value!r} is in the declared vocabulary"))
            else:
                results.append((FAIL, where, f"vocab:{cid}",
                                f"outcome {value!r} is NOT in {cid}'s declared "
                                f"vocabulary {sorted(allowed)} — either add it upstream "
                                f"(and re-freeze) or stop producing it"))
        missing = sorted(allowed - set(seen))
        if missing:
            results.append((PASS, upstream.name, f"vocab:{cid}",
                            f"declared but not yet produced downstream: {missing}"))
    return results


def report_unanchored(docs: list[pathlib.Path], ledger: dict) -> list[str]:
    """台账里从未被任何文档锚引用的 fact —— 提示哪些数字还没绑定。"""
    referenced: set[str] = set()
    for doc in docs:
        for match in ANCHOR_RE.finditer(doc.read_text()):
            facts, _ = parse_anchor_body(match.group(2))
            referenced.update(f"{match.group(1)}.{k}" for k in facts)
    return [
        f"{c['id']}.{k}"
        for c in ledger["checks"]
        for k in c["facts"]
        if f"{c['id']}.{k}" not in referenced
    ]


def run_selftest() -> int:
    """归一化自身的性质检查。**刻意不依赖任何存储哈希**——依赖它的负控会被污染：
    改动归一化会让基线哈希一并失效，检查因「基线对不上」而红，看着像抓住，
    其实什么都没证明（第二轮外审后做元负控时实际踩到过）。

    性质 P1：`@frozen` 锚**自身**必须被剔除（否则冻结标记自相矛盾）。
    性质 P2：剔除必须精确到锚的字符区间——同一行上锚**之外**的文字改了，
             归一结果必须随之改变。首版按整行子串剔除，P2 不成立。
    """
    failures = []

    a = "x\n<!--@frozen: commit=aaa, sha256=" + "0" * 64 + "-->\n"
    b = "x\n<!--@frozen: commit=bbb, sha256=" + "1" * 64 + "-->\n"
    if frozen_normalise(a) != frozen_normalise(b):
        failures.append("P1: @frozen 锚自身未被剔除——冻结标记会自相矛盾")

    c = "判据：取值只有四个  <!-- 本行提到 @frozen: 锚 -->\n"
    d = "判据：取值只有八个  <!-- 本行提到 @frozen: 锚 -->\n"
    if frozen_normalise(c) == frozen_normalise(d):
        failures.append(
            "P2: 同一行上锚之外的文字改了、归一结果却相同——"
            "剔除粒度是整行而非锚 span，冻结保护可被一句行内旁注绕过"
        )

    for f in failures:
        print(f"[{FAIL:12s}] frozen_normalise: {f}")
    if failures:
        print(f"\nfrozen_normalise selftest: {len(failures)} 条性质不成立")
        return 1
    print("frozen_normalise selftest: P1/P2 均成立")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ledger", type=pathlib.Path, help="checks.json 台账")
    ap.add_argument(
        "--trace",
        action="append",
        default=[],
        metavar="STAGE=UPSTREAM.md",
        help="追溯链检查，如 --trace goal=goals/xxx.md；可重复",
    )
    ap.add_argument(
        "--vocabulary",
        type=pathlib.Path,
        metavar="UPSTREAM.md",
        help="值域闭包检查：下游 @outcome 不得超出上游 @vocabulary 声明的取值",
    )
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="检验归一化自身的性质（不依赖任何存储哈希，可独立证伪）",
    )
    ap.add_argument("docs", nargs="*", type=pathlib.Path)
    ap.add_argument(
        "--strict",
        action="store_true",
        help="把 UNVERIFIABLE 也当作失败",
    )
    ap.add_argument(
        "--report-unanchored",
        action="store_true",
        help="列出台账里还没有被任何文档引用的 fact",
    )
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    results: list[tuple] = []
    ledger = None
    if args.ledger:
        ledger = load_ledger(args.ledger)
        if not ledger["all_passed"]:
            print(f"!! ledger reports FAILED checks: {ledger['failed']}\n")
        for doc in args.docs:
            results.extend(verify(doc, ledger, args.ledger))

    for spec in args.trace:
        stage, _, up = spec.partition("=")
        results.extend(verify_trace(stage, pathlib.Path(up), args.docs))

    if args.vocabulary:
        results.extend(verify_vocabulary(args.vocabulary, args.docs))

    for status, doc_name, target, message in results:
        print(f"[{status:12s}] {doc_name}: {target}: {message}")

    if args.report_unanchored and ledger:
        unanchored = report_unanchored(args.docs, ledger)
        print(f"\nfacts not referenced by any doc anchor ({len(unanchored)}):")
        for name in unanchored:
            print(f"  {name}")

    failed = [r for r in results if r[0] == FAIL]
    unverifiable = [r for r in results if r[0] == UNVERIFIABLE]
    pending = [r for r in results if r[0] == PENDING]
    print(
        f"\n{len(results)} claims checked: "
        f"{len(results) - len(failed) - len(unverifiable) - len(pending)} pass, "
        f"{len(failed)} fail, {len(unverifiable)} unverifiable, {len(pending)} pending"
    )
    if ledger and not ledger["all_passed"]:
        return 1
    if failed:
        return 1
    if unverifiable and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
