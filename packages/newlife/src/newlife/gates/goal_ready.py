#!/usr/bin/env python3
"""The gate before the freeze: did the steps that leave no trace actually happen?

**It checks that a step was taken, never that it was taken well.** The judgement stays
human. But "was it taken at all" has to be mechanical — otherwise you get the shape this
project already paid for: a skill said "run a literature search on any assumption that
passes the gate", the three fetches all died with ECONNRESET, the run continued, and
**nothing downstream noticed**.

That is the same shape as `re.search` missing and the code falling back to a default:
**attempt fails -> silently take the default -> everything looks fine**. The code side is
covered by `silent_degradation_scan`; this is the process side.

**Selection rule (not everything deserves a gate): only gate steps that leave no trace
when skipped.** Skipping the verdict runner leaves no `summary.json` — visible, no gate
needed. Skipping the literature search removes nothing at all — it needs one.

Six required anchors, exactly what the `newlife-goal` skill emits:

    <!--@evidence: literature_searched=yes, sources=3, verdict=unknown-->
    <!--@counterparty: who would bet the other way, and on what grounds-->
    <!--@attack_layer: conclusion|premise|definition-->
    <!--@decides: design|run-->
    <!--@who_changes_behavior: a specific person + a specific decision-->
    <!--@size_estimate: impl_lines=200, criteria=1, failure_modes=1-->

**A failure has to leave a mark; skipping quietly is not allowed.** If a step genuinely
cannot be done, waive it explicitly and say why:

    <!--@evidence: literature_searched=no, reason=…, waived_by=…-->

And if the goal stage does not apply to this question at all, say so in one anchor rather
than leaving the file half-filled:

    <!--@goal_gate: not_applicable — …why…-->

**`failure_modes` must be 1.** One question should have exactly one way to fail; a
failure A and a failure B you would want to report separately are two questions. If they
really must be merged, write `split_waived=<reason>`.
"""

from __future__ import annotations

import argparse
import pathlib
import re

ANCHOR = re.compile(r"<!--@([A-Za-z0-9_.\-]+):\s*([^>]*?)-->")
PLACEHOLDERS = {"", "TODO", "TBD", "...", "…", "PENDING", "?"}
DECIDES = {"design", "run"}
LAYERS = {"conclusion", "premise", "definition"}


def parse(text: str) -> dict[str, dict[str, str]]:
    """Anchor name -> its fields. An anchor with no `k=v` pair keeps its prose as `_text`."""
    out: dict[str, dict[str, str]] = {}
    for m in ANCHOR.finditer(text):
        fields: dict[str, str] = {}
        for kv in m.group(2).split(","):
            if "=" in kv:
                k, _, v = kv.partition("=")
                fields[k.strip()] = v.strip()
        if fields:
            out.setdefault(m.group(1), {}).update(fields)
        else:
            out.setdefault(m.group(1), {})["_text"] = m.group(2).strip()
    return out


