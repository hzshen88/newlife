#!/usr/bin/env python3
"""Classify a verdict bundle by **what kind of reproduction its world can offer**.

## Why this exists

`verdict.py` carries exactly one reproduction safety line: S0, byte-identical rerun, and
`final = verdict if s0 else "INVALID"`. For a deterministic world that is strong and cheap.
For a world whose outcome genuinely varies between runs — parallel reductions, concurrency,
a remote service — it **cannot** be satisfied, so that entire class of world produces no
verdict at all. Not a weaker conclusion: none.

The literature already separates `bitwise` from `statistical / distributional`
reproducibility (earth-system modelling, HPC, astrophysics — where "reproduced" routinely
means recovering a feature statistically, because bitwise identity is infeasible on those
machines). **But that is a descriptive vocabulary, used after the fact to say how far a
reproduction went.** This module asks whether the distinction can be *decided from what a
bundle already contains*.

## What is deliberately NOT a feature, and why

**`subprocess` is not treated as an external source.** newlife's own reproduction
machinery shells out to `sys.executable` to rerun the runner, and runners read git commits
the same way. At the AST level "shelled out to re-run myself" and "shelled out to something
nondeterministic" are the same node. Including it would classify **every** world as
`stochastic` — a feature that fires everywhere decides nothing.

The cost is recorded rather than hidden: a runner that shells out to a genuinely
nondeterministic external program is **missed** by this classifier. That is a known hole,
declared in the registration's boundary section, not a silent approximation.

**Clock reads are a feature, but only when they are not the stamp.** `datetime.now()`
appears in every runner that stamps an output directory. Only calls whose result feeds a
computation would matter, and static analysis cannot tell — so the clock feature requires
the call to appear **outside** a string/stamp context, which in practice means it is
approximated by module of origin (`time.time`, `time.monotonic`) rather than
`datetime.now`. Also a declared approximation.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import pathlib
import sys

# ─────────────────────────── the frozen feature table ───────────────────────────

NETWORK_MODULES = frozenset({"urllib", "urllib.request", "requests", "httpx", "socket",
                             "http.client", "aiohttp"})
CONCURRENCY_MODULES = frozenset({"threading", "multiprocessing", "concurrent.futures",
                                 "asyncio"})
CLOCK_CALLS = frozenset({"time.time", "time.monotonic", "time.perf_counter"})
RNG_MODULES = frozenset({"random", "numpy.random", "secrets"})
PROOFROOT_RNG = frozenset({"RngBank", "derive_stream_seed", "EVIDENCECORE_RNG_V1"})

REASONS = ("no_runner_found", "rng_without_traceable_seed",
           "mixed_seeded_and_stochastic", "no_feature_matched")
"""The only admissible reasons for `unclassified`. **Prose does not decide anything** —
the eighteenth milestone's lesson was that a difference is only defensible when code
computed the category, not when a paragraph argued for it."""


@dataclasses.dataclass(frozen=True)
class Features:
    """What was found. **Every field is observed, none is inferred from intent.**"""
    rng: bool = False
    traceable_seed: bool = False
    network: bool = False
    concurrency: bool = False
    clock: bool = False
    runner_found: bool = True

    @property
    def external(self) -> bool:
        return self.network or self.concurrency or self.clock


def classify(f: Features) -> tuple[str, str | None]:
    """Features -> (class, reason-if-unclassified). **A pure predicate**, which is what
    lets the selftest prove each branch can be reached and each can go red."""
    if not f.runner_found:
        return "unclassified", "no_runner_found"
    if f.rng and f.external:
        return "unclassified", "mixed_seeded_and_stochastic"
    if f.external:
        return "stochastic", None
    if f.rng:
        if not f.traceable_seed:
            return "unclassified", "rng_without_traceable_seed"
        return "seeded", None
    return "deterministic", None


# ─────────────────────────── feature extraction ───────────────────────────

def _dotted(node: ast.AST) -> str:
    """`a.b.c` from an attribute chain; '' when the shape is anything else."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def features_from_source(source: str) -> Features:
    """**AST only, never a substring scan.** The eighteenth milestone shipped a check that
    searched source text for a forbidden word and matched the module's own docstring
    explaining that it does not use that word."""
    tree = ast.parse(source)
    rng = seed = network = concurrency = clock = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                rng |= a.name in RNG_MODULES
                network |= a.name in NETWORK_MODULES
                concurrency |= a.name in CONCURRENCY_MODULES
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            rng |= mod in RNG_MODULES or any(a.name in PROOFROOT_RNG for a in node.names)
            seed |= any(a.name in PROOFROOT_RNG for a in node.names)
            network |= mod in NETWORK_MODULES
            concurrency |= mod in CONCURRENCY_MODULES
        elif isinstance(node, ast.Call):
            name = _dotted(node.func)
            clock |= name in CLOCK_CALLS
            # A seed is traceable when it is pinned to a literal in the frozen source, or
            # derived through proofroot's named streams — both are recorded inputs.
            if name.endswith(".seed") or name.endswith("default_rng"):
                rng = True
                seed |= any(isinstance(a, ast.Constant) for a in node.args)
            if name.split(".")[-1] in PROOFROOT_RNG:
                rng = seed = True
    return Features(rng=rng, traceable_seed=seed, network=network,
                    concurrency=concurrency, clock=clock)


