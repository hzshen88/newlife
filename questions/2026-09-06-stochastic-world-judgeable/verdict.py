"""stochastic world judgeable — verdict runner.

The criteria are frozen in `prereg.md` (see its §2). **The verdict is a mechanical
conjunction of the units and is never written by hand.**

**This runner does not run any other question's runner** (registration F4). There are
exactly two safety lines: self-reproduction and an unchanged environment. Questions are
siblings, not a chain — rerunning someone else's old conclusion adds nothing to the
credibility of this one, and with fifty questions it entangles all of them.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import urllib.request
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
# ── frozen constants (registration section 3) ────────────────────────────
POINTS = ("-1.0", "-4.0")          # adsorption energies, eV
MODEL_A, MODEL_B = "qwen3.5:4b", "qwen3.5:9b"
TEMPERATURE, N_START, N_MAX = 0.7, 8, 32
LEVEL, RESAMPLES, SEED = 0.95, 2000, 20260906
OLLAMA = os.environ.get("OLLAMA_HOST", "http://run:11434") + "/api/generate"
SAMPLES = HERE / "results" / "samples.json"

# **Independently implemented per registration constraint 6.** This file must not import
# `newlife.stochastic.equivalence`. Both implementations answer to the frozen numbers
# above and to the expectations in prereg.md; a shared helper would make them agree for
# the wrong reason.


def _percentile(sorted_xs: list[float], q: float) -> float:
    """Nearest-rank percentile. Written as an index computation rather than the other
    implementation's slice-and-clamp, so the same slip is unlikely to occur twice."""
    if not sorted_xs:
        raise ValueError("percentile of an empty sample")
    k = int(q * (len(sorted_xs) - 1) + 0.5)
    return sorted_xs[max(0, min(k, len(sorted_xs) - 1))]


def ci_of_difference(a: list[float], b: list[float], level: float, seed: int,
                     resamples: int = RESAMPLES):
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        sa = 0.0
        for _ in range(len(a)):
            sa += a[rng.randrange(len(a))]
        sb = 0.0
        for _ in range(len(b)):
            sb += b[rng.randrange(len(b))]
        diffs.append(sa / len(a) - sb / len(b))
    diffs.sort()
    tail = (1.0 - level) / 2.0
    return _percentile(diffs, tail), _percentile(diffs, 1.0 - tail)


def equivalent(a: dict, b: dict) -> tuple[bool, dict]:
    """Equivalent iff every point's interval contains zero. Bonferroni over the points:
    the conjunction is stricter than its parts, and two points at 95% land near 90%."""
    keys = sorted(a)
    if keys != sorted(b) or not keys:
        raise ValueError(f"sweep points differ or are empty: {sorted(a)} vs {sorted(b)}")
    per_point = 1.0 - (1.0 - LEVEL) / len(keys)
    out = {}
    for i, k in enumerate(keys):
        lo, hi = ci_of_difference(a[k], b[k], per_point, SEED + i)
        out[k] = {"lo": lo, "hi": hi, "contains_zero": lo <= 0.0 <= hi, "level": per_point}
    return all(v["contains_zero"] for v in out.values()), out


def converged(batch: dict) -> tuple[bool, dict]:
    """Split each point in half at random; converged iff the halves look equivalent."""
    rng = random.Random(SEED)
    lo_half, hi_half = {}, {}
    for k, xs in batch.items():
        if len(xs) < 4:
            return False, {"reason": f"point {k}: {len(xs)} samples is too few to split"}
        shuffled = list(xs)
        rng.shuffle(shuffled)
        cut = len(shuffled) // 2
        lo_half[k], hi_half[k] = shuffled[:cut], shuffled[cut:]
    return equivalent(lo_half, hi_half)


# ── sampling layer: the only place the world's randomness lives ──────────
def ask_once(model: str, point: str) -> float:
    """One call. **Any failure is a hard failure** (registration constraint 4): a partial
    sample silently becomes a narrower interval, and an empty response hashes to a
    constant that impersonates agreement — that one was hit for real on 2026-09-06."""
    prompt = (f"A catalyst surface has adsorption energy {point} eV. Reply with ONLY a "
              f"single number: the base-10 logarithm of the turnover frequency in s^-1. "
              f"No words, no units.")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": TEMPERATURE}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=300) as r:
        text = json.load(r)["response"]
    if not text.strip():
        raise SystemExit(f"{model} returned an empty response — refusing to continue with "
                         f"a partial sample")
    for token in re.findall(r"-?\d+\.?\d*", text):
        return float(token)
    raise SystemExit(f"no number in {model}'s reply: {text[:120]!r}")


def sample_to(store: dict, model: str, batch: str, n: int) -> dict:
    """Grow `batch` to n samples per point. Incremental so doubling N does not re-pay."""
    got = store.setdefault(batch, {p: [] for p in POINTS})
    for p in POINTS:
        while len(got[p]) < n:
            got[p].append(ask_once(model, p))
            print(f"    {batch}/{p}: {len(got[p])}/{n}", flush=True)
    return got


