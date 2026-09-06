"""One test, used in both directions — that is the whole idea.

## Why a single test, and why both directions

Deciding whether two sets of samples are "the same" needs a threshold, and a threshold can
be tuned:

- loosen it and **everything** looks equivalent — swap the model and nothing notices; the
  machinery runs and is blind
- tighten it and **nothing** does — the same model measured twice comes back "different";
  the machinery reports noise

Test one direction only and either failure is trivially avoidable: to pass stability,
loosen; to pass sensitivity, tighten. **So the same test and the same threshold answer
both questions**, and the registration forbids using two:

| | compared | must return |
|---|---|---|
| stability | two batches of the same model | equivalent |
| sensitivity | model A vs model B | **not** equivalent |

Whether one threshold can satisfy both at once is the question the milestone exists to ask.

## Why bootstrap rather than a t-test

The shape of an LLM's output distribution is unknown, and there is no reason to assume
normality. The percentile bootstrap assumes nothing about shape. It draws from a seeded
RNG, so **the judgement layer is `seeded`, not `stochastic`** (the twentieth milestone's
vocabulary): given the same samples, it reproduces byte for byte.

## Why "how many runs" is not a number in this file

Picking N by hand is picking an answer. The convergence rule instead asks the data:
**split this batch in half at random and run the same test; equivalent means the sample
has settled.** No units, no epsilon to choose for a quantity whose scale nobody knows,
and it is the same yardstick the criteria use.
"""

from __future__ import annotations

import argparse
import random
import sys

Samples = dict[str, list[float]]
"""Sweep point -> the values observed there. Keys are strings so the artifact is JSON."""


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def median(xs: list[float]) -> float:
    ys = sorted(xs)
    m = len(ys) // 2
    return ys[m] if len(ys) % 2 else (ys[m - 1] + ys[m]) / 2.0


def trimmed_mean(xs: list[float], frac: float = 0.2) -> float:
    """Drop `frac` from each tail, then average. 0.2 is the conventional choice."""
    ys = sorted(xs)
    k = int(len(ys) * frac)
    kept = ys[k:len(ys) - k] or ys      # never trim everything away
    return sum(kept) / len(kept)


LOCATION = {"mean": mean, "median": median, "trimmed": trimmed_mean}
"""**Which statistic is compared is a decision, not a default.**

The regular bootstrap fails to estimate the distribution of a sample *mean* under heavy
tails — rare values surface in resampling in the wrong proportions — while M-estimators
and other robust locations keep their power there. So the shape of the data decides what
to compare **before** it decides how many samples to take.

The twenty-first milestone compared means on a batch containing -400. Its diagnosis at the
time was "the sample size stopped at 8". That was half of it; **the other half is that the
mean should not have been the thing compared.**
"""


def bootstrap_diff_ci(a: list[float], b: list[float], *, level: float,
                      resamples: int, seed: int,
                      kind: str = "mean") -> tuple[float, float]:
    """Percentile CI for `mean(a) - mean(b)`, resampling both groups.

    **Both groups are resampled**, not just one: the question is whether the *difference*
    could be zero, and holding one group fixed understates its own sampling error.
    """
    if not a or not b:
        raise ValueError("bootstrap needs both groups non-empty — an empty group would "
                         "make the interval degenerate and quietly report 'equivalent'")
    loc = LOCATION[kind]
    rng = random.Random(seed)
    na, nb = len(a), len(b)
    diffs = [loc([a[rng.randrange(na)] for _ in range(na)])
             - loc([b[rng.randrange(nb)] for _ in range(nb)])
             for _ in range(resamples)]
    diffs.sort()
    tail = (1.0 - level) / 2.0
    lo = diffs[int(tail * resamples)]
    hi = diffs[min(int((1.0 - tail) * resamples), resamples - 1)]
    return lo, hi


def equivalent(a: Samples, b: Samples, *, level: float, resamples: int,
               seed: int, kind: str = "mean") -> tuple[bool, dict]:
    """Equivalent iff **every** sweep point's interval contains 0.

    Returns the per-point intervals too: a bare boolean cannot be audited, and the whole
    point of this round is that the numbers behind the verdict stay visible.
    """
    points = sorted(set(a) | set(b))
    if not points:
        raise ValueError("no sweep points — an empty comparison is vacuously equivalent, "
                         "which is exactly the shape a vacuous criterion takes")
    if set(a) != set(b):
        raise ValueError(f"sweep points differ: {sorted(a)} vs {sorted(b)}")
    # **Bonferroni**: "every point contains zero" is a conjunction, so the per-point level
    # must be raised or the test is stricter than it claims. Two points at 95% give
    # 0.95^2 ~ 90% — a one-in-ten chance of calling two samples of the *same* model
    # different. The selftest caught exactly that on its first run.
    per_point = 1.0 - (1.0 - level) / len(points)
    detail = {}
    for i, p in enumerate(points):
        lo, hi = bootstrap_diff_ci(a[p], b[p], level=per_point, resamples=resamples,
                                   seed=seed + i, kind=kind)   # one stream per point
        detail[p] = {"lo": lo, "hi": hi, "contains_zero": lo <= 0.0 <= hi,
                     "level": per_point}
    return all(d["contains_zero"] for d in detail.values()), detail


