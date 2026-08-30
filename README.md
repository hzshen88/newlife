# newlife

A verifiable profile layer for composable biological simulation: path authority,
effect validation, single-path lowering, and canonical evidence traces — the
scientific semantics a bare composition runtime does not provide.

| Package | Scope | Depends on |
|---|---|---|
| [`packages/proofroot`](packages/proofroot/) | Language-neutral trust core: named RNG stream derivation, run phases, evidence tiers, canonical serialization spec + cross-language vectors. Zero dependencies, zero domain semantics. | — |
| [`packages/newlife`](packages/newlife/) | BiologicalProfile: the four contracts (StateClaim / MechanismSpec / Effect / Resolver), path authority, read-only alias guard, single-path lowering, canonical traces. | proofroot |

## Status

v0.1 pre-registration in progress. **No lowering implementation code is
written before the preregistration freezes** — the discipline of this project
is that criteria freeze first, code follows. See `docs/design/proposal.md`
(§7 schedule) and
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
