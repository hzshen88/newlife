# newlife

A verifiable profile layer for composable biological simulation: path authority,
effect validation, single-path lowering, and canonical evidence traces — the
scientific semantics a bare composition runtime does not provide.

| Package | Scope | Depends on |
|---|---|---|
| [`packages/proofroot`](packages/proofroot/) | Language-neutral trust core: named RNG stream derivation, run phases, evidence tiers, canonical serialization spec + cross-language vectors. Zero dependencies, zero domain semantics. | — |
| [`packages/newlife`](packages/newlife/) | BiologicalProfile: the four contracts (StateClaim / MechanismSpec / Effect / Resolver), path authority, read-only alias guard, single-path lowering, canonical traces. | proofroot |

## Ask your own question

Your question lives in **your** repository, not this one.

Install the preregistration harness from PyPI. `proofroot` is installed as its
trust-core dependency; install it directly only when you need that lower-level API.

```bash
python -m pip install newlife
# Optional simulation backends:
python -m pip install "newlife[process-bigraph]"
python -m pip install "newlife[spatio-flux]"

mkdir my-research && cd my-research
git init                              # git is required: the freeze commit is the timestamp
git config user.name "Your Name"
git config user.email "you@example.com"
newlife skills install                # install the question-shaping skills for your AI
newlife init 2026-09-05-my-question
```

That scaffolds `questions/2026-09-05-my-question/` and **commits it while
deliberately leaving `prereg.md` uncommitted**. The freeze has to be that file's
first commit, and the natural habit — `git add -A` right after creating a folder
— destroys that irreversibly.

```bash
$EDITOR questions/2026-09-05-my-question/goal.md      # is this worth asking? six anchors
$EDITOR questions/2026-09-05-my-question/prereg.md    # the criteria
newlife freeze questions/2026-09-05-my-question       # ← this commit is the proof
$EDITOR questions/2026-09-05-my-question/verdict.py   # your world
newlife run   questions/2026-09-05-my-question
newlife check questions/2026-09-05-my-question       # four gates, see below
git add questions/2026-09-05-my-question/results && git commit -m "verdict"
newlife audit questions/2026-09-05-my-question
```

`goal.md` is scaffolded **deliberately red**, and `newlife freeze` refuses until you
fill in its six anchors — did you search the literature, who would bet the other way,
is the counterparty attacking the conclusion or the premise, is the answer settled by
the design or by the run, who changes their behaviour, how big is this. Every one of
them covers a step that **leaves no trace when skipped**: skip the runner and there is
no `summary.json`, but skip the literature search and nothing is missing at all. If the
stage genuinely does not apply, one anchor waives it — explicitly, on the record. The
freeze is where this is enforced rather than `check`, because `check` also needs
`results/` and so cannot run until the work is already done.

`check` runs four gates against **your own files**: the same goal-readiness check,
reported here for completeness; a scan for criteria that are
true by construction (a comprehension that iterates a named constant while
discarding the loop variable — that is a repetition, not a sweep); a scan for
parse-failures that silently fall back to a convenient default; and an alignment
check that the units your `prereg.md` declares are exactly the units your runner
computes. That last one caught a real misalignment the first time it ran on a real
question folder: the registration said `verdict = S0 ∧ S1 ∧ S2 ∧ S3` while the
runner had folded S3 into a sub-field of S2, so the conjunction was one unit weaker
than it looked.

The other gates in this repository — `verify_doc_claims`, `mutation_scan`,
`run_gates` — are **not** shipped: they assume a separate document pipeline (a
verification-script ledger, a goal/question/ledger triple). That is attribution, not
omission.

`audit` proves four things from git alone: the registration has a freeze commit,
the stamped hash matches it, the content was never edited afterwards, and **every
committed output post-dates the freeze**. That last one needs the registration and
the results to share a git ancestry, which is why they live in one repository, one
folder per question. Questions are siblings, not a chain: **a question's verdict
never runs another question's runner.**

The generated `verdict.py` already carries what every question needs identically —
provenance (which build of newlife by source digest, not the version string; which
environment by lockfile hash), the self-reproduction check, and the slot where each
criterion proves it can fail. Replace the placeholder model with your own.

> **What the first four real questions produced** — one toolchain smoke run, two honestly
> recorded `INVALID`s, and one `H1` reproducing Rosenfeld–Elowitz–Alon (2002) with a blind
> prediction that held — is written up in
> [`docs/product/2026-09-04-first-user-questions.md`](docs/product/2026-09-04-first-user-questions.md).
> The first of them also surfaced a silent defect in this library that four milestones with
> third-party code had missed, because all four happened to use the same timestep.

> **Why "proves it can fail" is a required slot**: this project shipped a negative
> control that was true by construction and nobody noticed for a whole milestone.
> See [`docs/worlds/019-yield-input-or-outcome.md`](docs/worlds/019-yield-input-or-outcome.md) §6.

