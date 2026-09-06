#!/usr/bin/env python3
"""The gate for **how the sample size was arrived at** — not for whether it was wise.

## What this refuses, and what it deliberately does not

A `stochastic` registration has to say how many repetitions it will run. The twenty-first
milestone shows what happens when that number comes from a rule of thumb: a convergence
test that stopped at 8 because wide intervals look like agreement, on data where the
statistic being compared was the wrong one to begin with. Nothing caught it, because
nothing was asking where the number came from.

So this gate asks for six things, and then checks **one** of them against the others:

| | | |
|---|---|---|
| `effect` | the difference worth detecting, in the quantity's own units | M1 |
| `location`, `spread` | which statistic is compared, and which estimates dispersion | M2 |
| `alpha`, `beta` | false alarm and miss rates you accept | M3 |
| `derivation` | how N follows from those — here, `bootstrap_power` | M4 |
| `budget` | the N past which you declare the question undecidable for now | M5 |
| `heavy_tail` | whether the data is heavy-tailed, and if so why `location` is still defensible | M6 |

**It does not judge the answers.** Whether 2.0 eV is the right effect to care about is a
scientific judgement, and checking it would need a referee who understands the question
better than the person asking it. No such referee exists.

**What it does judge is self-consistency**: re-run the power analysis from `effect`,
`location`, `alpha`, `beta` and the pilot samples, and the N that comes out must equal the
declared one. A number that does not follow from its own stated premises was picked, not
derived — and that is mechanically detectable without any opinion about the science.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ANCHOR = re.compile(r"<!--@judgement_design:\s*([^>]*?)-->")
REQUIRED = ("effect", "location", "spread", "alpha", "beta", "derivation", "budget",
            "heavy_tail", "n", "pilot")
LOCATIONS = ("mean", "median", "trimmed")


def parse(text: str) -> dict[str, str] | None:
    m = ANCHOR.search(text)
    if not m:
        return None
    out: dict[str, str] = {}
    for item in m.group(1).split(","):
        if "=" in item:
            k, _, v = item.partition("=")
            out[k.strip()] = v.strip()
    return out


def check_fields(f: dict[str, str] | None) -> list[str]:
    """Presence and shape only. **No opinion about the values.**"""
    if f is None:
        return ["no @judgement_design anchor — a stochastic registration must say where "
                "its repetition count came from. Six answers are required; see this "
                "module's docstring."]
    problems = [f"@judgement_design is missing {k}=" for k in REQUIRED if k not in f]
    if f.get("location") and f["location"] not in LOCATIONS:
        problems.append(f"location={f['location']!r} — must be one of {LOCATIONS}")
    if f.get("heavy_tail") == "yes" and f.get("location") == "mean" and not f.get("why_mean"):
        problems.append(
            "heavy_tail=yes with location=mean and no why_mean= — the regular bootstrap "
            "fails on the mean of heavy-tailed data. Comparing the mean anyway may still "
            "be defensible, but the reason has to be on the record, not implied.")
    for key in ("alpha", "beta", "effect"):
        if key in f:
            try:
                float(f[key])
            except ValueError:
                problems.append(f"{key}={f[key]!r} is not a number")
    return problems


def check_consistency(f: dict[str, str], folder: pathlib.Path) -> list[str]:
    """Re-derive N and compare. **This is the half that cannot be satisfied by typing.**"""
    from newlife.stochastic.design import required_n
    pilot_path = folder / f["pilot"]
    if not pilot_path.exists():
        return [f"pilot={f['pilot']} does not exist — without the samples the declared N "
                f"cannot be re-derived, and an unverifiable N is an asserted one"]
    data = json.loads(pilot_path.read_text(encoding="utf-8"))
    samples = data if isinstance(data, list) else data.get("samples")
    if not samples:
        return [f"{pilot_path} holds no `samples` list"]
    n_prime, curve = required_n(
        samples, float(f["effect"]), power=1.0 - float(f["beta"]), kind=f["location"],
        level=1.0 - float(f["alpha"]), resamples=int(f.get("resamples", 300)),
        trials=int(f.get("trials", 60)), seed=int(f.get("seed", 20260906)),
        budget=int(f["budget"]))
    declared = None if f["n"] in ("none", "undecidable") else int(f["n"])
    if n_prime != declared:
        return [f"declared n={f['n']} but re-deriving from effect={f['effect']}, "
                f"location={f['location']}, alpha={f['alpha']}, beta={f['beta']} gives "
                f"{n_prime}. Power curve: {curve}. **A number that does not follow from "
                f"its own premises was chosen, not derived.**"]
    return []


def _selftest() -> int:
    ok = True

    def case(name: str, text: str, want_red: bool) -> None:
        nonlocal ok
        red = bool(check_fields(parse(text)))
        good = red == want_red
        ok &= good
        print(f"  [{'RED' if red else 'green'}] {name}"
              f"{'' if good else '  <-- expected the opposite'}")

    full = ("<!--@judgement_design: effect=2.0, location=trimmed, spread=MAD, alpha=0.05, "
            "beta=0.2, derivation=bootstrap_power, budget=256, heavy_tail=yes, n=64, "
            "pilot=results/pilot.json-->")
    case("a complete declaration", full, False)
    case("no anchor at all", "# a registration with nothing said", True)
    for k in ("effect", "location", "alpha", "beta", "budget", "heavy_tail", "n", "pilot"):
        stripped = re.sub(rf"{k}=[^,>]*,?\s*", "", full)
        case(f"missing {k}", stripped, True)
    case("location is not one of the three",
         full.replace("location=trimmed", "location=geometric"), True)
    case("heavy tail + mean, no reason given",
         full.replace("location=trimmed", "location=mean"), True)
    case("heavy tail + mean, reason on the record",
         full.replace("location=trimmed", "location=mean, why_mean=bounded support"), False)
    case("effect is not a number", full.replace("effect=2.0", "effect=large"), True)

    print(f"  [{'green' if ok else 'RED'}] selftest: every omission red, "
          f"the complete declaration green")
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
    fields = parse(prereg.read_text(encoding="utf-8"))
    problems = check_fields(fields)
    if not problems and fields is not None:
        problems = check_consistency(fields, args.folder)
    for p in problems:
        print(f"[FAIL] prereg.md: {p}")
    if problems:
        print(f"\nThe repetition count is not accounted for: {len(problems)} item(s).")
        return 1
    print(f"Judgement design: six answers present, and n={fields['n']} re-derives from them.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
