"""judgement design method — verdict runner.

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
import shutil
import tempfile
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
REPO = HERE.parent.parent
SAMPLES = HERE / "results" / "samples.json"
DESIGN = HERE / "judgement-design.json"

# ── frozen world definitions (registration section 3) ────────────────────
A_POINTS = ("-1.0", "-4.0")
A_MODELS = ("qwen3.5:4b", "qwen3.5:9b")
A_TEMPERATURE, A_MAX_N, A_PILOT_N = 0.7, 64, 12
B_THETAS = (1.0, 2.0)
B_NSAM, B_MAX_N, B_PILOT_N = 8, 2000, 40
OLLAMA = os.environ.get("OLLAMA_HOST", "http://run:11434") + "/api/generate"
LEVEL, SEED = 0.95, 20260906

# **Independently implemented per registration constraint 5**: this file must not import
# `newlife.stochastic.design` or `.equivalence`. What it may not differ in is the *search
# strategy* — doubling from a fixed start. Two implementations that搜索 differently would
# not be two readings of one spec, they would be two specs.


def _loc(xs, kind):
    """Location statistic. Written as an explicit dispatch, where the library uses a table."""
    ys = sorted(xs)
    if kind == "median":
        m = len(ys) // 2
        return ys[m] if len(ys) % 2 else (ys[m - 1] + ys[m]) / 2.0
    if kind == "trimmed":
        k = int(len(ys) * 0.2)
        kept = ys[k:len(ys) - k] or ys
        return sum(kept) / len(kept)
    return sum(ys) / len(ys)


def ci_diff(a, b, kind, level, seed, resamples):
    rng = random.Random(seed)
    out = []
    for _ in range(resamples):
        ra = [a[rng.randrange(len(a))] for _ in range(len(a))]
        rb = [b[rng.randrange(len(b))] for _ in range(len(b))]
        out.append(_loc(ra, kind) - _loc(rb, kind))
    out.sort()
    t = (1.0 - level) / 2.0
    lo_i = int(t * (len(out) - 1) + 0.5)
    hi_i = int((1.0 - t) * (len(out) - 1) + 0.5)
    return out[lo_i], out[min(hi_i, len(out) - 1)]


def equivalent(a, b, kind, resamples):
    keys = sorted(a)
    assert keys == sorted(b) and keys, "sweep points must match and be non-empty"
    per = 1.0 - (1.0 - LEVEL) / len(keys)      # Bonferroni over the conjunction
    detail = {}
    for i, k in enumerate(keys):
        lo, hi = ci_diff(a[k], b[k], kind, per, SEED + i, resamples)
        detail[k] = {"lo": lo, "hi": hi, "contains_zero": lo <= 0.0 <= hi}
    return all(v["contains_zero"] for v in detail.values()), detail


def detect_rate(pilot, effect, n, kind, level, resamples, trials, seed):
    rng = random.Random(seed)
    hits = 0
    for t in range(trials):
        a = [pilot[rng.randrange(len(pilot))] for _ in range(n)]
        b = [pilot[rng.randrange(len(pilot))] + effect for _ in range(n)]
        lo, hi = ci_diff(a, b, kind, level, seed + t, resamples)
        hits += not (lo <= 0.0 <= hi)
    return hits / trials


def derive_n(pilot, effect, power, kind, level, resamples, trials, seed, budget, start=4):
    """Doubling search — **the same strategy the library uses**, because the strategy is
    part of the spec, not of either implementation."""
    n, curve = start, []
    while n <= budget:
        r = detect_rate(pilot, effect, n, kind, level, resamples, trials, seed)
        curve.append([n, r])
        if r >= power:
            return n, curve
        n *= 2
    return None, curve


def tail_ratio(xs):
    med = sorted(xs)[len(xs) // 2]
    mad = sorted(abs(x - med) for x in xs)[len(xs) // 2]
    mu = sum(xs) / len(xs)
    sd = (sum((x - mu) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    return float("inf") if mad == 0 and sd > 0 else (1.0 if mad == 0 else sd / (1.4826 * mad))


# ── sampling: the only place the worlds' randomness lives ────────────────
def ask_llm(model, point):
    prompt = (f"A catalyst surface has adsorption energy {point} eV. Reply with ONLY a "
              f"single number: the base-10 logarithm of the turnover frequency in s^-1. "
              f"No words, no units.")
    body = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": A_TEMPERATURE}}).encode()
    req = urllib.request.Request(OLLAMA, data=body,
                                 headers={"Content-Type": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=300) as r:
        text = json.load(r)["response"]
    if not text.strip():
        raise SystemExit(f"{model} returned empty — refusing to continue on a partial sample")
    for tok in re.findall(r"-?\d+\.?\d*", text):
        return float(tok)
    raise SystemExit(f"no number in {model}'s reply: {text[:100]!r}")


def sample_a(store, model, batch, n):
    got = store.setdefault(batch, {p: [] for p in A_POINTS})
    for p in A_POINTS:
        while len(got[p]) < n:
            got[p].append(ask_llm(model, p))
            print(f"    A/{batch}/{p}: {len(got[p])}/{n}", flush=True)
    return got


def sample_b(store, theta, batch, n):
    """World B: the project's own coalescent. Its R3 boundary (u<=30) is a hard failure,
    not a clamp — going outside it is an invalidation condition, not a silent adjustment."""
    from newlife.mechanisms.second_world.world import CoalescentWorld, DevDrawStream
    got = store.setdefault(batch, {"segsites": []})
    while len(got["segsites"]) < n:
        i = len(got["segsites"])
        w = CoalescentWorld(nsam=B_NSAM, theta=theta,
                            draws=DevDrawStream(seed=SEED + hash(batch) % 1000 + i))
        got["segsites"].append(float(w.run().segsites))
    return got


# ─────────────────────────────────────────────────────────────────────
# CRITERIA. **Write each one as a pure predicate** — that is what lets the runner
# prove, with synthetic inputs, that it can go red (registration F1).
# ─────────────────────────────────────────────────────────────────────
def synthetic_checks() -> dict[str, bool]:
    """S2: the deriver behaves on inputs whose right answer is known independently."""
    rng = random.Random(4)
    heavy = [rng.gauss(0, 1) if rng.random() > 0.1 else rng.gauss(0, 40) for _ in range(40)]
    light = [rng.gauss(0, 1) for _ in range(40)]
    kw = dict(level=LEVEL, resamples=300, trials=60, seed=SEED, budget=256)
    n_mean, _ = derive_n(heavy, 2.0, 0.8, "mean", **kw)
    n_trim, _ = derive_n(heavy, 2.0, 0.8, "trimmed", **kw)
    n_small, _ = derive_n(light, 1.0, 0.8, "mean", **kw)
    n_big, _ = derive_n(light, 4.0, 0.8, "mean", **kw)
    n_none, _ = derive_n(light, 0.01, 0.99, "mean", level=LEVEL, resamples=300,
                         trials=60, seed=SEED, budget=32)
    return {
        # Without this one, "match the statistic to the shape" is advice with nothing
        # behind it, and M2 could be dropped from the method entirely.
        "robust wins on heavy tails":
            n_trim is not None and (n_mean is None or n_trim < n_mean),
        "a bigger effect is not harder":
            n_big is not None and n_small is not None and n_big <= n_small,
        "undecidable is reachable": n_none is None,
    }


def gate_catches_inconsistency() -> dict:
    """S4: the gate must reject a declared N that does not follow from its own premises.

    **Run against a copy**, never against the frozen file: a criterion that mutates the
    artifact it judges would be reaching into its own evidence.
    """
    from newlife.gates.judgement_design import check
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "results").mkdir()
        shutil.copy(HERE / design["pilot"], work / design["pilot"])
        (work / "judgement-design.json").write_text(json.dumps(design), encoding="utf-8")
        clean = check(work)
        broken = json.loads(json.dumps(design))
        for q in broken["quantities"]:
            q["result"]["n"] = (q["result"]["n"] or 0) + 7      # not a derivable value
        (work / "judgement-design.json").write_text(json.dumps(broken), encoding="utf-8")
        dirty = check(work)
    return {"passed": not clean and bool(dirty),
            "clean_problems": clean, "mutated_problems": dirty}


def judge_worlds() -> dict:
    """S5/S6/S7. **The sample size comes from the design file, never from this file.**

    That is the self-referential part of this milestone: if the method derived a bad N,
    these units fail, which is precisely what is being tested.
    """
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    by_name = {q["name"]: q for q in design["quantities"]}
    store = json.loads(SAMPLES.read_text(encoding="utf-8")) if SAMPLES.exists() else {}

    out = {}
    # ---- world A -------------------------------------------------------
    qa = by_name["log10_tof"]
    na = qa["result"]["n"]
    if na is None:
        out["S5"] = {"passed": False, "undecidable_within_budget": True,
                     "note": "the method reported no N within budget; that is its correct "
                             "output, and this unit records it as not established"}
    else:
        sample_a(store, A_MODELS[0], "A1", na)
        sample_a(store, A_MODELS[0], "A2", na)
        sample_a(store, A_MODELS[1], "B1", na)
        kind = qa["location"]["statistic"]
        stable, sd = equivalent(store["A1"], store["A2"], kind, 2000)
        sensitive, nd = equivalent(store["A1"], store["B1"], kind, 2000)
        out["S5"] = {"passed": stable and not sensitive, "n": na, "location": kind,
                     "stability": sd, "sensitivity": nd}

    # ---- world B -------------------------------------------------------
    qb = by_name["segsites"]
    nb = qb["result"]["n"]
    if nb is None:
        out["S6"] = {"passed": False, "undecidable_within_budget": True}
    else:
        sample_b(store, B_THETAS[0], "T1a", nb)
        sample_b(store, B_THETAS[0], "T1b", nb)
        sample_b(store, B_THETAS[1], "T2", nb)
        kind = qb["location"]["statistic"]
        stable, sd = equivalent(store["T1a"], store["T1b"], kind, 2000)
        sensitive, nd = equivalent(store["T1a"], store["T2"], kind, 2000)
        out["S6"] = {"passed": stable and not sensitive, "n": nb, "location": kind,
                     "stability": sd, "sensitivity": nd}

    SAMPLES.parent.mkdir(parents=True, exist_ok=True)
    SAMPLES.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")

    # ---- do the two designs actually differ ----------------------------
    differ = (qa["result"]["n"] != qb["result"]["n"]
              or qa["location"]["statistic"] != qb["location"]["statistic"])
    out["S7"] = {"passed": differ,
                 "world_a": {"n": qa["result"]["n"], "location": qa["location"]["statistic"]},
                 "world_b": {"n": qb["result"]["n"], "location": qb["location"]["statistic"]}}
    return out


def criteria_can_fail() -> dict[str, bool]:
    """**F1: every criterion must be able to go red**, proved at runtime."""
    rng = random.Random(5)
    d = lambda c: [rng.gauss(c, 0.5) for _ in range(20)]
    heavy = [rng.gauss(0, 1) if rng.random() > 0.1 else rng.gauss(0, 40) for _ in range(40)]
    return {
        "equivalent() false on far-apart centres":
            equivalent({"p": d(0.0)}, {"p": d(8.0)}, "mean", 200)[0] is False,
        "equivalent() true on one shared distribution":
            equivalent({"p": d(0.0)}, {"p": d(0.0)}, "mean", 200)[0] is True,
        "derive_n returns None when the budget is too small":
            derive_n(d(0.0), 0.01, 0.99, "mean", LEVEL, 200, 30, SEED, 16)[0] is None,
        "tail_ratio separates normal from heavy":
            tail_ratio(d(0.0)) < 1.5 < tail_ratio(heavy),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    synthetic = synthetic_checks()
    gate_catches = gate_catches_inconsistency()
    # S5/S6/S7 are the blind units — a pilot must not touch the real worlds.
    live = None if os.environ.get("NEWLIFE_PILOT") else judge_worlds()

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
             "S2_deriver_correct_on_synthetic": {"passed": s2, "per_case": synthetic},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail},
             "S4_gate_catches_inconsistency": {"passed": gate_catches["passed"],
                                               **gate_catches}}
    if live is not None:
        units["S5_world_a_has_power"] = live["S5"]
        units["S6_world_b_has_power"] = live["S6"]
        units["S7_designs_differ"] = live["S7"]

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-06-judgement-design-method.v1", "provenance": prov,
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
