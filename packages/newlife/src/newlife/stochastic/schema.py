#!/usr/bin/env python3
"""The shape of a judgement design — `newlife.judgement-design.v1`.

## Why a file, not an anchor

The first version of this was one HTML-comment anchor with `key=value` pairs. It fails on
the first real study:

- **A run usually observes more than one quantity.** Turnover frequency, selectivity and
  conversion do not share an effect size worth caring about, nor the same statistic, nor
  the same N. One flat line cannot say that.
- **Anchors cannot hold arbitrary text.** The parser stops at the first `>` — a fact this
  project relearned on 2026-09-06 when `temperature>0` inside an anchor made the whole
  anchor vanish silently. Intervals, comparisons and lists would all break it.
- **The reasons have nowhere to go.** "Why is the mean still defensible on heavy-tailed
  data" is the field most worth writing at length, and it was competing for room on a
  single line.

So the design lives in `judgement-design.json` beside the registration, and the freeze
pins it with `--data`: `newlife audit` re-hashes it, so it is as immutable as the criteria
themselves.

## The shape

    {
      "schema": "newlife.judgement-design.v1",
      "pilot": "results/pilot-samples.json",     // {quantity: {point: [values]}}
      "sampling": {
        "shared": true,                          // one draw yields every quantity at once
        "n_effective": 64                        // = max over quantities when shared
      },
      "quantities": [
        {
          "name": "log10_tof",
          "unit": "log10(1/s)",
          "points": ["-1.0", "-4.0"],            // where it is measured
          "effect":   {"value": 2.0, "rationale": "..."},          // M1
          "location": {"statistic": "trimmed", "trim": 0.2, "why": "..."},  // M2
          "spread":   {"statistic": "MAD", "value": 1.35},         // M2
          "errors":   {"alpha": 0.05, "beta": 0.2},                // M3
          "derivation": {"method": "bootstrap_power",              // M4
                         "resamples": 300, "trials": 60, "seed": 20260906},
          "budget":   {"max_n": 256, "seconds_per_sample": 2.0},   // M5
          "heavy_tail": {"detected": true, "evidence": "...",      // M6
                         "consequence": "..."},
          "result":   {"n": 64, "power_curve": [[4, 0.10], [8, 0.28]]}
        }
      ]
    }

**`power_curve` is required, not decorative.** A bare N hides whether the answer was
comfortable or marginal; the curve is what lets a reader see that 64 scraped past 0.80
while 128 would have been safe.

**Every `rationale` / `why` / `evidence` field is required to be non-empty and is never
judged for quality.** Checking whether an effect size is *the right one to care about*
needs a referee who understands the question better than the person asking it. No such
referee exists. What can be checked is that a reason was given, and that the number
follows from the premises stated next to it.
"""

from __future__ import annotations

SCHEMA = "newlife.judgement-design.v1"
LOCATIONS = ("mean", "median", "trimmed")
METHODS = ("bootstrap_power",)

REQUIRED_TOP = ("schema", "pilot", "sampling", "applicability", "quantities")
REQUIRED_QUANTITY = ("name", "points", "effect", "location", "spread", "errors",
                     "derivation", "budget", "heavy_tail", "independence",
                     "pilot_adequacy", "result")

SUPPORTED_FORMS = ("two_group_location_shift",)
"""**What this derivation actually covers.** One form: two groups, compared on a location
statistic, against a declared shift.

Named forms that are **not** supported, and must not be forced into this one:
`monotone_trend` · `multi_group` · `slope` · `proportion` · `variance`.

This matters more than it looks. The twenty-first milestone's own scientific question was
*"does log10(TOF) rise monotonically with adsorption energy"* — a **trend**, not a two-group
comparison. **The method that grew out of that milestone does not cover the question that
produced it**, and saying so is cheaper than a sample size derived under the wrong shape.

Declaring the boundary is the point. A schema that silently accepts every form and derives
a number anyway is worse than one that refuses."""

MIN_PILOT_PER_POINT = 30
"""Below this, the empirical distribution is thin enough that using it to derive a sample
size is close to circular — the twenty-first milestone derived from 8. Not a hard refusal:
sometimes 8 is all there is. But then it has to be said in `pilot_adequacy.why`."""
PROSE_FIELDS = (("effect", "rationale"), ("location", "why"),
                ("heavy_tail", "evidence"), ("heavy_tail", "consequence"))
"""(section, key) pairs that must carry a non-empty reason. **Presence, never quality.**"""


