# {title}

**Frozen at commit:** _pending_

## 1. Hypothesis

- **H1**: (one sentence. **It must be the sentence this run could falsify** — not a
  research direction.)
- **H0**: any one of them fails. **H0 must name which one.**

## 2. Judgement units (mechanical conjunction, computed by the runner — **never filled in by hand**)

| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | Self-reproduction | two independent runs produce byte-identical artifacts | mechanical |
| **S1** | Environment unchanged | sha256 of `env.lock` matches the one in the artifact | mechanical |
| **S2** | (your positive control) | | |
| **S3** | every criterion proves it can fail | each predicate returns false on a synthetic counterexample, computed at runtime | mechanical |

**verdict = S0 ∧ S1 ∧ S2 ∧ S3.** Any one false → H0; **S0 false → INVALID**
(two runs disagreeing means this run had no discriminating power — that is not
"the hypothesis failed").

**The final verdict lives in `results/reproduction.json`**, not in `summary.json` —
S0 cannot be written into the file it is reproducing. The key in `summary.json` is
called `verdict_before_reproduction`, **deliberately not `verdict`**, so it cannot
pass itself off as the real one.

**Fill in the "Piloted?" column for every unit** — `seen` / `blind` / `mechanical`.
A confirmatory round in which nothing is blind carries no information.

## 3. Frozen implementation constraints

- **F1**: **Every criterion must be able to go red.** Prove it in the runner at runtime
  with synthetic inputs, not in prose. **A criterion that is true by construction never
  goes red, and people only investigate what is red.**
- **F2**: `passed` is computed from the conjunction, never assigned.
- **F3**: the artifact records the newlife source digest, the `env.lock` hash, the
  platform and the Python version.
- **F4**: **this question's verdict must not run any other question's runner.**
  Questions are siblings, not a chain.

## 4. Invalidation conditions (**written separately from the criteria**)

Criteria say whether the hypothesis holds. Invalidation conditions say whether this run
counts at all. Merge them and a disappointing result gets quietly reclassified as
"the run didn't count".

- **IC-1**: a building block fails to produce a result → environment problem, invalid.
- **IC-2**: S1 false (the environment changed) → not a judgement; rebuild and rerun.

**Hygiene checks belong here, not in the conjunction.** A mechanical check that can fail
on perfectly legitimate data must never hold veto power over a scientifically successful
run.

## 5. Declared in advance: the boundary of the conclusion

(What this run does **not** establish. At closeout, "we showed A" and "we did not show B"
must be written as separate sentences — **the first must never stand in for the second**.)
