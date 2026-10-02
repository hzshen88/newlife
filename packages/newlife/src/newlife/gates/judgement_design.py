"""The gate for **how the sample size was arrived at** — not for whether it was wise.

A `stochastic` registration has to say how many repetitions it will run. The twenty-first
milestone shows what happens when that number comes from a rule of thumb: a convergence
test stopped at 8, because on heavy-tailed data wide intervals look like agreement — and
the statistic being compared was the wrong one to begin with. Nothing caught it, because
nothing was asking where the number came from.

So the design lives in `judgement-design.json` (see `newlife.stochastic.schema` for the
shape and for why it is a file rather than an anchor), and this gate makes two passes:

1. **Shape** — are the seven answers there, one set per measured quantity, each with its
   reason written out.
2. **Consistency** — re-run the power analysis from `effect`, `location`, `alpha`, `beta`
   and the pilot samples. The N that comes out must equal the declared one. And (M7) take
   the estimator's readings on known truth, compute their location with the quantity's own
   statistic, and compare the distance to the truth with `effect`.

**The first pass never judges an answer.** Whether 2.0 is the right effect to care about
is a scientific judgement, and checking it needs a referee who understands the question
better than the person asking. There is no such referee. **The second pass needs no
opinion at all**: a number that does not follow from its own stated premises was chosen,
not derived, and that is mechanically detectable.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

DESIGN_FILE = "judgement-design.json"
CLASSES = ("deterministic", "seeded", "stochastic")
CLASS_ANCHOR = re.compile(r"<!--@reproduction_class:\s*([^>]*?)-->")


def declared_class(prereg_text: str) -> str | None:
    """The reproduction class prereg.md declares, or None.

    None covers an absent anchor and the template's untouched placeholder (it lists all
    three words with `|` between them). The freeze treats None as `deterministic` and says
    so; only `seeded` and `stochastic` oblige a `judgement-design.json` (rule seven).
    """
    m = CLASS_ANCHOR.search(prereg_text)
    if not m:
        return None
    body = m.group(1).strip().lower()
    first = body.split()[0].rstrip(",.;:") if body else ""
    if "|" in body or first not in CLASSES:
        return None
    return first


def load(folder: pathlib.Path) -> tuple[dict | None, list[str]]:
    path = folder / DESIGN_FILE
    if not path.exists():
        return None, [
            f"no {DESIGN_FILE} — a stochastic registration must say where its repetition "
            f"count came from. Seven answers per measured quantity; see "
            f"`newlife.stochastic.schema` for the shape."]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{DESIGN_FILE} is not valid JSON: {exc}"]


def tail_crosscheck(d: dict, pilot: dict) -> list[str]:
    """Measure the tail and compare it with what the design claims.

    **A fact that can be measured should not rest on self-report.** The rule that this gate
    never judges an *answer* still leaves room to check a *measurement*: declaring
    `heavy_tail.detected = false` is how one would slip past the requirement to justify
    comparing means, and the data itself can say otherwise.
    """
    from newlife.stochastic.design import HEAVY_TAIL_RATIO, tail_ratio
    out: list[str] = []
    for q in d["quantities"]:
        by_point = pilot.get(q["name"]) or {}
        ratios = {p: tail_ratio(v) for p, v in by_point.items() if len(v) >= 4}
        if not ratios:
            continue
        measured = max(ratios.values()) > HEAVY_TAIL_RATIO
        claimed = bool((q.get("heavy_tail") or {}).get("detected"))
        if measured != claimed:
            worst = max(ratios, key=lambda k: ratios[k])
            out.append(
                f"{q['name']}: heavy_tail.detected={claimed} but sd/(1.4826*MAD) at point "
                f"{worst} is {ratios[worst]:.2f} (threshold {HEAVY_TAIL_RATIO}) — measured "
                f"{'heavy' if measured else 'light'}. Either correct the declaration or "
                f"give heavy_tail.override_why saying why the ratio misleads here."
                if not str((q.get("heavy_tail") or {}).get("override_why", "")).strip()
                else "")
    return [x for x in out if x]


def calibration_problems(d: dict, pilot: dict) -> list[str]:
    """M7: is the estimator's bias on known truth smaller than the effect it must resolve?

    **The bias is computed here, never typed.** A design that wrote `bias: 0.01` next to its
    effect would be a log, not a measurement; the readings are the measurement. Their
    location is taken with the quantity's own M2 statistic, so effect and bias are measured
    with one ruler. Whether the truth is really independent of the estimator is not judged —
    `family` puts the claim on the record, and that is all a gate can do.
    """
    from newlife.stochastic.equivalence import LOCATION
    out: list[str] = []
    for q in d["quantities"]:
        cal = q.get("calibration") or {}
        if "not_applicable" in cal:
            continue
        name, key = q["name"], cal["samples"]
        readings = pilot.get(key)
        if (not isinstance(readings, list) or not readings
                or not all(isinstance(x, (int, float)) and not isinstance(x, bool)
                           for x in readings)):
            out.append(f"{name}: calibration.samples={key!r} names no list of readings in "
                       f"{d['pilot']} — without the readings the bias is an assertion")
            continue
        kind = q["location"]["statistic"]
        estimate = LOCATION[kind](readings)
        bias = abs(estimate - float(cal["truth"]))
        effect = float(q["effect"]["value"])
        if bias >= effect and not str(cal.get("bias_accepted") or "").strip():
            out.append(
                f"{name}: on known truth {cal['truth']} the estimator reads {estimate:.6g} "
                f"({kind} of {len(readings)} readings) — a bias of {bias:.6g}, not smaller "
                f"than the effect {effect:.6g} it must resolve. **The effect and the "
                f"estimator's own bias are then the same number.** Fix the estimator, or "
                f"say on the record why the reading is still worth having: "
                f"calibration.bias_accepted.")
    return out


def consistency_problems(d: dict, folder: pathlib.Path) -> list[str]:
    """Re-derive N for every quantity. **This half cannot be satisfied by typing.**"""
    from newlife.stochastic.design import required_n

    pilot_path = folder / d["pilot"]
    if not pilot_path.exists():
        return [f"pilot={d['pilot']} does not exist — without the samples the declared N "
                f"cannot be re-derived, and an N nobody can re-derive is an asserted one"]
    pilot = json.loads(pilot_path.read_text(encoding="utf-8"))
    out: list[str] = []
    out += tail_crosscheck(d, pilot)
    out += calibration_problems(d, pilot)
    for q in d["quantities"]:
        name = q["name"]
        by_point = pilot.get(name)
        if not by_point:
            out.append(f"{name}: no pilot samples under this name in {d['pilot']}")
            continue
        # **The hardest point governs.** The test fires when *any* point differs, so the
        # sample size must serve the point where the difference is hardest to see.
        worst: int | None = 0
        for point, values in sorted(by_point.items()):
            n_p, _ = required_n(
                values, float(q["effect"]["value"]),
                power=1.0 - float(q["errors"]["beta"]),
                kind=q["location"]["statistic"],
                level=1.0 - float(q["errors"]["alpha"]),
                resamples=int(q["derivation"]["resamples"]),
                trials=int(q["derivation"]["trials"]),
                seed=int(q["derivation"]["seed"]),
                budget=int(q["budget"]["max_n"]))
            if n_p is None:
                worst = None
                break
            worst = max(worst or 0, n_p)
        # **Correlated draws carry less information than their count suggests.** The
        # bootstrap resamples as if they were independent, so the derived N is for the
        # independent case and must be inflated by the declared factor.
        ind = q.get("independence") or {}
        if worst is not None and ind.get("assumed") == "correlated":
            factor = float(ind["effective_n_factor"])
            worst = math.ceil(worst / factor)
        declared = q["result"].get("n")
        if worst != declared:
            out.append(
                f"{name}: declared n={declared} but re-deriving from effect="
                f"{q['effect']['value']}, location={q['location']['statistic']}, "
                f"alpha={q['errors']['alpha']}, beta={q['errors']['beta']} gives {worst}. "
                f"**A number that does not follow from its own premises was chosen, "
                f"not derived.**")
    return out


def check(folder: pathlib.Path) -> list[str]:
    from newlife.stochastic.schema import shape_problems
    d, problems = load(folder)
    if d is None:
        return problems
    problems = shape_problems(d)
    if problems:
        return problems                     # shape first: consistency needs the fields
    return consistency_problems(d, folder)


# ─────────────────────────── negative control ───────────────────────────

def _complete() -> dict:
    return {
        "schema": "newlife.judgement-design.v1",
        "pilot": "results/pilot-samples.json",
        "sampling": {"shared": True, "n_effective": 64},
        "applicability": {"comparison_form": "two_group_location_shift",
                          "why": "two models answering one prompt; the comparison is a location shift"},
        "quantities": [{
            "name": "log10_tof", "unit": "log10(1/s)", "points": ["-1.0"],
            "effect": {"value": 2.0, "rationale": "smaller than this changes no decision"},
            "location": {"statistic": "trimmed", "trim": 0.2,
                         "why": "heavy tail; the bootstrap of a mean fails there"},
            "spread": {"statistic": "MAD", "value": 1.35},
            "errors": {"alpha": 0.05, "beta": 0.2},
            "derivation": {"method": "bootstrap_power", "resamples": 300,
                           "trials": 60, "seed": 20260906},
            "budget": {"max_n": 256, "seconds_per_sample": 2.0},
            "heavy_tail": {"detected": True, "evidence": "one value at -400 in 8 draws",
                           "consequence": "location switched from mean to trimmed"},
            "independence": {"assumed": "iid", "evidence": "each call is issued independently, with no shared state"},
            "pilot_adequacy": {"min_per_point": 40, "why": ""},
            "result": {"n": 64, "power_curve": [[4, 0.1], [8, 0.3], [64, 0.83]]},
            "calibration": {"truth": -2.0, "family": "a synthetic rate law with a known "
                            "closed-form turnover, not this fit's output",
                            "samples": "log10_tof@truth", "bias_accepted": None},
        }],
    }


# Measured 2026-09-06 and deliberately left alone: this function is 70 lines, the
# largest here, and its twenty-odd cases share one shape (deepcopy, drop a field,
# assert red). Turning them into a table would save about 25 lines and stop a new
# field from being added without a case. **Not done**: it fixes no defect and was in
# no registration's criteria. Do it the next time a field is actually added.
def _selftest() -> int:
    from newlife.stochastic.schema import shape_problems
    ok = True

    def case(name: str, d: dict, want_red: bool) -> None:
        nonlocal ok
        red = bool(shape_problems(d))
        good = red == want_red
        ok &= good
        print(f"  [{'RED' if red else 'green'}] {name}"
              f"{'' if good else '  <-- expected the opposite'}")

    case("a complete design", _complete(), False)

    import copy
    for field in ("effect", "location", "spread", "errors", "derivation", "budget",
                  "heavy_tail", "result", "points", "calibration"):
        d = copy.deepcopy(_complete())
        del d["quantities"][0][field]
        case(f"missing {field}", d, True)

    d = copy.deepcopy(_complete()); d["quantities"] = []
    case("no quantities at all", d, True)
    d = copy.deepcopy(_complete()); d["schema"] = "something.else"
    case("wrong schema id", d, True)
    d = copy.deepcopy(_complete()); d["quantities"][0]["location"]["statistic"] = "geometric"
    case("unknown location statistic", d, True)
    d = copy.deepcopy(_complete()); d["quantities"][0]["effect"]["rationale"] = "   "
    case("effect given with an empty rationale", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["location"] = {"statistic": "mean", "why": ""}
    case("heavy tail + mean with no argument", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["location"] = {"statistic": "mean",
                                      "why": "support is bounded; no tail in practice"}
    d["quantities"][0]["heavy_tail"]["detected"] = False
    case("mean with the tail argued away", d, False)
    d = copy.deepcopy(_complete()); d["quantities"][0]["result"]["power_curve"] = []
    case("N without a power curve", d, True)

    # Negative controls for the four defences added after the self-review
    d = copy.deepcopy(_complete()); del d["applicability"]
    case("no applicability declared", d, True)
    d = copy.deepcopy(_complete())
    d["applicability"]["comparison_form"] = "monotone_trend"
    case("a trend question forced into two-group shape", d, True)
    d = copy.deepcopy(_complete()); d["applicability"]["why"] = "  "
    case("applicability without a reason", d, True)
    d = copy.deepcopy(_complete()); del d["quantities"][0]["independence"]
    case("missing independence", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["independence"] = {"assumed": "correlated", "evidence": "AR(1)"}
    case("correlated without an effective-n factor", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["independence"] = {"assumed": "correlated", "evidence": "AR(1)",
                                          "effective_n_factor": 0.12}
    case("correlated with a factor", d, False)
    d = copy.deepcopy(_complete()); del d["quantities"][0]["pilot_adequacy"]
    case("missing pilot_adequacy", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["pilot_adequacy"] = {"min_per_point": 8, "why": ""}
    case("a pilot of 8 per point with no argument", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["pilot_adequacy"] = {"min_per_point": 8,
                                            "why": "the remote service rate-limits; eight is the whole budget"}
    case("a thin pilot argued on the record", d, False)

    # M7, shape
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"] = {"not_applicable": "read directly off the counter"}
    case("calibration not applicable, with a reason", d, False)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"] = {"not_applicable": " "}
    case("calibration not applicable, no reason", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"]["family"] = ""
    case("calibration with no word on where the truth comes from", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"]["not_applicable"] = "x"
    case("calibration that is both given and not applicable", d, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"]["samples"] = "log10_tof"
    case("calibration readings under the quantity's own key", d, True)

    # M7, the arithmetic — a pure function of the design and the pilot file
    def arith(name: str, d: dict, pilot: dict, want_red: bool) -> None:
        nonlocal ok
        red = bool(calibration_problems(d, pilot))
        good = red == want_red
        ok &= good
        print(f"  [{'RED' if red else 'green'}] {name}"
              f"{'' if good else '  <-- expected the opposite'}")

    near = {"log10_tof@truth": [-2.3, -1.9, -2.1, -1.8, -2.2]}       # bias ~0.06 < 2.0
    far = {"log10_tof@truth": [0.1, 0.4, 0.2, 0.3, 0.0]}             # bias ~2.2 >= 2.0
    arith("bias well inside the effect", _complete(), near, False)
    arith("bias as large as the effect, not accepted", _complete(), far, True)
    d = copy.deepcopy(_complete())
    d["quantities"][0]["calibration"]["bias_accepted"] = "only the sign is used downstream"
    arith("bias as large as the effect, accepted on the record", d, far, False)
    arith("readings absent from the pilot file", _complete(), {}, True)
    arith("readings that are not numbers", _complete(), {"log10_tof@truth": ["a"]}, True)

    print(f"  [{'green' if ok else 'RED'}] selftest: every omission red, "
          f"the complete design green")
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
    problems = check(args.folder)
    for p in problems:
        print(f"[FAIL] {DESIGN_FILE}: {p}")
    if problems:
        print(f"\nThe repetition count is not accounted for: {len(problems)} item(s).")
        return 1
    print("Judgement design: every quantity answers the seven, each n re-derives, and "
          "each estimator's bias on known truth is below its effect or accepted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