## Writing your own world

`newlife blocks` lists every `Process`/`Step` installed in your environment — 59 of them
in a default install with the `spatio-flux` extra. If one of them is your model, wire it up
directly. If your simulator is not a process-bigraph `Process` (most are not — tellurium,
COPASI, your own code), wrap it in about twenty lines:

```python
from process_bigraph import Process

class TelluriumODE(Process):
    """Run an Antimony model for `interval`, return the species deltas."""
    config_schema = {"model": "string", "species": "list[string]"}

    def initialize(self, config=None):
        import tellurium as te
        self.rr = te.loada(self.config["model"])
        self.names = list(self.config["species"])

    def inputs(self):  return {"species": "map[float]"}
    def outputs(self): return {"species": "map[float]"}

    def update(self, state, interval):
        for name in self.names:
            self.rr[name] = float(state["species"][name])
        self.rr.resetSelectionLists()
        self.rr.simulate(0.0, float(interval), 2)
        return {"species": {n: float(self.rr[n]) - float(state["species"][n])
                            for n in self.names}}
```

Then declare **what it is allowed to write**, and build the composite:

```python
profile = BiologicalProfile()
profile.register_mechanism(MechanismSpec(
    identity="grn", version="tellurium-2.2.13.1", plane="biological",
    biological_role="gene-regulation", ports=("state",),
    claims=(StateClaim(("species",), "own"),),          # ← the authority declaration
    schedule={"stage": "growth"}, rng_streams=(),
    allowed_effects=frozenset({"StateDelta"}), invariants=()), "grn")

composite = build_composite(
    "my_module:TelluriumODE", identity="grn",
    bindings=(PortBinding("species", ("species",), "add"),),
    lowering={("StateDelta", ("species",)): ("species", "sum-map-add")},
    config={"model": MODEL, "species": ["P"]},
    state_roots={"species": {"P": 0.0}},
    in_wiring={"species": ["species"]}, out_wiring={"species": ["species"]},
    contract=True, interval=DT)                          # ← see the warning below
```

Writing anywhere you did not claim raises `newlife.core.errors.CommitAuthorityError` —
**from the contract layer, not from your solver**. That distinction matters: "an exception
was raised" is not the same as "the contract stopped it", and a criterion that conflates
them proves nothing.

> **`interval` is not optional in practice.** It is the process's *own* timestep. If the
> duration you pass to `run_composite` is not a positive integer multiple of it,
> process-bigraph accumulates the requests and fires far fewer times than you asked —
> this used to happen **silently**, producing plausible-looking numbers (251 sample points
> carrying 5 distinct values, final 0.9817 against an analytic 0.9933). `run_composite`
> now hard-fails on the mismatch instead.

## Quickstart (contributing to newlife itself)

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/). Nothing else is
needed for the trust core:

```bash
uv sync --package proofroot
uv run --package proofroot pytest packages/proofroot/tests -q
```

`newlife` itself needs the pinned upstream runtime, which lives behind an
optional extra (the narrow-dependency rule of §5.1 — vendor types never reach
the core, and packaging enforces it):

```bash
uv sync --package newlife --extra process-bigraph
uv run --package newlife pytest packages/newlife/tests -q
python3 scripts/check_imports.py                               # import-lint
```

**The `--extra process-bigraph` is not optional in practice.** Five test
modules import `bigraph_schema` unconditionally; without the extra, pytest
fails at collection with `ModuleNotFoundError: No module named
'bigraph_schema'`.

