#!/usr/bin/env python3
"""The units a registration declares must match, one for one, the units the runner computes.

## Why this gate exists

The first time the user-repository flow was walked end to end, one step was done **by
hand**: matching the unit names in `prereg.md` §2 against the keys the runner emits under
`units`. **Nothing checked it.** So this hole was wide open:

    the registration says  verdict = S0 ∧ S1 ∧ S2 ∧ S3
    the runner computed only three — **and nobody would notice**

This belongs to the same family as a criterion that is true by construction: that one is
"computed but vacuous", this one is "declared but never computed". Both make the
conjunction look stronger than it is.

The reverse is checked too: **a unit present in the artifact that the registration never
declared** is a criterion added after the fact — HARKing at the level of a single unit.

## Three checks

1. the units in `prereg.md` §2's table == the units in the `verdict = …` conjunction
2. the declared units == the units actually computed in the artifact
3. `S0` is special: it lands in `reproduction.json`, not `summary.json` (the record of a
   reproduction cannot live inside the artifact being reproduced) — the two files are read
   together as "what the artifact contains"

    python -m newlife.gates.unit_alignment <question-folder>
    python -m newlife.gates.unit_alignment --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Iterable

TABLE_ROW = re.compile(r"^\|\s*\*\*([^*]+)\*\*\s*\|")
"""(Row head, the bolded cell.) **A row may carry an alias**: `| **U0 (S0)** | …`
(2026-09-09-proteome-*) — the row's own name first, the artifact's name second. The cell
is captured whole and split in `declared()`; a pattern that demanded `**` right after the
name read those rows as absent and produced an alarm about the parser, aimed at the
author. Reading both names as independent units was a second way to be wrong: the table
then claimed a unit the conjunction could not mention."""
# Stops at a period of either script. **Written for Chinese text first**: with only `。`
# in the class, an English line `verdict = S0 ∧ S1. Any one false -> H0` swallowed the
# whole sentence and reported `H0` as an undefined unit. The selftest missed it because
# its fixture also used `。` — **a check too narrow to reach the case it was guarding.**
CONJUNCTION = re.compile(r"verdict\s*=\s*([^.。\n]*)")
UNIT_TOKEN = re.compile(r"\b([A-Z]+\d+)\b")        # in prose: S0 ∧ S1 ∧ …
# In JSON keys: `S1_env_unchanged`. **`\b` does not work here** — there is no word
# boundary between `1` and `_`, so nothing matches at all, and "the artifact contains no
# units" then looks like "the runner computed none".
# That is exactly how this was first written, and all four units were reported missing.
# **A check that is too naive and a check that is too weak are two faces of one disease.**
UNIT_KEY = re.compile(r"^([A-Z]+\d+)(?:_|$)")


def declared(prereg_text: str) -> tuple[set[str], set[str], dict[str, str]]:
    """(units declared in the table, units appearing in the conjunction, alias -> primary).

    **A table row may carry an alias — `| **U0 (S0)** | …`** (2026-09-09-proteome-*): the
    row's own name first, then the name the artifact keys use. An alias is the *same*
    unit, not a second one, so it is recorded as a mapping and never as a table member —
    treating both names as independent made the table claim a unit the conjunction could
    not mention, and the gate then reported the registration for a naming choice the
    registration had already declared. A pattern that demanded `**` right after the name
    read those rows as absent and produced a third alarm, from the parser itself.
    """
    # silent-degradation: ok — per-line filtering: skipping a non-table row is this
    # function's normal branch. The aggregate outcome "nothing matched at all" is reported
    # explicitly by `check()` (an empty table goes red immediately).
    table: set[str] = set()
    aliases: dict[str, str] = {}
    for line in prereg_text.splitlines():
        m = TABLE_ROW.match(line)
        if not m:
            continue
        names = UNIT_TOKEN.findall(m.group(1))
        if not names:
            continue
        table.add(names[0])
        for alias in names[1:]:
            aliases[alias] = names[0]
    conj: set[str] = set()
    # silent-degradation: ok — as above; a missing conjunction is reported by `check()`
    # as "declared in the table, absent from the conjunction".
    for m in CONJUNCTION.finditer(prereg_text):
        body = m.group(1)
        # **Only a line that actually conjoins is a conjunction.** Two false alarms,
        # 2026-09-10, both from prose that merely names a result: `verdict=H1`
        # (backbone-v2 §0, one token) and `verdict=H0：S3 标签失败、S0/S1/S2/S4/S5 过`
        # (backbone §0, several — so "at least two tokens" does not separate them).
        # Every real conjunction line carries `∧`; requiring it removes both alarms
        # without weakening the check.
        if "∧" not in body:
            continue
        conj |= set(UNIT_TOKEN.findall(body))
    return table, conj, aliases


def canon(names: Iterable[str], aliases: dict[str, str]) -> set[str]:
    """Resolve aliases to the row's own name so the three sets compare in one namespace."""
    return {aliases.get(n, n) for n in names}


