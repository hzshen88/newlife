#!/usr/bin/env python3
"""Scan for fake sweeps: comprehensions that are **named a sweep but are a repetition**.

## Why this gate exists

A negative control once had its criterion frozen as "set `yield` to the value dFBA
reaches at one point, **re-sweep**, and confirm Monod's yield still does not move".
The implementation was:

    monod_pinned = [_run(MONOD, "foreign-monod", pinned) for _ in O2_SWEEP]

`O2_SWEEP` is iterated, but **the loop variable is discarded** — five runs of the same
configuration. So the criterion `max - min < 1e-9` was true under **any** physical
configuration (measured: green for `yield` from 1e-6 to 1e3), with zero discriminating
power. It sat inside the conjunction for an entire milestone, because **a criterion that
is true by construction never goes red, and people only investigate what is red.**

## The rule

A comprehension over a **named module-level constant** whose loop variable is never
referenced in the element expression -> reported.

`range(n)` is not reported: comprehending over it means "repeat n times", which is a
legitimate way to write replicate trials in a stochastic process. **A named constant is
different** — giving a set of values a name says the values themselves matter.

    python3 vacuous_criterion_scan.py <file.py> ...
    python3 vacuous_criterion_scan.py --selftest
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys

Finding = tuple[int, str, str]      # line number, constant name, loop variable


def _named_constants(tree: ast.Module) -> set[str]:
    """Names bound by a module-level `NAME = <sequence literal>`."""
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Tuple, ast.List, ast.Set)):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _targets(node: ast.expr) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def scan(source: str) -> list[Finding]:
    tree = ast.parse(source)
    constants = _named_constants(tree)
    findings: list[Finding] = []
    comprehensions = (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
    for node in ast.walk(tree):
        if not isinstance(node, comprehensions):
            continue
        # Element expression: DictComp has key/value, the rest have elt
        parts = ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt])
        used = set().union(*(_targets(p) for p in parts))
        for gen in node.generators:
            if not (isinstance(gen.iter, ast.Name) and gen.iter.id in constants):
                continue
            bound = _targets(gen.target)
            if not (bound & used):
                findings.append((node.lineno, gen.iter.id,
                                 ", ".join(sorted(bound)) or "_"))
    return findings


SELFTEST_RED = "SWEEP = (1, 2, 3)\nxs = [run(cfg) for _ in SWEEP]\n"
SELFTEST_GREEN = ("SWEEP = (1, 2, 3)\n"
                  "xs = [run(cfg(v)) for v in SWEEP]\n"
                  "ys = [make() for _ in range(3)]\n")


def _selftest() -> int:
    """Negative control: a fake sweep must be caught; a real sweep and a `range`
    repetition must not be."""
    ok = True
    if not scan(SELFTEST_RED):
        print("  [FAIL] a fake sweep discarding its loop variable was not reported"); ok = False
    if scan(SELFTEST_GREEN):
        print(f"  [FAIL] false positive on a real sweep / range repetition: {scan(SELFTEST_GREEN)}"); ok = False
    print("  selftest passed: fake sweep red, real sweep and range repetition green."
          if ok else "  selftest FAILED.")
    return 0 if ok else 1


KNOWN_VACUOUS = {("newlife/conform/yield_verdict.py", "O2_SWEEP"): 2}
"""**Disposition already made (2026-09-04). This is not a to-do.**

That milestone's registration is frozen and its artifact reproduces byte-identically.
Editing the runner would destroy that reproduction, so **it is not edited** — following
the precedent of `verdict_rot.KNOWN_BROKEN`: record it, do not hide it, do not rewrite
history.

The two occurrences are the Monod sweeps behind Z4 and Z5. Z5 is therefore **true by
construction with zero discriminating power** (measured: green for `yield` from 1e-6 to
1e3). Z4 compares each point against a declared constant, which holds at a single point,
so it is unaffected — but it is printed alongside the oxygen column in the artifact, where
it reads like a sweep. The conclusion does not depend on Z5: Z3 (dFBA's yield varies with
oxygen by 56%) and Z4 (Monod's is constant) already entail it arithmetically.

Full disposition: `docs/zh/worlds/019-yield-input-or-outcome.md`.
**The registered figure is an exact count**: one more fake sweep on the same constant in
the same file, or these two disappearing, both turn this red — an exemption neither
accumulates silently nor becomes a zombie.
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=pathlib.Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)          # None -> read sys.argv; unchanged when run as a script
    if args.selftest:
        return _selftest()

    seen: dict[tuple[str, str], int] = {}
    # A registered entry is only checked when **its file was actually scanned** — a
    # narrower scan does not mean the defect went away, and treating "not scanned" as
    # "already fixed" is silent degradation itself.
    in_scope = {k for k in KNOWN_VACUOUS
                if any(str(q).endswith(k[0]) for q in args.paths)}
    unregistered = 0
    for path in args.paths:
        for lineno, const, target in scan(path.read_text()):
            key = next((k for k in KNOWN_VACUOUS
                        if str(path).endswith(k[0]) and k[1] == const), None)
            if key is not None:
                seen[key] = seen.get(key, 0) + 1
                continue
            unregistered += 1
            print(f"{path}:{lineno}: iterates the named constant {const}, but the loop "
                  f"variable {target} is never used — this is not a sweep, it is a "
                  f"repetition len({const}) times")

    drifted = [(k, KNOWN_VACUOUS[k], seen.get(k, 0))
               for k in in_scope if seen.get(k, 0) != KNOWN_VACUOUS[k]]
    for (rel, const), want, got in drifted:
        print(f"{rel}: {want} known fake sweep(s) registered on {const}, {got} found — "
              f"{'the registration is stale' if got < want else 'a new, unregistered one appeared'}")

    for rel, const in in_scope:
        want = KNOWN_VACUOUS[(rel, const)]
        if not any(k == (rel, const) for k, *_ in drifted):
            print(f"[registered] {rel}: {want} on {const}; disposition in the KNOWN_VACUOUS docstring")

    if unregistered:
        print(f"\n{unregistered} unregistered fake sweep(s). A criterion built on one is true by "
              f"construction — a negative control that cannot go red is not a control.")
    return 1 if (unregistered or drifted) else 0


if __name__ == "__main__":
    raise SystemExit(main())
