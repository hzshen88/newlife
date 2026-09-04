# proofroot

Language-neutral trust core for reproducible simulation. Zero dependencies,
zero domain semantics.

## Install and use

Requires Python 3.12 or newer.

```bash
python -m pip install proofroot
```

```python
import random

from proofroot import EVIDENCECORE_RNG_V1, RngBank, canonical_bytes

bank = RngBank(
    root_seed=42,
    names=["mutation", "selection"],
    rng_strategy=EVIDENCECORE_RNG_V1,
    stream_factory=random.Random,
)
mutation_rng = bank.rng_stream("mutation")
print(bank.stream_seeds())
print(mutation_rng.random())
print(canonical_bytes({"answer": 42}))
```

Everything every simulation community needs and none of what any single one
wants to own: named RNG stream seed derivation (`evidencecore-rng-v1`), bank
semantics invariants (declared streams, lowercase normalization, forward-only),
run phases, evidence tier vocabulary (exploration / confirmatory / unknown —
missing fields default to unknown, never to confirmatory), and a canonical
serialization spec (RFC 8785 structural rules; IEEE754 bit-pattern float
comparison) with cross-language test vectors.

**Charter boundary (frozen):** the cross-language contract ends at the derived
seed. Seed derivation is byte-defined over SHA-256 and portable; random
*sequences* depend on the host generator (Julia's Xoshiro, Python's choice)
and are recorded in the run manifest, not standardized.

**Oracle:** `EvidenceCore.jl` in the [ParaLife](https://github.com/hzshen88/paralife)
monorepo is the frozen oracle generating this package's cross-language test
vectors. ParaLife's legacy compatibility layers (legacy encodings, UPPER-CASE
phase spellings) are deliberately **not** ported here.

Design rationale: [proposal §5.10](https://github.com/hzshen88/newlife/blob/main/docs/design/proposal.md).
