#!/usr/bin/env python3
"""How many repetitions — answered by the data, not by a formula.

## Why not the closed form

`n = 2(z_{a/2} + z_b)^2 * sigma^2 / delta^2` assumes normality and equal variance, and it
describes a t-test. Neither holds here: the worlds this is written for are heavy-tailed,
and the test actually used at judgement time is a bootstrap interval over a chosen location
statistic. **Using that formula would derive a sample size for a test nobody runs, from an
assumption nobody checked.**

## What is done instead — five steps, each running the real test

1. Take the pilot sample as an **empirical distribution**. No shape is assumed, so heavy
   tails are carried rather than modelled away.
2. Build the "there is a difference" world by shifting that distribution by the target
   effect. Shifted, not scaled: the declared effect is a difference in location, which is
   the quantity the test compares.
3. For a candidate N, repeat: draw N from each, **run the same test used at judgement**,
   record whether it says "not equivalent".
4. The **detection rate** is how often it did. Take the smallest N whose rate reaches the
   required power.
5. If the budget ceiling is reached without getting there, say **"undecidable within this
   budget"**. That is a correct answer, not a failure — and it is the answer the twenty-
   first milestone needed and did not have.

Multiple comparisons need no separate correction: step 3 runs the real conjunction over
sweep points, so whatever the test does about them is already inside the number. What must
be declared is **how many points carry the difference** — this module assumes the hardest
case, exactly one, because "at least one point differs" needs only one to be caught.
"""

from __future__ import annotations

import argparse
import random
import sys

from newlife.stochastic.equivalence import LOCATION, bootstrap_diff_ci