def units_in(keys: Iterable[str]) -> set[str]:
    """Recognise unit names among JSON keys.

    **Factored out so the selftest can exercise it directly** — the original bug was here,
    not in the judgement logic.
    """
    # silent-degradation: ok — keys like `schema`/`provenance` are not unit names.
    # "recognised none at all" is reported explicitly by `check()`, deliberately worded
    # so it cannot be mistaken for "no criterion was computed".
    return {m.group(1) for k in keys if (m := UNIT_KEY.match(k))}


def produced(folder: pathlib.Path) -> set[str]:
    """Units actually computed in the artifact. **Both files are read together** — S0
    lives on the reproduction side."""
    found: set[str] = set()
    for name in ("summary.json", "reproduction.json"):
        path = folder / "results" / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        found |= units_in(list(data.get("units", {})) + list(data))
    return found


def check(table: set[str], conj: set[str], made: set[str],
          aliases: dict[str, str] | None = None) -> list[str]:
    """**A pure predicate** — which is what lets the selftest prove it can go red."""
    aliases = aliases or {}
    tbl, cj, md = canon(table, aliases), canon(conj, aliases), canon(made, aliases)
    problems = []
    if not table:
        problems.append("no judgement unit parsed out of prereg.md §2 — table rows must "
                        "look like `| **S1** | … |`. On an empty set, \"everything lines "
                        "up\" is true by construction.")
        return problems
    for missing in sorted(tbl - cj):
        problems.append(f"{missing}: declared in the table but absent from the "
                        f"`verdict = …` conjunction — it takes no part in the judgement")
    for extra in sorted(cj - tbl):
        problems.append(f"{extra}: appears in the conjunction but is not defined in the "
                        f"table — nobody can say what it means")
    if not made:
        problems.append("no judgement unit parsed out of the artifact — either the runner "
                        "has not been run, or the `units` keys are not shaped like `S1_…`. "
                        "This is not the same as \"no criterion was computed\": one "
                        "wrong character in the parser once reported all four units as "
                        "missing, pointing the reader somewhere entirely wrong.")
        return problems
    for missing in sorted(tbl - md):
        problems.append(f"{missing}: declared in the registration but absent from the "
                        f"artifact — the criterion is on paper, the power is not in the code")
    for extra in sorted(md - tbl):
        problems.append(f"{extra}: computed in the artifact but never declared — a "
                        f"criterion added after the fact, HARKing at the unit level")
    return problems


SELFTEST_PREREG = """
| **S0** | self-reproduction | … |
| **S1** | environment unchanged | … |
| **S2** | positive control | … |

**verdict = S0 ∧ S1 ∧ S2.** Any one false -> H0; **S0 false -> INVALID**.
"""
"""**Deliberately written the way the shipped English template writes it** — including the
sentence after the period. The first fixture ended at `。` and therefore never exercised
the case that actually broke."""