def collect() -> dict:
    """Sample every batch, doubling N until each converges or N_MAX is reached.

    Returns the store; **whether convergence was reached is recorded, not enforced here** —
    S6 reads it. A sampler that stopped early and said nothing would be the silent
    degradation this project keeps paying for.
    """
    if SAMPLES.exists():
        return json.loads(SAMPLES.read_text(encoding="utf-8"))
    store: dict = {}
    plan = (("A1", MODEL_A), ("A2", MODEL_A), ("B1", MODEL_B))
    n = N_START
    while True:
        for batch, model in plan:
            sample_to(store, model, batch, n)
        if all(converged(store[b])[0] for b, _ in plan):
            store["_n"] = n
            store["_converged"] = True
            break
        if n * 2 > N_MAX:
            store["_n"] = n
            store["_converged"] = False
            break
        n *= 2
    SAMPLES.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")
    return store


# ── synthetic samples for S2 (expectations frozen in prereg.md section 2) ─
def synthetic_cases() -> dict[str, bool]:
    """S2. **Separated pairs are asserted directly; same-distribution behaviour is a rate.**

    The first version asserted that one same-distribution pair must come back equivalent.
    The pilot judged it false, correctly: with two points the conjunction sits near 90%
    even after Bonferroni, so that assertion was a coin flip wearing the costume of a
    check. It had already been fixed in `newlife.stochastic.equivalence` — and was written
    again here, in the deliberately independent implementation. **Writing it twice guards
    against a slip, not against a wrong idea**: both copies come from one head.
    """
    rng = random.Random(11)
    d = lambda c: [rng.gauss(c, 0.5) for _ in range(24)]
    far = equivalent({"p1": d(0.0), "p2": d(1.0)}, {"p1": d(9.0), "p2": d(9.0)})[0]
    one = equivalent({"p1": d(0.0), "p2": d(1.0)}, {"p1": d(0.0), "p2": d(7.0)})[0]

    agree = 0
    trials, s2_resamples = 20, 800
    for t in range(trials):
        r = random.Random(1000 + t)
        e = lambda c: [r.gauss(c, 0.5) for _ in range(24)]
        a, b = {"p1": e(0.0), "p2": e(1.0)}, {"p1": e(0.0), "p2": e(1.0)}
        keys = sorted(a)
        per_point = 1.0 - (1.0 - LEVEL) / len(keys)
        ok = True
        for i, k in enumerate(keys):
            lo, hi = ci_of_difference(a[k], b[k], per_point, SEED + i, s2_resamples)
            ok &= lo <= 0.0 <= hi
        agree += ok
    rate = agree / trials
    return {
        "far apart -> not equivalent": far is False,
        "one point differs -> not equivalent": one is False,
        f"same-distribution agreement {rate:.2f} >= 0.80": rate >= 0.80,
    }


# ─────────────────────────────────────────────────────────────────────
# CRITERIA. **Write each one as a pure predicate** — that is what lets the runner
# prove, with synthetic inputs, that it can go red (registration F1).
# ─────────────────────────────────────────────────────────────────────
def criteria_can_fail() -> dict[str, bool]:
    """**F1: every criterion must be able to go red**, proved at runtime, not in prose."""
    rng = random.Random(5)
    d = lambda c: [rng.gauss(c, 0.5) for _ in range(20)]
    return {
        "equivalent() is false on far-apart centres":
            equivalent({"p": d(0.0)}, {"p": d(8.0)})[0] is False,
        "equivalent() is true on one shared distribution":
            equivalent({"p": d(0.0)}, {"p": d(0.0)})[0] is True,
        "converged() is false on too few samples":
            converged({"p": [1.0, 2.0]})[0] is False,
        "ci_of_difference brackets a known offset":
            ci_of_difference(d(5.0), d(0.0), 0.95, SEED)[0] > 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    synthetic = synthetic_cases()
    # **S4/S5/S6 are the blind units**: `newlife pilot` must not sample the world.
    # One-way condition — only `newlife pilot` sets it, a real run never does.
    store = None if os.environ.get("NEWLIFE_PILOT") else collect()

    can_fail = criteria_can_fail()
    # S1: the packages installed *now* are exactly the ones `env.lock` recorded at the
    # freeze. **The first version of this line compared the file's digest with a digest of
    # the same file taken a moment earlier — true by construction, and it shipped in every
    # early question.** `newlife freeze` rewrites env.lock from the live environment and
    # pins its hash into the registration; `newlife audit` proves the file never changed
    # afterwards; this line proves the run happened in that environment.
    s1 = provenance.env_text() == (HERE / "env.lock").read_text(encoding="utf-8")
    s2 = all(synthetic.values())
    # **"the criteria can fail" is its own visible slot in the conjunction, not a
    # detail nested inside another unit.** The first version folded it into a sub-field
    # of S2, so the registration read S0∧S1∧S2∧S3 while the code computed three —
    # the unit-alignment gate in `newlife check` caught exactly this the first time it
    # ran against a real question folder.
    units = {"S1_env_unchanged": {"passed": s1},
             "S2_test_correct_on_synthetic": {"passed": s2, "per_case": synthetic},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail}}
    if store is not None:
        stable, stable_detail = equivalent(store["A1"], store["A2"])
        sensitive, sensitive_detail = equivalent(store["A1"], store["B1"])
        units["S4_same_model_equivalent"] = {"passed": stable, "detail": stable_detail}
        # **Same test, same threshold, opposite direction** — using a second test here
        # would let each end be satisfied separately, which is the question being dodged.
        units["S5_across_models_not_equivalent"] = {"passed": not sensitive,
                                                    "detail": sensitive_detail}
        units["S6_converged_within_budget"] = {"passed": bool(store.get("_converged")),
                                               "n_per_point": store.get("_n"),
                                               "n_max": N_MAX}

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-06-stochastic-world-judgeable.v1", "provenance": prov,
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