def check(text: str) -> list[str]:
    """Every problem with this goal document. Empty list = ready to freeze."""
    a = parse(text)
    problems: list[str] = []

    if "goal_gate" in a and a["goal_gate"].get("_text", "").startswith(
        "not_applicable"
    ):
        return []  # explicit waiver, with the reason in the anchor

    ev = a.get("evidence")
    if ev is None:
        problems.append(
            "no @evidence — whether the literature was searched leaves no "
            "trace when skipped, so it has to be recorded"
        )
    elif ev.get("literature_searched") == "no":
        if not ev.get("reason") or not ev.get("waived_by"):
            problems.append(
                "@evidence says no search was done but gives no reason= and "
                "no waived_by= — an explicit waiver is fine, quietly "
                "skipping it is not"
            )
    elif ev.get("literature_searched") != "yes":
        problems.append("@evidence: literature_searched must be yes or no")
    elif not ev.get("sources") or not ev.get("verdict"):
        problems.append(
            "@evidence claims a search was run but gives no sources= and "
            "verdict= (known / partly known / unknown)"
        )

    cp = a.get("counterparty")
    if cp is None:
        problems.append(
            "no @counterparty — if you cannot name anyone who would bet the "
            "other way, the result is already inside your expectations and "
            "carries no information (this is the root of seven H1 and zero H0)"
        )
    else:
        body = (
            cp.get("_text", "") or ",".join(f"{k}={v}" for k, v in cp.items())
        ).strip()
        if body in PLACEHOLDERS or len(body) < 15:
            problems.append(
                f"@counterparty is a placeholder or too short: {body!r} — "
                f"say what grounds the other side would bet on"
            )

    dec = a.get("decides")
    if dec is None:
        problems.append(
            "no @decides — is the answer settled by the design or by the "
            "run? Without that distinction a tooling question gets reported "
            "as a conclusion about the world"
        )
    elif dec.get("_text", "").strip() not in DECIDES:
        problems.append("@decides must be design or run")

    layer = a.get("attack_layer")
    if layer is None:
        problems.append(
            "no @attack_layer — is the counterparty attacking the "
            "conclusion, the premise, or the question itself? When the "
            "premise is under attack a simulation settles nothing, and the "
            "output can only be a discriminating prediction"
        )
    else:
        value = layer.get("_text", "").strip()
        if value not in LAYERS:
            problems.append("@attack_layer must be conclusion / premise / definition")
        elif value == "definition":
            problems.append(
                "@attack_layer=definition — an argument about definitions is "
                "not something a simulation can answer"
            )

    who = a.get("who_changes_behavior")
    if who is None:
        problems.append(
            "no @who_changes_behavior — if you cannot name a specific person "
            "and a specific decision, the question is in the 'unimportant but "
            "decidable' bucket: it passes every later gate and is still not "
            "worth asking"
        )
    else:
        body = who.get("_text", "").strip()
        if len(body) < 12 or body in PLACEHOLDERS:
            problems.append(
                f"@who_changes_behavior is a placeholder or too short: "
                f"{body!r} — name the person and the decision"
            )

    sz = a.get("size_estimate")
    if sz is None:
        problems.append(
            "no @size_estimate — with no estimate made in advance there is "
            "nothing to calibrate against, and no later way to tell whether "
            "this should have been split"
        )
    else:
        for key in ("impl_lines", "criteria", "failure_modes"):
            if not sz.get(key, "").strip().isdigit():
                problems.append(f"@size_estimate is missing the numeric field {key}=")
        modes = sz.get("failure_modes", "")
        if modes.isdigit() and int(modes) > 1 and not sz.get("split_waived"):
            problems.append(
                f"@size_estimate declares {modes} decidable ways to fail. A question "
                f"should have one — failures you would want to report separately are "
                f"separate questions. To merge them anyway, write split_waived=<reason>"
            )
    return problems


# ─────────────────────────── negative control ───────────────────────────
READY = """
<!--@evidence: literature_searched=yes, sources=4, verdict=partly known-->
<!--@counterparty: Alon's group would bet the gap is an artefact of the matching step-->
<!--@attack_layer: conclusion-->
<!--@decides: run-->
<!--@who_changes_behavior: me, choosing whether to keep the matching step in v4-->
<!--@size_estimate: impl_lines=200, criteria=2, failure_modes=1-->
"""
"""One goal document that is genuinely ready. **The gate must be green on this.**

A gate that only ever goes red is as useless as one that only ever goes green, and this
project has already had a mechanical check fail on perfectly legitimate data and veto a
scientifically successful run. Every red fixture below is paired against this one.
"""