Reproduce the second world (Hudson's `ms` minimal coalescent) end to end —
this compiles the vendored `ms` sources itself, so it needs a C compiler
(`cc`) and nothing more:

```bash
uv run --package newlife python -m newlife.conform.second_world_verdict --output /tmp/second-world
```

It prints the verdict bundle and exits non-zero if the verdict does not hold.
Expected: `"passed": true`, `"verdict": "ms_minimal_coalescent_reproducible"`,
30 replicates.

The first world (Resource Foraging) is the one reproduction that **cannot** be
run from this repository alone: its L2 recorded-draw comparison replays draws
recorded by the Julia reference implementation, so it additionally needs Julia
and a local [ParaLife](https://github.com/hzshen88/paralife) `parworlds`
checkout. See [`examples/first-world/README.md`](examples/first-world/) for the
commands and `--parworlds` path.

Release maintainers should follow [`docs/releasing.md`](docs/releasing.md). A tagged
release builds and validates both distributions before publishing them through PyPI
Trusted Publishing; no long-lived upload token is stored in GitHub.

## Repository map

| Path | What it holds |
|---|---|
| `packages/` | The two libraries (table above). |
| `docs/design/proposal.md` | The living build plan: architecture, design decisions, milestones, risks. Read §1.5 (pain-point ballast) and §8 (risks) before proposing any new construction. |
| `docs/worlds/` | One document per world question — why this world, what the frozen known answer is, which comparison tier applies. |
| `examples/` | Application layer, **data only**. `import-lint` enforces zero Python files here: assembling existing mechanisms is configuration, not code. |
| `scripts/` | Gate acceptance runners and the import-lint CI check. |
| `results/` | One directory per closed milestone, holding the machine-computed verdict bundle. `passed` is always computed from a conjunction, never hand-written. |
| `vendor/` | Third-party reference oracles, vendored verbatim and pinned by SHA-256 (currently Hudson's `ms`). |

## How a milestone gets accepted

Every milestone in this repository goes through the same pipeline, and the
order is the discipline — not a formality:

```
goal → question → plan → preregistration (frozen) → implementation → verdict runner → results bundle
```

- **goal** — what this work is meant to buy, stated against the pain-point
  list in `proposal.md` §1.5, *before* the question narrows. It is checked
  again at the end, and it is allowed — and has already happened — for a
  milestone to reach a supported hypothesis while its goal went backwards.
- **question / plan / preregistration** live in the
  [exloop](https://github.com/hzshen88/exloop) exploration archive under
  `docs/science-superpowers/`, and are frozen with `prereg.sh freeze` before
  any implementation code is written.
- **verdict runner** computes the verdict mechanically from the frozen
  criteria. `results/*/summary.json` is its output, never an edited file.

The two failure modes this ordering exists to prevent are both on record in
§8: freezing criteria after seeing results, and building for a user who does
not exist yet.

## Status

Fifteen milestones are decided, each against criteria frozen before the
implementation existed. Every verdict below is computed by a runner from the
frozen conjunction, not asserted by hand:

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
| Is yield an input or an outcome? | **H1** — `MonodKinetics` and `DynamicFBA` are interchangeable at the same port and **share the same uptake law**; sweeping the oxygen bound, dFBA secretes acetate and its yield drops (textbook overflow metabolism) while Monod's yield stays exactly its declared constant. **Matching one point is not representing the degree of freedom** — though the negative control that was supposed to show this (Z5) was later found to be **vacuously true** (a `for _ in SWEEP` that discards the loop variable; the flaw is in the frozen preregistration, not the implementation). **H1 stands and the artifact is not overwritten** — the conclusion follows arithmetically from Z3 (dFBA's yield varies by 56.2% across the sweep) and Z4 (Monod's is constant). See [`docs/worlds/019-yield-input-or-outcome.md`](docs/worlds/019-yield-input-or-outcome.md) §6. First end-to-end run using only off-the-shelf blocks: **221 lines total, 0 new world code** | `results/nineteenth/summary.json` |

World 4 is the first world with **no external program as a comparison target
anywhere** — it checks against mathematics the project derives and verifies
itself. It is also the first time pain point P1 (cross-world mechanism
composability) advanced: World 2's observer is reused **unmodified through the
registry**, judged by object identity rather than an import list. The goal
records that as `achieved` in its narrow, pre-frozen sense — **P1 moved off
zero**, not "P1 solved".

Recorded as honestly as the successes: World 2 was the second consecutive world
to bypass `staging.py` and P1 went slightly backwards there; World 4 bypasses it
a **fourth** consecutive time, and its reuse works only because the consumer
accommodates World 2's namespace (`TREE_PATH` stays `second_world/tree`) — that
composition is not clean. Both costs were pre-declared before execution. See
`docs/design/proposal.md` §7 and `docs/worlds/004-moran-genealogy.md`. That is
what the goal step exists to surface.

**The discipline is that criteria freeze first and code follows.** See
`docs/design/proposal.md` (§7 schedule) and
[the originating exploration](https://github.com/hzshen88/exloop) for the full
evidence chain: a frozen, pre-registered dual-implementation pressure test
(66/66 checks, 0-warning audit) established that Process-Bigraph is a viable
composition runtime *only with* a mandatory, independently versioned
biological profile — which is what this repository builds.

## Lineage

- **ParaLife** (Julia monorepo, first generation): evidence discipline carried
  by repository governance (ADR sign-off, frozen run bindings, architecture
  gates). newlife is the second generation: the same discipline enforced at
  runtime, plus the mechanism composition ParaLife deliberately omitted.
- `EvidenceCore.jl` stays frozen in ParaLife as the **oracle** that generates
  proofroot's cross-language test vectors; ParaLife is not migrated.
- Upstream runtime: [process-bigraph](https://github.com/vivarium-collective/process-bigraph)
  and [bigraph-schema](https://github.com/vivarium-collective/bigraph-schema)
  (Apache-2.0), pinned `==1.8.3` / `==1.6.0`, confined to the adapter layer.

## License

Apache-2.0. Upstream notices are preserved per the Apache-2.0 requirements;
see `docs/design/proposal.md` §6.
