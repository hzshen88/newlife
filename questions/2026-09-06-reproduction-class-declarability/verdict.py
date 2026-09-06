"""reproduction class declarability — verdict runner.

The criteria are frozen in `prereg.md` (see its §2). **The verdict is a mechanical
conjunction of the units and is never written by hand.**

**This runner does not run any other question's runner** (registration F4). There are
exactly two safety lines: self-reproduction and an unchanged environment. Questions are
siblings, not a chain — rerunning someone else's old conclusion adds nothing to the
credibility of this one, and with fifty questions it entangles all of them.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import os
import subprocess
import sys
from pathlib import Path

from newlife import provenance
from newlife.core.verdict_seam import RenderSpec, decide, emit, exit_code

HERE = Path(__file__).resolve().parent
INNER = "_NEWLIFE_INNER_RUN"        # marks the inner reproduction run; stops infinite recursion

# ─────────────────────────────────────────────────────────────────────
# YOUR WORLD. **Replace everything from here down to "criteria" with your own.**
# ─────────────────────────────────────────────────────────────────────
REPO = HERE.parent.parent          # questions/<slug>/ -> repo root
BUNDLES = REPO / "results"
CONFORM = REPO / "packages/newlife/src/newlife/conform"

# **Independently implemented, per registration constraint 7.** This file must not import
# `newlife.gates.reproduction_class`; the discipline is that the classification is written
# twice, by two code paths, both answering to the expectations frozen in prereg.md. A
# shared helper would make the two agree for the wrong reason.
NETWORK = {"urllib", "urllib.request", "requests", "httpx", "socket", "http.client", "aiohttp"}
CONCURRENT = {"threading", "multiprocessing", "concurrent.futures", "asyncio"}
CLOCKS = {"time.time", "time.monotonic", "time.perf_counter"}
RNGS = {"random", "numpy.random", "secrets"}
PROOFROOT = {"RngBank", "derive_stream_seed", "EVIDENCECORE_RNG_V1"}


class _Scan(ast.NodeVisitor):
    """A visitor, where the gate uses `ast.walk` — two shapes, so a mistake in one is
    unlikely to be the same mistake in the other."""

    def __init__(self) -> None:
        self.rng = self.seed = self.net = self.conc = self.clock = False

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.rng |= a.name in RNGS
            self.net |= a.name in NETWORK
            self.conc |= a.name in CONCURRENT
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        hit = {a.name for a in node.names} & PROOFROOT
        self.rng |= mod in RNGS or bool(hit)
        self.seed |= bool(hit)
        self.net |= mod in NETWORK
        self.conc |= mod in CONCURRENT
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _name_of(node.func)
        self.clock |= name in CLOCKS
        if name.endswith(".seed") or name.endswith("default_rng"):
            self.rng = True
            self.seed |= any(isinstance(a, ast.Constant) for a in node.args)
        if name.split(".")[-1] in PROOFROOT:
            self.rng = self.seed = True
        self.generic_visit(node)


def _name_of(node) -> str:
    bits = []
    while isinstance(node, ast.Attribute):
        bits.append(node.attr)
        node = node.value
    return ".".join(reversed(bits + [node.id])) if isinstance(node, ast.Name) else ""


def classify(rng: bool, seed: bool, external: bool, runner_found: bool = True):
    """The frozen feature table of prereg.md section 3, written out a second time."""
    if not runner_found:
        return "unclassified", "no_runner_found"
    if rng and external:
        return "unclassified", "mixed_seeded_and_stochastic"
    if external:
        return "stochastic", None
    if rng:
        return ("seeded", None) if seed else ("unclassified", "rng_without_traceable_seed")
    return "deterministic", None


# The eight synthetic samples, with the categories prereg.md section 2 (S2) fixes in advance.
# (name, rng, seed, external, runner_found, expected class, expected reason)
SYNTHETIC = (
    ("plain arithmetic",          False, False, False, True, "deterministic", None),
    ("config file only",          False, False, False, True, "deterministic", None),
    ("random with literal seed",  True,  True,  False, True, "seeded", None),
    ("proofroot named stream",    True,  True,  False, True, "seeded", None),
    ("remote service call",       False, False, True,  True, "stochastic", None),
    ("thread pool",               False, False, True,  True, "stochastic", None),
    ("rng, no seed anywhere",     True,  False, False, True, "unclassified", "rng_without_traceable_seed"),
    ("seeded AND networked",      True,  True,  True,  True, "unclassified", "mixed_seeded_and_stochastic"),
)


def scan_source(text: str):
    v = _Scan()
    v.visit(ast.parse(text))
    return v.rng, v.seed, (v.net or v.conc or v.clock)


def product_features(summary: dict):
    blob = json.dumps(summary).lower()
    rng = any(k in blob for k in ('"seed"', "seed_", "_seed", '"rng"', "rng_", "_rng"))
    return rng, rng, False


def runner_for(bundle_name: str):
    """Best-effort match from a bundle directory name to the runner that produced it.
    **No match is a fact, not an error** — it becomes `no_runner_found`."""
    stem = bundle_name.replace("-", "_")
    for cand in (f"{stem}_verdict.py", f"{stem}.py", f"{stem.split('_')[0]}_verdict.py"):
        p = CONFORM / cand
        if p.exists():
            return p
    return None


def classify_bundles():
    """L1 and L2 over every bundle under `results/`. **Enumerated, never hand-picked**
    (constraint 4)."""
    rows = {}
    for d in sorted(x for x in BUNDLES.iterdir() if x.is_dir()):
        summary = d / "summary.json"
        if not summary.exists():
            continue
        p_rng, p_seed, _ = product_features(json.loads(summary.read_text(encoding="utf-8")))
        l1, l1_why = classify(p_rng, p_seed, False)
        runner = runner_for(d.name)
        if runner is None:
            l2, l2_why = classify(False, False, False, runner_found=False)
        else:
            s_rng, s_seed, s_ext = scan_source(runner.read_text(encoding="utf-8"))
            l2, l2_why = classify(p_rng or s_rng, p_seed or s_seed, s_ext)
        rows[d.name] = {"L1": l1, "L1_reason": l1_why, "L2": l2, "L2_reason": l2_why,
                        "runner": runner.name if runner else None}
    return rows


def safety_line_verdict_rot():
    """S4: did this round break any existing judgement? Runs the real thing."""
    proc = subprocess.run([sys.executable, "-m", "newlife.conform.verdict_rot"],
                          capture_output=True, text=True, cwd=str(REPO))
    out = proc.stdout
    m = re.search(r"复现 (\d+) · 坏 (\d+) · 跑不了 (\d+)", out)
    if not m:
        # **Parse failure is a hard failure, never a convenient default.** Falling back to
        # "nothing broke" is exactly the shape `silent_degradation_scan` exists to catch.
        raise SystemExit("could not parse verdict_rot output; refusing to assume it passed")
    return {"reproduced": int(m.group(1)), "broken": int(m.group(2)),
            "unrunnable": int(m.group(3))}


# ─────────────────────────────────────────────────────────────────────
# CRITERIA. **Write each one as a pure predicate** — that is what lets the runner
# prove, with synthetic inputs, that it can go red (registration F1).
# ─────────────────────────────────────────────────────────────────────
def criteria_can_fail() -> dict[str, bool]:
    """**F1: every criterion must be able to go red**, proved at runtime.

    Where this comes from: a negative control once written as `[f(x) for _ in SWEEP]` —
    the loop variable discarded, five identical runs compared against each other. True by
    construction, zero discriminating power, and it sat inside the conjunction for a whole
    milestone. **People only investigate what is red.**
    """
    return {
        "classify is false on a wrong label": classify(True, True, False)[0] != "stochastic",
        "mixed really lands unclassified": classify(True, True, True)[0] == "unclassified",
        "unseeded rng really lands unclassified":
            classify(True, False, False)[1] == "rng_without_traceable_seed",
        "scanner is false on inert source": scan_source("x = 1 + 1\n") == (False, False, False),
        "scanner really sees a network import":
            scan_source("import socket\n")[2] is True,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    synthetic = {name: classify(r, sd, e, rf) == (want, why)
                 for name, r, sd, e, rf, want, why in SYNTHETIC}
    rot = safety_line_verdict_rot()
    # **S5 is computed only outside a pilot.** It is the one blind unit of this round, and
    # `newlife pilot` exists to look at things before the freeze — looking at this one would
    # burn the one unit that carries information. The condition is one-way: it can make a
    # pilot compute *less*, never a real run compute less, so it cannot be used to switch a
    # criterion off at judgement time.
    bundles = None if os.environ.get("NEWLIFE_PILOT") else classify_bundles()

    can_fail = criteria_can_fail()
    # S1: the packages installed *now* are exactly the ones `env.lock` recorded at the
    # freeze. **The first version of this line compared the file's digest with a digest of
    # the same file taken a moment earlier — true by construction, and it shipped in every
    # early question.** `newlife freeze` rewrites env.lock from the live environment and
    # pins its hash into the registration; `newlife audit` proves the file never changed
    # afterwards; this line proves the run happened in that environment.
    s1 = provenance.env_text() == (HERE / "env.lock").read_text(encoding="utf-8")
    s2 = all(synthetic.values())
    s4 = rot["reproduced"] >= 7 and rot["broken"] == 0
    # **"the criteria can fail" is its own visible slot in the conjunction, not a
    # detail nested inside another unit.** The first version folded it into a sub-field
    # of S2, so the registration read S0∧S1∧S2∧S3 while the code computed three —
    # the unit-alignment gate in `newlife check` caught exactly this the first time it
    # ran against a real question folder.
    units = {"S1_env_unchanged": {"passed": s1},
             "S2_classifier_correct_on_synthetic": {"passed": s2, "per_sample": synthetic},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail},
             "S4_existing_judgements_intact": {"passed": s4, **rot}}
    if bundles is not None:
        unclassified = sorted(k for k, v in bundles.items() if v["L2"] == "unclassified")
        units["S5_l2_covers_every_bundle"] = {"passed": not unclassified,
                                              "unclassified": unclassified,
                                              "per_bundle": bundles}

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-06-reproduction-class-declarability.v1", "provenance": prov,
               "units": units}
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