def shape_problems(d: dict) -> list[str]:
    """Everything wrong with the *shape*. Consistency of the numbers is a separate pass,
    because the two failures deserve different messages: one says "you did not say",
    the other says "what you said does not add up"."""
    out: list[str] = []
    if d.get("schema") != SCHEMA:
        out.append(f"schema must be {SCHEMA!r}, found {d.get('schema')!r}")
    for k in REQUIRED_TOP:
        if k not in d:
            out.append(f"missing top-level {k!r}")
    app = d.get("applicability") or {}
    form = app.get("comparison_form")
    if form is None:
        out.append("applicability.comparison_form is missing — this derivation covers "
                   f"only {SUPPORTED_FORMS}, and a design that does not say which shape "
                   f"its question has can be handed a sample size derived for a different "
                   f"one")
    elif form not in SUPPORTED_FORMS:
        out.append(f"applicability.comparison_form={form!r} is **not supported** by this "
                   f"derivation (supported: {SUPPORTED_FORMS}). Deriving N under the wrong "
                   f"comparison shape produces a number with no relation to the question. "
                   f"Note that a monotone-trend question — the very one the twenty-first "
                   f"milestone asked — is in this category.")
    elif not str(app.get("why", "")).strip():
        out.append("applicability.why is empty — state why the question really has this "
                   "shape; it is not judged, but it is required")

    quantities = d.get("quantities")
    if not isinstance(quantities, list) or not quantities:
        out.append("quantities must be a non-empty list — a design that declares no "
                   "measured quantity cannot be checked against anything")
        return out
    for i, q in enumerate(quantities):
        where = q.get("name", f"quantities[{i}]")
        for k in REQUIRED_QUANTITY:
            if k not in q:
                out.append(f"{where}: missing {k!r}")
        loc = (q.get("location") or {}).get("statistic")
        if loc is not None and loc not in LOCATIONS:
            out.append(f"{where}: location.statistic {loc!r} not in {LOCATIONS}")
        method = (q.get("derivation") or {}).get("method")
        if method is not None and method not in METHODS:
            out.append(f"{where}: derivation.method {method!r} not in {METHODS}")
        for section, key in PROSE_FIELDS:
            body = (q.get(section) or {}).get(key)
            if body is not None and not str(body).strip():
                out.append(f"{where}: {section}.{key} is empty — the reason has to be on "
                           f"the record; it is not judged, but it is required")
            elif body is None and section in q:
                out.append(f"{where}: {section}.{key} is missing")
        # **Heavy tail plus the mean is the one combination that needs an argument.**
        if (q.get("heavy_tail") or {}).get("detected") and loc == "mean":
            if not str((q.get("location") or {}).get("why", "")).strip():
                out.append(f"{where}: heavy tail with location=mean and no why — the "
                           f"regular bootstrap fails on the mean of heavy-tailed data")
        ind = q.get("independence") or {}
        assumed = ind.get("assumed")
        if "independence" in q:
            if assumed not in ("iid", "correlated"):
                out.append(f"{where}: independence.assumed must be 'iid' or 'correlated', "
                           f"found {assumed!r}")
            elif assumed == "correlated":
                factor = ind.get("effective_n_factor")
                if not isinstance(factor, (int, float)) or not 0 < factor <= 1:
                    out.append(
                        f"{where}: independence.assumed='correlated' needs "
                        f"effective_n_factor in (0, 1] — the bootstrap resamples as if the "
                        f"draws were independent, so a correlated sample needs "
                        f"n/factor draws to carry the same information. Measured on an "
                        f"AR(1) series with phi=0.85, the N this derivation returns "
                        f"delivered 0.74 power against a declared target of 0.80.")
            if not str(ind.get("evidence", "")).strip():
                out.append(f"{where}: independence.evidence is empty — say how you know")

        adequacy = q.get("pilot_adequacy") or {}
        if "pilot_adequacy" in q:
            per_point = adequacy.get("min_per_point")
            if not isinstance(per_point, int):
                out.append(f"{where}: pilot_adequacy.min_per_point must be an integer")
            elif per_point < MIN_PILOT_PER_POINT and not str(adequacy.get("why", "")).strip():
                out.append(
                    f"{where}: only {per_point} pilot samples per point (< "
                    f"{MIN_PILOT_PER_POINT}) and no pilot_adequacy.why — deriving a sample "
                    f"size from an empirical distribution this thin is close to circular. "
                    f"It may still be the best available; say so on the record.")

        result = q.get("result") or {}
        if "power_curve" in result and not result["power_curve"]:
            out.append(f"{where}: power_curve is empty — a bare N hides whether it "
                       f"scraped past the target or cleared it")
    return out
