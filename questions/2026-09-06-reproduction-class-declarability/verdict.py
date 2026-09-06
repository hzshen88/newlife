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
import json
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
SWEEP = (1.0, 2.0, 4.0, 8.0)


def model(x: float) -> float:
    """Placeholder: a trivial deterministic model. Replace with your own assembly.

    `newlife blocks` lists every Process/Step installed in this environment.
    """
    return x * x


# ─────────────────────────────────────────────────────────────────────
# CRITERIA. **Write each one as a pure predicate** — that is what lets the runner
# prove, with synthetic inputs, that it can go red (registration F1).
# ─────────────────────────────────────────────────────────────────────
def strictly_increasing(values: list[float]) -> bool:
    return all(b > a for a, b in zip(values, values[1:]))


def criteria_can_fail() -> dict[str, bool]:
    """**F1: every criterion must be able to go red.** Proved at runtime, not asserted
    in prose.

    Where this comes from: a negative control once written as `[f(x) for _ in SWEEP]` —
    the loop variable was discarded, so five identical runs were compared against each
    other. The criterion was true by construction, had zero discriminating power, and sat
    inside the conjunction for an entire milestone.
    **A criterion that is true by construction never goes red, and people only
    investigate what is red.**
    """
    return {
        "false on a constant sequence": strictly_increasing([1.0, 1.0, 1.0]) is False,
        "false on a decreasing sequence": strictly_increasing([3.0, 2.0, 1.0]) is False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "results/summary.json")
    args = ap.parse_args()

    prov = provenance.snapshot(
        preregistration_freeze=provenance.frozen_at(HERE / "prereg.md"),
        env_lock_sha256=provenance.file_digest(HERE / "env.lock"),
    )
    observed = [model(x) for x in SWEEP]

    can_fail = criteria_can_fail()
    # S1: the packages installed *now* are exactly the ones `env.lock` recorded at the
    # freeze. **The first version of this line compared the file's digest with a digest of
    # the same file taken a moment earlier — true by construction, and it shipped in every
    # early question.** `newlife freeze` rewrites env.lock from the live environment and
    # pins its hash into the registration; `newlife audit` proves the file never changed
    # afterwards; this line proves the run happened in that environment.
    s1 = provenance.env_text() == (HERE / "env.lock").read_text(encoding="utf-8")
    s2 = strictly_increasing(observed)
    # **"the criteria can fail" is its own visible slot in the conjunction, not a
    # detail nested inside another unit.** The first version folded it into a sub-field
    # of S2, so the registration read S0∧S1∧S2∧S3 while the code computed three —
    # the unit-alignment gate in `newlife check` caught exactly this the first time it
    # ran against a real question folder.
    units = {"S1_env_unchanged": {"passed": s1},
             "S2_increases_across_sweep": {"passed": s2},
             "S3_criteria_can_fail": {"passed": all(can_fail.values()),
                                      "demonstrations": can_fail}}

    invalid = not s1                       # IC-2: a changed environment is not a judgement
    passed = all(u["passed"] for u in units.values())
    verdict = decide(h1=(not invalid) and passed,
                     h0=(not invalid) and not passed, invalid=invalid)

    summary = {"schema": "2026-09-06-reproduction-class-declarability.v1", "provenance": prov,
               "sweep": list(SWEEP), "observed": observed, "units": units}
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