def features_from_product(summary: dict) -> Features:
    """L1: what the artifact alone carries. **This is the level the counterparty says is
    empty**, and the measurement says they are largely right — most bundles record nothing
    about randomness at all."""
    blob = json.dumps(summary).lower()
    rng = any(k in blob for k in ('"seed"', "seed_", "_seed", '"rng"', "rng_", "_rng"))
    return Features(rng=rng, traceable_seed=rng)   # a recorded seed IS a traceable one


def merge(a: Features, b: Features) -> Features:
    return Features(rng=a.rng or b.rng, traceable_seed=a.traceable_seed or b.traceable_seed,
                    network=a.network or b.network, concurrency=a.concurrency or b.concurrency,
                    clock=a.clock or b.clock, runner_found=a.runner_found and b.runner_found)


# ─────────────────────────── negative control ───────────────────────────

FIXTURES: tuple[tuple[str, Features, str, str | None], ...] = (
    ("plain arithmetic", Features(), "deterministic", None),
    ("reads a config file", Features(rng=False), "deterministic", None),
    ("random with a literal seed", Features(rng=True, traceable_seed=True), "seeded", None),
    ("proofroot named stream", Features(rng=True, traceable_seed=True), "seeded", None),
    ("calls a remote service", Features(network=True), "stochastic", None),
    ("thread pool", Features(concurrency=True), "stochastic", None),
    ("rng with no seed anywhere", Features(rng=True, traceable_seed=False),
     "unclassified", "rng_without_traceable_seed"),
    ("seeded AND networked", Features(rng=True, traceable_seed=True, network=True),
     "unclassified", "mixed_seeded_and_stochastic"),
)
"""Eight synthetic samples: two per class, **including two `unclassified` negatives**.
A classifier that only ever returns a class is as useless as a gate that only goes green."""


def _selftest() -> int:
    ok = True
    for name, feats, want_cls, want_reason in FIXTURES:
        got_cls, got_reason = classify(feats)
        good = (got_cls, got_reason) == (want_cls, want_reason)
        ok &= good
        print(f"  [{'ok ' if good else 'FAIL'}] {name:28s} -> {got_cls}"
              f"{'/' + got_reason if got_reason else ''}")

    # **The parser must be tested too, not only the predicate.** A `--selftest` that
    # exercises only `classify()` cannot catch an extractor that recognises nothing —
    # that exact hole shipped once in `unit_alignment` and reported every unit missing.
    probes = (
        ("import random\nrandom.seed(7)\n", True, True, False),
        ("import random\nx = random.random()\n", True, False, False),
        ("import urllib.request\n", False, False, True),
        ("import threading\n", False, False, True),
        ("x = 1 + 1\n", False, False, False),
    )
    for src, want_rng, want_seed, want_ext in probes:
        f = features_from_source(src)
        good = (f.rng, f.traceable_seed, f.external) == (want_rng, want_seed, want_ext)
        ok &= good
        print(f"  [{'ok ' if good else 'FAIL'}] parse {src.splitlines()[0]:26s} -> "
              f"rng={f.rng} seed={f.traceable_seed} ext={f.external}")

    print(f"  [{'green' if ok else 'RED'}] selftest: every class reachable, "
          f"both unclassified reasons reachable, extractor recognises what it must")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bundle", nargs="?", type=pathlib.Path)
    ap.add_argument("--runner", type=pathlib.Path, help="the verdict runner that produced it")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.bundle is None:
        ap.error("pass a bundle directory, or --selftest")

    summary = args.bundle / "summary.json"
    if not summary.exists():
        print(f"{summary} does not exist — not a verdict bundle.")
        return 1
    l1 = features_from_product(json.loads(summary.read_text(encoding="utf-8")))
    if args.runner and args.runner.exists():
        l2 = merge(l1, features_from_source(args.runner.read_text(encoding="utf-8")))
    else:
        l2 = dataclasses.replace(l1, runner_found=False)
    for level, f in (("L1", l1), ("L2", l2)):
        cls, reason = classify(f)
        print(f"{level}: {cls}{' (' + reason + ')' if reason else ''}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