SELFTEST_PROSE_WITH_RESULT = """
The predecessor round reproduced the same number; its verdict=H1 after the fix.
Earlier, quoting v1: （…，verdict=H0：S3 标签失败、S0/S1/S2/S4/S5 过）。The rest is prose.
"""
"""**Prose that names a verdict, not a conjunction — in both observed shapes.** 2026-09-10:
`verdict=H1` (chemistry-fim-backbone-v2 §0) and `verdict=H0：S3 …、S0/S1/…` (backbone §0)
each produced a permanent, unresolvable false alarm ("appears in the conjunction but is
not defined in the table"). The second has several unit-shaped tokens, which is why the
separator — not the token count — is what tells a conjunction apart. The fixture keeps
both cases reachable."""

SELFTEST_ALIASED_ROW = """
| **U0 (S0)** | self-reproduction | … |
| **U1** | environment unchanged | … |

**verdict = U0 ∧ U1.** Any one false -> H0.
"""
"""**A row may carry an alias.** 2026-09-09-proteome-* write `| **U0 (S0)** | …`; a
pattern demanding `**` right after the name read that row as absent and then reported
the aliased unit twice — once from each side of the comparison."""


def _selftest() -> int:
    """Negative control: four kinds of mismatch must each go red, the aligned case green;
    **plus two assertions on the parsers themselves**.

    The first version tested only `check()`, not the parsers — and the bug actually made
    while drafting was in `produced()` (`\b` does not hold between `1` and `_` in
    `S1_env_unchanged`, so no key was recognised and all four units were reported
    missing). **Testing the judgement logic but not the parsing is a check that is too
    weak.**
    """
    ok = True
    if units_in(["S1_env_unchanged", "S0_byte_identical_on_rerun", "schema"]) != {"S0", "S1"}:
        print("  [FAIL] unit names in JSON keys not recognised"); ok = False
    if declared(SELFTEST_PREREG) != ({"S0", "S1", "S2"}, {"S0", "S1", "S2"}, {}):
        print("  [FAIL] unit names in the prereg table or conjunction not recognised"); ok = False
    if declared(SELFTEST_PREREG + SELFTEST_PROSE_WITH_RESULT) != ({"S0", "S1", "S2"}, {"S0", "S1", "S2"}, {}):
        print("  [FAIL] prose naming a result (verdict=H1 / verdict=H0：…) was read as a conjunction"); ok = False
    if declared(SELFTEST_ALIASED_ROW) != ({"U0", "U1"}, {"U0", "U1"}, {"S0": "U0"}):
        print("  [FAIL] an aliased table row (**U0 (S0)**) was not read as U0 with alias S0"); ok = False
    if check({"U0", "U1"}, {"U0", "U1"}, {"S0", "U1"}, {"S0": "U0"}):
        print("  [FAIL] an artifact keyed by the row's alias was reported as undeclared"); ok = False
    print(f"  [{'green' if ok else 'RED'}] parsers: JSON keys and the prereg table/conjunction")

    full = {"S0", "S1", "S2"}
    cases = [
        ("everything aligns", full, full, full, False),
        ("declared but never computed", full, full, {"S0", "S1"}, True),
        ("computed but never declared", {"S0", "S1"}, {"S0", "S1"}, full, True),
        ("in the table, absent from the conjunction", full, {"S0", "S1"}, full, True),
        ("no unit parsed from the registration", set(), full, full, True),
        ("no unit present in the artifact", full, full, set(), True),
    ]
    for name, table, conj, made, want_red in cases:
        red = bool(check(table, conj, made))
        mark = "RED" if red else "green"
        if red != want_red:
            print(f"  [FAIL] {name}: got {mark}, expected {'RED' if want_red else 'green'}")
            ok = False
        else:
            print(f"  [{mark}] {name}")
    print("  selftest passed: parsers correct, every mismatch red, the aligned case green."
          if ok else "  selftest FAILED.")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
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
    table, conj, aliases = declared(prereg.read_text())
    made = produced(args.folder)
    problems = check(table, conj, made, aliases)
    for p in problems:
        print(f"{args.folder}: {p}")
    if problems:
        print(f"\n{len(problems)} misalignment(s). What the registration says and what "
              f"the code does must match word for word — one unit short and the "
              f"conjunction is weaker than it looks.")
        return 1
    print(f"{args.folder}: units aligned — {len(table)} declared "
          f"({' '.join(sorted(table))}), every one present in the artifact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