def _selftest() -> int:
    """Every omission goes red and the ready document goes green.

    **This stays stdlib-only and reads no file.** Its siblings are copied into a scratch
    workspace, mutated, and required to go red, which only works for a self-contained
    script. The one invariant that does cross components — that the `goal.md` written by
    `newlife init` is itself red — is asserted in the test suite instead
    (`test_goal_ready.py`), where reaching into `scaffold/templates/` is free.
    """
    ok = True

    def case(name: str, text: str, want_red: bool) -> None:
        nonlocal ok
        red = bool(check(text))
        mark = "RED" if red else "green"
        if red != want_red:
            print(
                f"  [FAIL] {name}: got {mark}, expected "
                f"{'RED' if want_red else 'green'}"
            )
            ok = False
        else:
            print(f"  [{mark}] {name}")

    case("a goal that is genuinely ready", READY, False)

    for anchor in (
        "evidence",
        "counterparty",
        "attack_layer",
        "decides",
        "who_changes_behavior",
        "size_estimate",
    ):
        case(
            f"@{anchor} missing",
            READY.replace(f"<!--@{anchor}:", f"<!--@{anchor}_REMOVED:"),
            True,
        )

    case(
        "@counterparty is a placeholder",
        READY.replace(
            "Alon's group would bet the gap is an artefact of the matching step", "TODO"
        ),
        True,
    )
    case(
        "@who_changes_behavior is a placeholder",
        READY.replace("me, choosing whether to keep the matching step in v4", "?"),
        True,
    )
    case(
        "@decides is neither design nor run",
        READY.replace("@decides: run", "@decides: maybe"),
        True,
    )
    case(
        "@attack_layer=definition is not a simulation question",
        READY.replace("@attack_layer: conclusion", "@attack_layer: definition"),
        True,
    )
    case(
        "@evidence: no search, no waiver",
        READY.replace(
            "literature_searched=yes, sources=4, verdict=partly known",
            "literature_searched=no",
        ),
        True,
    )
    case(
        "@evidence: no search, waived explicitly",
        READY.replace(
            "literature_searched=yes, sources=4, verdict=partly known",
            "literature_searched=no, reason=no indexed corpus, waived_by=the author",
        ),
        False,
    )
    case(
        "@evidence: a search claimed with no sources",
        READY.replace("sources=4, verdict=partly known", "sources=, verdict="),
        True,
    )
    case(
        "@size_estimate: a non-numeric field",
        READY.replace("impl_lines=200", "impl_lines=some"),
        True,
    )
    case(
        "@size_estimate: two ways to fail, unsplit",
        READY.replace("failure_modes=1", "failure_modes=2"),
        True,
    )
    case(
        "@size_estimate: two ways to fail, waived",
        READY.replace(
            "failure_modes=1", "failure_modes=2, split_waived=one shared runner"
        ),
        False,
    )
    case(
        "the whole stage waived",
        "<!--@goal_gate: not_applicable — a toolchain smoke test-->",
        False,
    )

    print("  selftest passed: every omission red, the ready document green."
          if ok else "  selftest FAILED.")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("goal", nargs="?", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.goal is None:
        ap.error("pass a goal document, or --selftest")

    path = args.goal / "goal.md" if args.goal.is_dir() else args.goal
    if not path.exists():
        # **Not a silent skip.** A missing goal.md on a folder scaffolded before this
        # gate existed is a real gap, and saying nothing about it is the exact defect
        # this gate is here to prevent.
        print(
            f"{path} does not exist. `newlife init` writes one.\n"
            f"If this folder was created before it did, and the registration is already\n"
            f"frozen, **do not write the six anchors now** — a goal document composed\n"
            f"after the verdict is the same shape as HARKing. Record the truth instead:\n"
            f"    <!--@goal_gate: not_applicable ... predates the goal gate ...-->"
        )
        return 1

    problems = check(path.read_text(encoding="utf-8"))
    for p in problems:
        print(f"[FAIL] {path.name}: {p}")
    if problems:
        print(
            f"\nThe goal is not ready: {len(problems)} item(s). These steps leave no "
            f"trace when skipped, which is why a gate covers them."
        )
        return 1
    print(
        f"The goal is ready: {path.name} has all six (literature · counterparty · "
        f"attack layer · design or run · who changes behaviour · size)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
