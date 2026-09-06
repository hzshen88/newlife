# How newlife itself was built

newlife was built under the discipline it ships. This page is the record: the acceptance
pipeline every milestone went through, the verdict of each, what a reader can check here
and what they cannot.

## What is public and what is not

`results/` holds one directory per closed milestone with the machine-computed verdict
bundle; `passed` is always computed from a conjunction, never hand-written. The runners
that produced them are under `packages/newlife/src/newlife/conform/`. The Chinese world
documents under `docs/zh/worlds/` describe each question, its frozen known answer and the
comparison tier that applied.

**The frozen registration documents are not published.** Each milestone's goal, question,
plan and preregistration live in the author's private exploration archive (the
`exloop-archive` repository's `docs/science-superpowers/`; the public `exloop` repository
holds only the skill), frozen there with `prereg.sh freeze` before any
implementation code was written, and stamped by that repository's git history. That
history holds forty freeze and stamp commits and cannot be rewritten or moved without
breaking the chain, and the same repository holds the author's personal explorations, so
it stays private. The consequence for a reader is plain: **you cannot run `newlife audit`
on the author's milestones.** You can read the bundles, re-run the runners, and read the
world documents. The project's claim is about your questions in your repository, where
`prereg.md` and `results/` share one git ancestry; the author's milestones are offered as
history, not as evidence you are asked to trust.

The bundles under `results/` also contain absolute paths from the author's machine. They
are frozen artifacts and are left as they were produced.

## How a milestone gets accepted

A milestone of newlife is a question folder in this repository, exactly what the tool
scaffolds for a user (since 2026-09-06; the twenty-two before it followed a longer pipeline
whose frozen documents are private, see above):

```
questions/<slug>/goal.md → prereg.md (newlife freeze) → implementation → verdict.py → results/ → goal.md §5
```

- **goal.md**: what this work is meant to buy, with the six anchors the freeze requires,
  *before* the question narrows. It is judged again at the end (§5, achieved / not_achieved
  / regressed / not_applicable), and it is allowed, and has happened, for a milestone to
  reach a supported hypothesis while its goal went backwards.
- **README.md** in the folder: the design rationale — what was compared and why, what was
  ruled out — the part the tool deliberately does not ask a user for.
- **prereg.md**: frozen by `newlife freeze` before the implementation exists; `results/`
  is what `verdict.py` computed, never an edited file.
- **One row** in the table below. `scripts/check_record.py` reconciles the folders against
  it and goes red on any missing cell; the older bundles under `results/` keep their older
  six-cell record.

The two failure modes this ordering exists to prevent are both on record in the proposal's
§8: freezing criteria after seeing results, and building for a user who does not exist yet.

## Verdicts

Twenty-two milestones are decided. The four earliest predate the goal stage; every later
one was judged against criteria frozen before the implementation existed, except archival
replay, which ran without a separate registration and says so. Every verdict below is
computed by a runner from the frozen conjunction, not asserted by hand:

