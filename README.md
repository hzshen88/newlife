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

Five milestones are decided, each against criteria frozen before the
implementation existed. Every verdict below is computed by a runner from the
frozen conjunction, not asserted by hand:

| Milestone | Verdict | Evidence |
|---|---|---|
| v0.1a lowering completeness | H1 supported — `compatible_for_frozen_slices_v1_lowered` | `results/v0.1a/` |
| v0.1b staging declarability | H1 supported — `staging_declarable_for_frozen_slices` | `results/v0.1b/` |
| v0.2 World 1 (Resource Foraging) | gate closed — bit-exact L2 reproduction, both conditions | `results/v0.2/gate.json` |
| v0.3 compare (causal attribution) | H1 supported — `causal_attribution_declarable_for_world1_pairs` | `results/v0.3/summary.json` |
| World 2 (`ms` minimal coalescent) | H1 supported — `ms_minimal_coalescent_reproducible` | `results/second-world/summary.json` |

Recorded as honestly as the successes: World 2 is the **second consecutive
world that bypasses `staging.py`**, and pain point P1 (mechanism
composability) did not advance there — it went slightly backwards. See
`docs/design/proposal.md` §7. That is what the goal step exists to surface.

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