def converged(s: Samples, *, level: float, resamples: int, seed: int) -> tuple[bool, dict]:
    """Split each point's samples in half at random; converged iff the halves are equivalent.

    **The convergence rule is the criterion's own yardstick**, not a proxy: if the two
    halves of what you already have cannot be told apart, more of the same will not move
    the verdict.
    """
    rng = random.Random(seed)
    first: Samples = {}
    second: Samples = {}
    for p, xs in s.items():
        if len(xs) < 4:
            return False, {"reason": f"point {p} has {len(xs)} samples; a half of fewer "
                                     f"than two cannot support an interval"}
        shuffled = list(xs)
        rng.shuffle(shuffled)
        half = len(shuffled) // 2
        first[p], second[p] = shuffled[:half], shuffled[half:]
    ok, detail = equivalent(first, second, level=level, resamples=resamples, seed=seed)
    return ok, detail


# ─────────────────────────── negative control ───────────────────────────

def _separated_fixtures() -> list[tuple[str, Samples, Samples, bool]]:
    """Pairs whose answer is **not** a coin flip: centres far enough apart that the test
    must say "different" every time. Same-distribution behaviour is checked separately
    and as a *rate* — see `_false_alarm_rate`."""
    rng = random.Random(11)
    def draw(centre: float, spread: float, n: int = 24) -> list[float]:
        return [rng.gauss(centre, spread) for _ in range(n)]
    return [
        ("centres far apart", {"p1": draw(0.0, 0.5), "p2": draw(1.0, 0.5)},
         {"p1": draw(9.0, 0.5), "p2": draw(9.0, 0.5)}, False),
        ("one point differs only", {"p1": draw(0.0, 0.5), "p2": draw(1.0, 0.5)},
         {"p1": draw(0.0, 0.5), "p2": draw(7.0, 0.5)}, False),
    ]


def _false_alarm_rate(trials: int = 20, resamples: int = 600) -> float:
    """How often the test calls two samples of the **same** distribution "different".

    **A single same-distribution fixture is the wrong shape of assertion.** The first
    version asserted that one such pair must come back equivalent; it failed, and it was
    right to — two points at 95% put the conjunction near 90%, so one run in ten says
    "different", and that fixture would have been a coin flip pretending to be a check.
    What is worth asserting is the *rate*.
    """
    hits = 0
    for t in range(trials):
        rng = random.Random(1000 + t)
        def draw(c: float) -> list[float]:
            return [rng.gauss(c, 0.5) for _ in range(24)]
        a = {"p1": draw(0.0), "p2": draw(1.0)}
        b = {"p1": draw(0.0), "p2": draw(1.0)}
        ok, _ = equivalent(a, b, level=LEVEL, resamples=resamples, seed=SEED + t)
        hits += ok
    return hits / trials


LEVEL, RESAMPLES, SEED = 0.95, 2000, 20260906
"""The values this project freezes. Kept here so the selftest exercises the real ones."""


def _selftest() -> int:
    ok = True
    for name, a, b, want in _separated_fixtures():
        got, _ = equivalent(a, b, level=LEVEL, resamples=RESAMPLES, seed=SEED)
        good = got == want
        ok &= good
        print(f"  [{'ok ' if good else 'FAIL'}] {name:26s} equivalent={got} (want {want})")

    # Same distribution: assert the **rate**, not one draw. Bonferroni should put this
    # near 0.95. At or below 0.8 the test cries wolf too often for C1 to mean anything;
    # a flat 1.0 over many trials would suggest it can no longer say "different" at all.
    rate = _false_alarm_rate()
    good_rate = rate >= 0.8
    ok &= good_rate
    print(f"  [{'ok ' if good_rate else 'FAIL'}] same-distribution agreement {rate:.2f} (want >= 0.80)")

    # Convergence must be reachable in both directions too.
    rng = random.Random(3)
    settled = {"p1": [rng.gauss(0, 0.3) for _ in range(32)],
               "p2": [rng.gauss(1, 0.3) for _ in range(32)]}
    c1, _ = converged(settled, level=LEVEL, resamples=RESAMPLES, seed=SEED)
    ok &= c1
    print(f"  [{'ok ' if c1 else 'FAIL'}] a settled sample converges     ({c1})")
    c2, why = converged({"p1": [1.0, 2.0]}, level=LEVEL, resamples=RESAMPLES, seed=SEED)
    ok &= not c2
    print(f"  [{'ok ' if not c2 else 'FAIL'}] too few samples does not     ({c2})")

    # Degenerate inputs must raise, never quietly return "equivalent".
    for bad, kind in (((None, {"p1": []}, {"p1": [1.0]}), "empty group"),
                      ((None, {}, {}), "no sweep points"),
                      ((None, {"p1": [1.0]}, {"p2": [1.0]}), "mismatched points")):
        _, x, y = bad
        try:
            equivalent(x, y, level=LEVEL, resamples=10, seed=SEED)
            print(f"  [FAIL] {kind} did not raise — vacuous 'equivalent' is reachable")
            ok = False
        except ValueError:
            print(f"  [ok ] {kind} raises")
    print(f"  [{'green' if ok else 'RED'}] selftest: both answers reachable, "
          f"degenerate inputs refused")
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