| Milestone | Verdict | Evidence |
|---|---|---|
| v0.1a lowering completeness | H1 supported — `compatible_for_frozen_slices_v1_lowered` | `results/v0.1a/` |
| v0.1b staging declarability | H1 supported — `staging_declarable_for_frozen_slices` | `results/v0.1b/` |
| v0.2 World 1 (Resource Foraging) | gate closed — bit-exact L2 reproduction, both conditions | `results/v0.2/gate.json` |
| v0.3 compare (causal attribution) | H1 supported — `causal_attribution_declarable_for_world1_pairs` | `results/v0.3/summary.json` |
| World 2 (`ms` minimal coalescent) | H1 supported — `ms_minimal_coalescent_reproducible` | `results/second-world/summary.json` |
| World 4 (Moran genealogy vs Kingman) | H1 supported — exact topology for `n ∈ {3..7}`, `S̄` in the frozen region | `results/fourth-world/summary.json` |
| World 5 (the gate's own check coverage) | **H0 supported** — 3 of 47 checks are `hollow`; first non-H1 verdict in eight milestones | `results/fifth-world/summary.json` |
| World 3 (Moran under selection) | H1 supported — per-step oracle replay over 4050 replicates, all three cells in region | `results/third-world/summary.json` |
| World 6 (staging bypasses — a retrospective audit) | H1 supported — all four scheduling loops are unrolling-expressible; the recorded "same cause five times" does **not** hold | `results/sixth-world/summary.json` |
| World 7 (how much of the harness is generable) | **H0 supported** — 4 of 42 parts fall outside DEVS's model/simulator/experimental-frame plus `rng`; they cluster into two capabilities the canonical decomposition does not name | `results/seventh-world/summary.json` |
| World 8 (generic harness absorbs World 4) | H1 supported — all four harness parts absorbed, config is pure data, verdict byte-identical; **P3 met for the first time**, though only for a world with no tick loop | `results/eighth-world/summary.json` |
| World 9 (declarative termination for a real tick loop) | **H0-a supported** — the condition *is* expressible in the frozen operator set (no inner-platform effect), but `run` is a mixed part and the harness collides with World 1 over engine-assembly ownership | `results/ninth-world/summary.json` |
| Verdict seam (extracted from eight runners) | **INVALID** — three generations of verdict representation do fit one three-valued Definition, but one frozen product is no longer reproducible for an unrelated reason (IC-4) | `results/tenth/summary.json` |
| Verdict rot (re-running eight old verdicts) | H1 supported — seven of seven reproduce byte-for-byte, excluding the one already known broken; the literature's ~3.4% base rate comes from multi-year dependency drift, which this has never been tested against | `results/eleventh/summary.json` |
| Archival replay (declared deps only) | H1 — five of five replay byte-for-byte in a clean venv, but one undeclared dependency (a C toolchain) surfaced; **no separate preregistration was frozen**, so this one's audit is unavailable | `results/twelfth/summary.json` |
| Undeclared dependencies | **H0 supported** — with `git` absent one runner still emits a well-formed verdict blaming the wrong cause; the fourth instance of the same silent-degradation shape, and the first the scanner cannot reach | `results/thirteenth/summary.json` |
| Cross-runtime verification (one world, two engines) | **H1** — World 4's single declaration runs on both `ReferenceKernel` and `process-bigraph`, **2101/2101 byte-identical**, negative control goes red; process-bigraph goes from zero users to actually running a world. **But the seam is still single-provider**: its Definition, read off `ReferenceKernel`, is a per-stage *pull* interface, and process-bigraph is a *push* runtime — unforeseen going in | `results/fourteenth/summary.json` |
| Admitting a third-party process | **H1** — `process_bigraph`'s own `Grow` runs inside a newlife world **with its source untouched**, byte-identical to bare pb, and the contract still bites (mis-declared path and undeclared effect are both rejected; a meta-control confirms the rejection comes from the contract). **But the published ecosystem does not install**: both `biosimulator-processes` and `vivarium-interface` import a `ProcessTypes` that no usable pb version has, and neither declares a version bound. The declaration is written *by us*, so this proves the contract binds a written declaration — not that the ecosystem plugs in safely | `results/fifteenth/summary.json` |
| Admitting a genuinely external package | **H1** — `spatio-flux`'s `MonodKinetics` (a separately published third-party package) runs inside a newlife world **with its source untouched**, byte-identical to bare pb on both trajectories, with the contract still biting and a meta-control confirming the rejection comes from the contract. **The previous milestone's "the ecosystem does not install" is half retracted**: two entry packages fail, the ecosystem does not. The third party ships the *vocabulary* (`register_types`); the *authority* declaration is still written by us | `results/sixteenth/summary.json` |
| Admitting a solver-backed process | **H1** — `spatio-flux`'s `DynamicFBA` (an LP solved every tick, E. coli core) runs inside a newlife world **with its source untouched**, byte-identical to bare pb, contract still biting (and the rejection must come from newlife's own error types, not the solver's). **Three things must be reported alongside**: byte-identity here buys *the same solver's same choice*, not *the same scientific answer* (FBA optima are typically non-unique); GLPK is a third non-Python dependency that arrived unannounced — **an exhaustive enumeration has a shelf life**; and port granularity caps declaration granularity | `results/seventeenth/summary.json` |
| Deriving the authority declaration | **H0** — the criterion demanded item-by-item equality with the three hand-written specs; `claims` matched 1/3. **But nothing turned out to be underivable**: `allowed_effects` 3/3 and **the add/set operator 3/3** — the very item the effect-systems literature names as *not* inferable from interface types, recovered by a **behavioural probe** on the registered store type. Both `claims` mismatches are mechanically classified as our own hand-written choices (`layout`) or limitations (`finer`), not missing information. **The bottleneck is removable** | `results/eighteenth/summary.json` |
| Is yield an input or an outcome? | **H1** — `MonodKinetics` and `DynamicFBA` are interchangeable at the same port and **share the same uptake law**; sweeping the oxygen bound, dFBA secretes acetate and its yield drops (textbook overflow metabolism) while Monod's yield stays exactly its declared constant. **Matching one point is not representing the degree of freedom** — though the negative control that was supposed to show this (Z5) was later found to be **vacuously true** (a `for _ in SWEEP` that discards the loop variable; the flaw is in the frozen preregistration, not the implementation). **H1 stands and the artifact is not overwritten** — the conclusion follows arithmetically from Z3 (dFBA's yield varies by 56.2% across the sweep) and Z4 (Monod's is constant). See `docs/zh/worlds/019-yield-input-or-outcome.md` §6. First end-to-end run using only off-the-shelf blocks: **221 lines total, 0 new world code** | `results/nineteenth/summary.json` |
| Can a world declare which kind of reproduction it offers? | **H0** — of 21 bundles, 12 came back `unclassified`, **every one of them for `no_runner_found`**: the three-class table matched all 9 bundles whose runner could be located, and not one fell through for want of a feature. The H0 measures a filename heuristic, not the division under study — visible only because the registration required the reason to come from a fixed vocabulary computed by code. Product-level artifact of the counterparty's argument: reading the **artifact alone** classifies 21/21 and discovers nothing; adding the runner source exposes the 12. **First milestone with the registration and the artifact in one repository — `newlife audit` returns PASS on all five arms, CHRONOLOGY included, which the twenty cross-repository registrations could never establish.** | `questions/2026-09-06-reproduction-class-declarability/results/` |
| Can a world whose outcome differs every run be judged? | **H0** — one test used in both directions: the same model's two batches must come back equivalent (S4, true), two different models must not (S5, **false**). **The failure is not that the models are indistinguishable.** One batch carried a -400 outlier, sd=138, making that point's interval 159 wide against a 2–3 difference in means — an effect size around 2% of the interval, where any two samples of eight are equivalent. **And the convergence rule points the wrong way**: wider variance means wider intervals means the two halves agree sooner, so it stopped at n=8 out of a budget of 32 — it calls a halt exactly when more samples are most needed. That defect is visible *only* because S5 failed; had it squeaked through, n=8 would have read as efficiency. | `questions/2026-09-06-stochastic-world-judgeable/results/` |
| Can a *method* for choosing judgement parameters replace a rule? | **H0**, and the only failing unit is a budget. No fixed rule survives every world — the previous milestone's convergence test stopped earliest exactly when variance was largest — so this one ships six questions that must be answered before freezing, plus a gate that re-derives the declared N from the premises written beside it. Applied to two worlds it produced genuinely different answers, chosen by the data: tail ratio 3.77 gave a trimmed mean and **no N within 64 calls**; tail ratio 1.17 gave the mean and **n=16**, whose interval contained zero for two batches of the same configuration and excluded zero across configurations — **one threshold satisfying both ends**, which the previous milestone could not do. "Undecidable within this budget" is the method working, not failing: it priced the question instead of returning a number that would have looked fine. | `questions/2026-09-06-judgement-design-method/results/` |

World 4 is the first world with **no external program as a comparison target anywhere**:
it checks against mathematics the project derives and verifies itself. It is also the first
time pain point P1 (cross-world mechanism composability) advanced: World 2's observer is
reused **unmodified through the registry**, judged by object identity rather than an import
list. The goal records that as `achieved` in its narrow, pre-frozen sense, **P1 moved off
zero**, not "P1 solved".

Recorded as honestly as the successes: World 2 was the second consecutive world to bypass
`staging.py` and P1 went slightly backwards there; World 4 bypasses it a **fourth**
consecutive time, and its reuse works only because the consumer accommodates World 2's
namespace (`TREE_PATH` stays `second_world/tree`); that composition is not clean. Both
costs were pre-declared before execution. See `docs/zh/design/proposal.md` §7 and
`docs/zh/worlds/004-moran-genealogy.md`. That is what the goal step exists to surface.

**The discipline is that criteria freeze first and code follows.** See
`docs/zh/design/proposal.md` (§7 schedule) and the originating exploration (in the
author's private archive) for the full evidence chain: a frozen, pre-registered
dual-implementation pressure test (66/66 checks, 0-warning audit) established that
Process-Bigraph is a viable composition runtime *only with* a mandatory, independently
versioned biological profile, which is what this repository builds.

## What the first real questions produced

One toolchain smoke run, two honestly recorded `INVALID`s, and one `H1` reproducing
Rosenfeld–Elowitz–Alon (2002) with a blind prediction that held; written up in
`docs/zh/product/2026-09-04-first-user-questions.md` (Chinese). Both INVALIDs had the same
non-scientific cause, a criterion naming a quantity nobody had looked at before the freeze,
and that is where `newlife pilot` and the pilot-coverage gate come from. The first of those
questions also surfaced a silent defect in this library that four milestones with
third-party code had missed, because all four happened to use the same timestep.

## Lineage

- **ParaLife** (Julia monorepo, first generation): evidence discipline carried by
  repository governance (ADR sign-off, frozen run bindings, architecture gates). newlife is
  the second generation: the same discipline enforced at runtime, plus the mechanism
  composition ParaLife deliberately omitted. ParaLife is a private repository.
- `EvidenceCore.jl` stays frozen in ParaLife as the **oracle** that generates proofroot's
  cross-language test vectors; ParaLife is not migrated.
- Upstream runtime: [process-bigraph](https://github.com/vivarium-collective/process-bigraph)
  and [bigraph-schema](https://github.com/vivarium-collective/bigraph-schema)
  (Apache-2.0), pinned `==1.8.3` / `==1.6.0`, confined to the adapter layer.
