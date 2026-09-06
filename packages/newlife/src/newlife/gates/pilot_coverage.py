#!/usr/bin/env python3
"""The second gate before the freeze: was every criterion piloted, and is one still blind?

## Why this gate exists

Of the first four real registrations, two came back INVALID, and **neither failure was
scientific** — both were defects in the criteria that a pilot would have exposed:

- an integration window frozen with no pilot at all (steady states differed by 1.8%,
  the criterion demanded <1e-3 — a two-second run would have found it);
- a pilot that looked at one trajectory's distinct-value count, then froze a criterion
  about *every* trajectory (the other model's increments underflowed to zero).

The `newlife-prereg` skill states the rules — cover every quantity, keep one unit
blind — in prose. **Prose does not stop a freeze.** This gate does.

## What is mechanical here

1. Every row of the `prereg.md` §2 table says how it was piloted: `seen`, `blind` or
   `mechanical`. An empty cell is a decision not yet made, and the freeze is where it
   has to be made.
2. A row marked `seen` has a pilot run behind it. `newlife pilot` runs the runner into
   `pilot/<stamp>/` (never `results/`) and appends the units it produced to
   `pilot/ledger.jsonl`. "I derived it, so I know" does not count as having looked.
3. At least one row is `blind`. A confirmatory round in which every number was already
   seen while drafting carries no information. When a round genuinely has nothing blind
   (a toolchain smoke test), waive it **on the record**:

       <!--@pilot_gate: no_blind_waived — why-->

   and when the stage does not apply at all:

       <!--@pilot_gate: not_applicable — why-->

4. The **most recent** pilot ran in the environment being frozen. `newlife pilot` records
   a digest of the live environment in the ledger; this compares it with the live
   environment at the freeze. Install a package in between and the freeze rewrites
   `env.lock` from the new environment — S1 then goes green against an environment in
   which the runner was **never once executed**, and the discovery comes at run time,
   after the one irreversible step, when repairing the environment would itself turn S1
   red. A ledger with no digest (written before this existed) stays green.
5. **The commitments in `goal.md` did not move between the pilot and the freeze.** Rule
   one sends the pilot to look at every quantity a criterion names, so it may hand you the
   answer to the main criterion before anything is frozen; changing what you are betting
   on afterwards is HARKing and leaves no trace in any file. Four anchors are digested at
   pilot time and compared here — `counterparty`, `attack_layer`, `decides`,
   `who_changes_behavior`. **Not the whole file**: §5's closeout is written after the run
   and §1's prose legitimately grows. A legitimate change is recorded, not forbidden:

       <!--@goal_changed: what moved, and why it is not a response to the pilot-->

   A ledger with no goal digest (written before this existed) stays green.

## What is not mechanical

Whether a `blind` row is genuinely blind. The ledger records which *units* a run
computed, not which *numbers* a person looked at; a runner that computes everything in
one pass produces the blind unit too. So the gate does not cross-check `blind` against
the ledger — that judgement stays with the person, the way it always did.

    python -m newlife.gates.pilot_coverage <question-folder>
    python -m newlife.gates.pilot_coverage --selftest
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import json
import pathlib
import re

from newlife import provenance

TABLE_ROW = re.compile(r"^\|\s*\*\*([A-Z]+\d+)\*\*\s*\|")
ANCHOR = re.compile(r"<!--@pilot_gate:\s*([^>]*?)-->")
GOAL_ANCHOR = re.compile(r"<!--@([A-Za-z0-9_.\-]+):\s*([^>]*?)-->")
GOAL_CHANGED = re.compile(r"<!--@goal_changed:\s*([^>]*?)-->")
COMMITMENTS = ("counterparty", "attack_layer", "decides", "who_changes_behavior")
"""The four anchors the pilot is not entitled to move. `evidence` and `size_estimate`
are deliberately absent: revising a source count or an estimate is bookkeeping, not a
change to what is being bet on."""
UNIT_KEY = re.compile(r"^([A-Z]+\d+)(?:_|$)")
VALUES = ("seen", "blind", "mechanical")


def piloted(prereg_text: str) -> dict[str, str]:
    """Unit -> the value of its `Piloted?` cell (the fourth column), normalised.

    Rows look like `| **S2** | what | passes when | seen |`. A row with fewer than four
    cells yields the empty string, which `check()` reports as an unfilled decision.
    """
    out: dict[str, str] = {}
    # silent-degradation: ok -- non-table lines are the normal case here; "no row parsed at
    # all" is reported explicitly by check(), it does not become a green empty set.
    for line in prereg_text.splitlines():
        m = TABLE_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        value = cells[3] if len(cells) >= 4 else ""
        out[m.group(1)] = value.strip("`* ").lower()
    return out


def waiver(prereg_text: str) -> str | None:
    """The body of a `<!--@pilot_gate: ...-->` anchor, or None when there is none.

    An anchor body must not contain `>`; the parser stops at the first one and the
    anchor then silently does not exist — same rule as the goal anchors.
    """
    # silent-degradation: ok -- most registrations carry no waiver; None is the normal
    # return and check() treats it as "no waiver", never as "waived".
    m = ANCHOR.search(prereg_text)
    return m.group(1).strip() if m else None


def units_in(keys) -> set[str]:
    """Recognise unit names among JSON keys (`S1_env_unchanged` -> `S1`)."""
    # silent-degradation: ok -- keys like `schema` or `provenance` are not unit names;
    # an empty result is reported by the caller, not swallowed.
    return {m.group(1) for k in keys if (m := UNIT_KEY.match(k))}


def produced(out_dir: pathlib.Path) -> set[str]:
    """Units a pilot run computed: `summary.json` and `reproduction.json` read together."""
    found: set[str] = set()
    for name in ("summary.json", "reproduction.json"):
        path = out_dir / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        found |= units_in(list(data.get("units", {})) + list(data))
    return found


def ledger_units(ledger: pathlib.Path) -> set[str]:
    """Every unit any recorded pilot run produced. A missing ledger is the empty set —
    and `check()` then says so for every `seen` row, which is the point."""
    if not ledger.exists():
        return set()
    found: set[str] = set()
    for number, line in enumerate(
        ledger.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        entry = json.loads(
            line
        )  # malformed ledger lines raise: a broken record is not a record
        units = entry.get("units")
        if not isinstance(units, list):
            raise SystemExit(
                f"{ledger} line {number} has no `units` list — not a pilot record"
            )
        found |= set(units)
    return found


def goal_commitments(goal_text: str) -> str | None:
    """A digest of the four `goal.md` anchors that fix what is being bet on, or None.

    Whitespace inside an anchor body is normalised, so reflowing a line does not read as
    a changed commitment. None when no commitment anchor parses at all — an unfilled
    `goal.md` is `goal_ready`'s business, not this gate's, and reporting it twice would
    send the author to fix the same thing from two directions.
    """
    found: dict[str, str] = {}
    for m in GOAL_ANCHOR.finditer(goal_text):
        name = m.group(1).lower()
        if name in COMMITMENTS:
            found[name] = " ".join(m.group(2).split())
    if not found:
        return None
    blob = "\n".join(f"{k}={found[k]}" for k in sorted(found))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def goal_change_note(prereg_text: str) -> str | None:
    """The body of a `<!--@goal_changed: ...-->` anchor in prereg.md, or None.

    Same `>`-stops-the-body rule as every other anchor in this project.
    """
    m = GOAL_CHANGED.search(prereg_text)
    return m.group(1).strip() if m else None


def _latest(ledger: pathlib.Path, key: str) -> str | None:
    """The value `key` holds in the **most recent** pilot run that recorded it, or None.

    Most recent, not "any run matched": a pilot in an environment you have since left, or
    under commitments you have since rewritten, proves nothing about what is about to be
    frozen. None covers a missing ledger and records written before the key existed —
    those must stay green, or every registration already in flight becomes unfreezable.
    """
    if not ledger.exists():
        return None
    newest: str | None = None
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line).get(key)   # malformed lines raise, same rule as ledger_units
        if isinstance(value, str) and value:
            newest = value
    return newest


def latest_goal(ledger: pathlib.Path) -> str | None:
    """The goal-commitments digest of the most recent pilot run, or None."""
    return _latest(ledger, "goal_sha256")


def latest_env(ledger: pathlib.Path) -> str | None:
    """The environment digest of the most recent pilot run, or None."""
    return _latest(ledger, "env_sha256")


def latest_python(ledger: pathlib.Path) -> str | None:
    """The interpreter the most recent pilot ran under, or None — named in the refusal
    when the environment differs, because two newlife installations on one machine are the
    common cause and a digest alone does not say so."""
    return _latest(ledger, "python")




def check(rows: dict[str, str], ledger: set[str], waived: str | None,
          piloted_env: str | None = None, live_env: str | None = None,
          piloted_goal: str | None = None, live_goal: str | None = None,
          goal_note: str | None = None,
          piloted_python: str | None = None, live_python: str | None = None) -> list[str]:
    """A pure predicate over parsed inputs — which is what lets the selftest prove it can go red."""
    if waived is not None and waived.startswith("not_applicable"):
        return []
    problems: list[str] = []
    # **The environment the pilot ran in must still be the one being frozen.** Both digests
    # known and different means: install/upgrade/removal since the pilot, so the runner has
    # never been executed in the environment `env.lock` is about to record. S1 will not
    # catch it — the freeze rewrites `env.lock` from the live environment, so S1 goes green
    # against an environment nobody ever ran. And the freeze is irreversible: discovering
    # it at run time leaves no move, because repairing the environment then turns S1 red.
    if piloted_env and live_env and piloted_env != live_env:
        problems.append(
            f"the environment changed after the last pilot (pilot {piloted_env[:12]}, "
            f"now {live_env[:12]}) — the runner has never run in the environment this "
            f"freeze would record. Run `newlife pilot` again, then freeze. Finding this "
            f"out after the freeze leaves no move: the freeze is irreversible, and "
            f"repairing the environment afterwards turns S1 red."
            + (f" The pilot ran under {piloted_python} and this freeze under {live_python}: "
               f"two newlife installations are two environments — run pilot and freeze "
               f"from the same one."
               if piloted_python and live_python and piloted_python != live_python else "")
        )
    # **What is being bet on must not have moved since the pilot.** Rule one sends the pilot
    # to look at every quantity a criterion names, so it can hand you the answer to the main
    # criterion before the freeze; flipping H1 afterwards would pass every other gate and
    # leave no trace in any file. This is the only gate that can see it. A change is not
    # forbidden — it is recorded, so that "we confirmed A" and "A was chosen after seeing B"
    # cannot become one sentence at closeout.
    if piloted_goal and live_goal and piloted_goal != live_goal and goal_note is None:
        problems.append(
            "goal.md's commitments changed after the last pilot (counterparty / "
            "attack_layer / decides / who_changes_behavior). The pilot may change **how** "
            "you measure, never **what** you measure or which way you expect it to go — "
            "see newlife-prereg rule one. If the change is legitimate (a re-pointing at "
            "data never read, a fallback to a hypothesis written before the pilot), record "
            "it: <!--@goal_changed: what moved, and why it is not a response to the "
            "pilot--> in prereg.md."
        )
    if not rows:
        problems.append(
            "no judgement unit parsed out of prereg.md §2 — table rows must look "
            'like `| **S1** | … | … | seen |`. On an empty table, "everything '
            'was piloted" would be true by construction.'
        )
        return problems
    for unit, value in sorted(rows.items()):
        if value not in VALUES:
            shown = value or "an empty cell"
            problems.append(
                f"{unit}: the Piloted? column holds {shown!r} — every row must "
                f"say seen / blind / mechanical. An empty cell is a decision "
                f"not yet made, and the freeze is where it has to be made."
            )
    for unit, value in sorted(rows.items()):
        if value == "seen" and unit not in ledger:
            problems.append(
                f"{unit}: marked seen, but no run in pilot/ledger.jsonl produced "
                f'it. Run `newlife pilot` — "I derived it, so I know" does not '
                f"count as having looked (two registrations were lost to exactly "
                f"that)."
            )
    if not any(v == "blind" for v in rows.values()):
        if waived is None or not waived.startswith("no_blind_waived"):
            problems.append(
                "no unit is blind — a confirmatory round in which every number "
                "was already seen while drafting carries no information. Mark "
                "one row blind (derive it from the mechanism: a parameter never "
                "swept, a scale never run), or waive it on the record: "
                "<!--@pilot_gate: no_blind_waived — why-->"
            )
    return problems


# ─────────────────────────── negative control ───────────────────────────
READY = """
| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | Self-reproduction | byte-identical rerun | mechanical |
| **S1** | Environment unchanged | env.lock digest matches | mechanical |
| **S2** | Steady state matched | relative error below 1e-3 | seen |
| **S3** | every criterion proves it can fail | synthetic counterexamples | mechanical |
| **S4** | Gap shrinks with the decay rate | strictly decreasing over a | blind |
"""
"""One registration that is genuinely ready, paired with a ledger that produced S2.
**The gate must be green on this** — a gate that only goes red is as useless as one that
only goes green."""
READY_LEDGER = {"S0", "S1", "S2", "S3"}

GOAL_BEFORE = """
<!--@evidence: literature_searched=yes, sources=3, verdict=unknown-->
<!--@counterparty: iModulon authors, who hold that regulon overlap is the right yardstick-->
<!--@attack_layer: conclusion-->
<!--@decides: run-->
<!--@who_changes_behavior: a method developer choosing a decomposition-->
<!--@size_estimate: impl_lines=200, criteria=1, failure_modes=1-->
"""
"""The commitments as they stood when the pilot ran."""

GOAL_AFTER = GOAL_BEFORE.replace(
    "iModulon authors, who hold that regulon overlap is the right yardstick",
    "nobody in particular; we now expect no effect",
)
"""The same file after the pilot answered the main criterion and the bet was rewritten.
**This is the move the gate exists to catch.**"""

GOAL_REFLOWED = GOAL_BEFORE.replace(
    "iModulon authors, who hold that regulon overlap is the right yardstick",
    "iModulon authors,  who hold that regulon overlap\n  is the right yardstick",
)
"""Same commitment, rewrapped. Must digest identically, or the gate cries wolf at every edit."""

GOAL_ESTIMATE_REVISED = GOAL_BEFORE.replace("impl_lines=200", "impl_lines=340")
"""Revising an estimate is bookkeeping, not a change to what is being bet on."""


def _selftest() -> int:
    ok = True

    def case(
        name: str,
        rows: dict[str, str],
        ledger: set[str],
        waived: str | None,
        want_red: bool,
        piloted_env: str | None = None,
        live_env: str | None = None,
        piloted_goal: str | None = None,
        live_goal: str | None = None,
        goal_note: str | None = None,
    ) -> None:
        nonlocal ok
        red = bool(check(rows, ledger, waived, piloted_env, live_env,
                         piloted_goal, live_goal, goal_note))
        mark = "RED" if red else "green"
        if red != want_red:
            print(
                f"  [FAIL] {name}: got {mark}, expected {'RED' if want_red else 'green'}"
            )
            ok = False
        else:
            print(f"  [{mark}] {name}")

    rows = piloted(READY)
    if rows != {
        "S0": "mechanical",
        "S1": "mechanical",
        "S2": "seen",
        "S3": "mechanical",
        "S4": "blind",
    }:
        print(f"  [FAIL] table parser: {rows}")
        ok = False
    if units_in(["S1_env_unchanged", "S0_byte_identical_on_rerun", "schema"]) != {
        "S0",
        "S1",
    }:
        print("  [FAIL] unit names in JSON keys not recognised")
        ok = False
    if (
        waiver("x <!--@pilot_gate: no_blind_waived — smoke--> y")
        != "no_blind_waived — smoke"
    ):
        print("  [FAIL] waiver anchor not parsed")
        ok = False
    if waiver("<!--@pilot_gate: not_applicable — <r>-->") is not None:
        print("  [FAIL] an anchor body containing `>` must not parse")
        ok = False
    print(f"  [{'green' if ok else 'RED'}] parsers: table, JSON keys, waiver anchor")

    case("a registration that is genuinely ready", rows, READY_LEDGER, None, False)
    case("S2 seen but never piloted", rows, {"S0", "S1", "S3"}, None, True)
    case("S2 seen, no ledger at all", rows, set(), None, True)
    no_blind = {**rows, "S4": "seen"}
    case("nothing blind, not waived", no_blind, READY_LEDGER | {"S4"}, None, True)
    case(
        "nothing blind, waived on the record",
        no_blind,
        READY_LEDGER | {"S4"},
        "no_blind_waived — smoke test, no claim about the world",
        False,
    )
    case("an empty Piloted? cell", {**rows, "S2": ""}, READY_LEDGER, None, True)
    case("an unknown value", {**rows, "S2": "yes"}, READY_LEDGER, None, True)
    case(
        "the scaffolded table (S2 undecided, nothing blind)",
        {"S0": "mechanical", "S1": "mechanical", "S2": "", "S3": "mechanical"},
        set(),
        None,
        True,
    )
    case("no row parsed at all", {}, READY_LEDGER, None, True)
    case(
        "the whole stage waived",
        {},
        set(),
        "not_applicable — a toolchain smoke test",
        False,
    )
    case(
        "a package installed between the pilot and the freeze",
        rows, READY_LEDGER, None, True,
        piloted_env="a" * 64, live_env="b" * 64,
    )
    case(
        "the environment is the one the pilot ran in",
        rows, READY_LEDGER, None, False,
        piloted_env="a" * 64, live_env="a" * 64,
    )
    case(
        "a ledger written before env_sha256 existed",
        rows, READY_LEDGER, None, False,
        piloted_env=None, live_env="b" * 64,
    )

    # ── the commitments in goal.md ──
    g1, g2 = goal_commitments(GOAL_BEFORE), goal_commitments(GOAL_AFTER)
    if not g1 or g1 == g2:
        print("  [FAIL] the two fixture goals must digest differently")
        ok = False
    if goal_commitments(GOAL_BEFORE) != goal_commitments(GOAL_REFLOWED):
        print("  [FAIL] reflowing an anchor body must not change the digest")
        ok = False
    if goal_commitments(GOAL_BEFORE) == goal_commitments(GOAL_ESTIMATE_REVISED):
        pass  # evidence/size_estimate are outside COMMITMENTS; see the next check
    if goal_commitments(GOAL_BEFORE) != goal_commitments(GOAL_ESTIMATE_REVISED):
        print("  [FAIL] revising size_estimate is bookkeeping and must not go red")
        ok = False
    if goal_commitments("no anchors here") is not None:
        print("  [FAIL] a goal with no commitment anchor must digest to None")
        ok = False
    if goal_change_note("x <!--@goal_changed: re-pointed at RPE1--> y") != "re-pointed at RPE1":
        print("  [FAIL] the goal_changed anchor did not parse")
        ok = False
    print(f"  [{'green' if ok else 'RED'}] goal digest: differs, stable under reflow, ignores bookkeeping")

    case(
        "the counterparty was rewritten after the pilot",
        rows, READY_LEDGER, None, True,
        piloted_goal=g1, live_goal=g2,
    )
    case(
        "the commitments are the ones the pilot ran against",
        rows, READY_LEDGER, None, False,
        piloted_goal=g1, live_goal=g1,
    )
    case(
        "changed, and recorded on the record",
        rows, READY_LEDGER, None, False,
        piloted_goal=g1, live_goal=g2,
        goal_note="re-pointed at RPE1, never read; direction of H1 unchanged",
    )
    case(
        "a ledger written before goal_sha256 existed",
        rows, READY_LEDGER, None, False,
        piloted_goal=None, live_goal=g2,
    )

    print(
        "  selftest passed: parsers correct, every omission red, the ready registration green."
        if ok
        else "  selftest FAILED."
    )
    # The refusal must name both interpreters when the environment differs and the
    # ledger recorded where the pilot ran — two newlife installations on one machine are
    # the common cause, and two digests alone do not say so.
    named = check(rows, READY_LEDGER, None, piloted_env="a" * 64, live_env="b" * 64,
                  piloted_python="/venv-a/bin/python", live_python="/venv-b/bin/python")
    if not any("/venv-a/bin/python" in m and "/venv-b/bin/python" in m for m in named):
        print("  [FAIL] environment changed under a different interpreter: neither path named")
        ok = False
    else:
        print("  [RED] environment changed, both interpreters named")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder", nargs="?", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.folder is None:
        ap.error("pass a question folder, or --selftest")

    prereg = args.folder / "prereg.md"
    if not prereg.exists():
        print(f"{prereg} does not exist — this is not a question folder.")
        return 1
    text = prereg.read_text(encoding="utf-8")
    ledger = args.folder / "pilot" / "ledger.jsonl"
    goal = args.folder / "goal.md"
    live_goal = goal_commitments(goal.read_text(encoding="utf-8")) if goal.exists() else None
    problems = check(piloted(text), ledger_units(ledger), waiver(text),
                     piloted_env=latest_env(ledger), live_env=provenance.env_digest(),
                     piloted_goal=latest_goal(ledger), live_goal=live_goal,
                     goal_note=goal_change_note(text),
                     piloted_python=latest_python(ledger), live_python=sys.executable)
    for p in problems:
        print(f"[FAIL] {prereg.name}: {p}")
    if problems:
        print(
            f"\nThe criteria are not covered by a pilot: {len(problems)} item(s). Two of the "
            f"first four real registrations were lost to exactly this, so the freeze checks it."
        )
        return 1
    rows = piloted(text)
    blind = sorted(u for u, v in rows.items() if v == "blind")
    print(
        f"Pilot coverage: {len(rows)} unit(s) all marked, every seen unit has a run behind "
        f"it, blind: {' '.join(blind) if blind else 'none (waived on the record)'}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
