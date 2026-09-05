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
import json
import pathlib
import re

TABLE_ROW = re.compile(r"^\|\s*\*\*([A-Z]+\d+)\*\*\s*\|")
ANCHOR = re.compile(r"<!--@pilot_gate:\s*([^>]*?)-->")
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


def check(rows: dict[str, str], ledger: set[str], waived: str | None) -> list[str]:
    """A pure predicate over parsed inputs — which is what lets the selftest prove it can go red."""
    if waived is not None and waived.startswith("not_applicable"):
        return []
    problems: list[str] = []
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


def _selftest() -> int:
    ok = True

    def case(
        name: str,
        rows: dict[str, str],
        ledger: set[str],
        waived: str | None,
        want_red: bool,
    ) -> None:
        nonlocal ok
        red = bool(check(rows, ledger, waived))
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

    print(
        "  selftest passed: parsers correct, every omission red, the ready registration green."
        if ok
        else "  selftest FAILED."
    )
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
    problems = check(piloted(text), ledger_units(ledger), waiver(text))
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
