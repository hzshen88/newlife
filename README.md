# newlife

A verifiable profile layer for composable biological simulation: path authority,
effect validation, single-path lowering, and canonical evidence traces — the
scientific semantics a bare composition runtime does not provide.

| Package | Scope | Depends on |
|---|---|---|
| [`packages/proofroot`](packages/proofroot/) | Language-neutral trust core: named RNG stream derivation, run phases, evidence tiers, canonical serialization spec + cross-language vectors. Zero dependencies, zero domain semantics. | — |
| [`packages/newlife`](packages/newlife/) | BiologicalProfile: the four contracts (StateClaim / MechanismSpec / Effect / Resolver), path authority, read-only alias guard, single-path lowering, canonical traces. | proofroot |

## Quickstart

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/). Nothing else is
needed for the trust core:

```bash
uv sync --package proofroot
uv run --package proofroot pytest packages/proofroot/tests -q   # 121 passed
```

`newlife` itself needs the pinned upstream runtime, which lives behind an
optional extra (the narrow-dependency rule of §5.1 — vendor types never reach
the core, and packaging enforces it):

```bash
uv sync --package newlife --extra process-bigraph
uv run --package newlife pytest packages/newlife/tests -q      # 174 passed
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