def tail_ratio(xs: list[float]) -> float:
    """`sd / (1.4826 * MAD)` — about 1 for a normal sample, well above 1 under heavy tails.

    **Why this rather than kurtosis**: kurtosis is itself a fourth moment, so on exactly the
    data where the question matters it is estimated worst. This ratio compares a
    tail-sensitive scale against a tail-resistant one; the divergence between them *is* the
    tail. Reported so the declaration can be cross-checked — **a fact that can be measured
    should not rest on self-report**, even under a rule that never judges answers.
    """
    if len(xs) < 4:
        raise ValueError("tail ratio needs at least 4 values")
    med = sorted(xs)[len(xs) // 2]
    mad = sorted(abs(x - med) for x in xs)[len(xs) // 2]
    mean_x = sum(xs) / len(xs)
    sd = (sum((x - mean_x) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    if mad == 0.0:
        return float("inf") if sd > 0 else 1.0
    return sd / (1.4826 * mad)


HEAVY_TAIL_RATIO = 1.5
"""Above this, the sample is treated as heavy-tailed for cross-checking purposes.
Not a law of nature — a threshold, chosen so that a normal sample sits comfortably below
and the twenty-first milestone's batch (which contained a -400) sits far above."""


def detection_rate(pilot: list[float], effect: float, n: int, *, kind: str, level: float,
                   resamples: int, trials: int, seed: int) -> float:
    """How often N samples per group let the test see a shift of `effect`.

    **The test here is the one used at judgement** — same interval, same location
    statistic. A power analysis run against a different test measures a different thing.
    """
    if not pilot:
        raise ValueError("power analysis needs a pilot sample; an empty one would make "
                         "every N look sufficient")
    rng = random.Random(seed)
    seen = 0
    for t in range(trials):
        a = [pilot[rng.randrange(len(pilot))] for _ in range(n)]
        b = [pilot[rng.randrange(len(pilot))] + effect for _ in range(n)]
        lo, hi = bootstrap_diff_ci(a, b, level=level, resamples=resamples,
                                   seed=seed + t, kind=kind)
        seen += not (lo <= 0.0 <= hi)
    return seen / trials


def required_n(pilot: list[float], effect: float, *, power: float, kind: str, level: float,
               resamples: int, trials: int, seed: int, budget: int,
               start: int = 4) -> tuple[int | None, list[tuple[int, float]]]:
    """Smallest N reaching `power`, or **None** when the budget runs out first.

    Returns the curve as well: a single number hides whether the answer was comfortable or
    marginal, and the registration is supposed to let a reader see that.
    """
    curve: list[tuple[int, float]] = []
    n = start
    while n <= budget:
        rate = detection_rate(pilot, effect, n, kind=kind, level=level,
                              resamples=resamples, trials=trials, seed=seed)
        curve.append((n, rate))
        if rate >= power:
            return n, curve
        n *= 2
    return None, curve


# ─────────────────────────── negative control ───────────────────────────

def _heavy_tail(rng: random.Random, n: int = 40) -> list[float]:
    """A light core with occasional far-out values — the shape that broke the mean."""
    return [rng.gauss(0.0, 1.0) if rng.random() > 0.1 else rng.gauss(0.0, 40.0)
            for _ in range(n)]


def _selftest() -> int:
    ok = True
    LEVEL, RESAMPLES, TRIALS, SEED = 0.95, 300, 60, 20260906

    # **The load-bearing property.** If a robust location did not need fewer samples on
    # heavy-tailed data, then "choose the statistic to match the shape" would be advice
    # with nothing behind it, and M2 could be dropped from the method.
    rng = random.Random(4)
    pilot = _heavy_tail(rng)
    n_mean, _ = required_n(pilot, effect=2.0, power=0.8, kind="mean", level=LEVEL,
                           resamples=RESAMPLES, trials=TRIALS, seed=SEED, budget=256)
    n_trim, _ = required_n(pilot, effect=2.0, power=0.8, kind="trimmed", level=LEVEL,
                           resamples=RESAMPLES, trials=TRIALS, seed=SEED, budget=256)
    better = (n_trim is not None) and (n_mean is None or n_trim < n_mean)
    ok &= better
    print(f"  [{'ok ' if better else 'FAIL'}] heavy tail: trimmed needs {n_trim}, "
          f"mean needs {n_mean} — robust must win")

    # A larger effect must never need more samples than a smaller one.
    light = [rng.gauss(0.0, 1.0) for _ in range(40)]
    n_small, _ = required_n(light, 1.0, power=0.8, kind="mean", level=LEVEL,
                            resamples=RESAMPLES, trials=TRIALS, seed=SEED, budget=256)
    n_big, _ = required_n(light, 4.0, power=0.8, kind="mean", level=LEVEL,
                          resamples=RESAMPLES, trials=TRIALS, seed=SEED, budget=256)
    mono = n_big is not None and n_small is not None and n_big <= n_small
    ok &= mono
    print(f"  [{'ok ' if mono else 'FAIL'}] bigger effect is not harder: "
          f"delta=4 -> {n_big}, delta=1 -> {n_small}")

    # **Undecidable must be reachable**, or step 5 is decoration.
    n_none, curve = required_n(light, effect=0.01, power=0.99, kind="mean", level=LEVEL,
                               resamples=RESAMPLES, trials=TRIALS, seed=SEED, budget=32)
    unreach = n_none is None and len(curve) > 0
    ok &= unreach
    print(f"  [{'ok ' if unreach else 'FAIL'}] tiny effect within a small budget is "
          f"reported undecidable ({n_none}), curve has {len(curve)} points")

    # An empty pilot must raise, never make every N look sufficient.
    try:
        detection_rate([], 1.0, 8, kind="mean", level=LEVEL, resamples=10, trials=2,
                       seed=SEED)
        print("  [FAIL] empty pilot did not raise")
        ok = False
    except ValueError:
        print("  [ok ] empty pilot raises")

    print(f"  [{'green' if ok else 'RED'}] selftest: robust wins on heavy tails, "
          f"monotone in effect, undecidable reachable")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if not args.selftest:
        ap.error("this module is a library; run --selftest")
    return _selftest()


if __name__ == "__main__":
    sys.exit(main())
