"""R2 mapping-correctness check, isolated from the `ms`-comparison grid
(analysis plan §7 Task 1; round-2 red-team strengthened the assertion —
"pairwise distinct" alone is near-vacuous at this sample size and was
replaced with round-trip reassembly + an observable-lossy-truncation
check, both of which catch the mapping's real failure modes: word-order,
shift, and mask errors).

Never touches `ms` or the frozen grid — this tests the mapping function on
its own terms.
"""

from __future__ import annotations

from newlife.mechanisms.second_world.rng_mapping import (
    derived_seed_to_ms_triple,
    pack_ms_triple,
)
from proofroot import EVIDENCECORE_RNG_V1, derive_stream_seed

_U48_MASK = (1 << 48) - 1

# At least two distinct concrete (version, root_seed, name) inputs relevant
# to this world's eventual declared streams (plan §7 Task 1).
DERIVATION_INPUTS = [
    (EVIDENCECORE_RNG_V1, 1, "second-world-coalescent"),
    (EVIDENCECORE_RNG_V1, 2, "second-world-coalescent"),
    (EVIDENCECORE_RNG_V1, 1, "second-world-mutation"),
]


def test_mapping_of_real_derived_seeds_is_valid_and_round_trips():
    for version, root_seed, name in DERIVATION_INPUTS:
        seed = derive_stream_seed(version, root_seed, name)
        triple = derived_seed_to_ms_triple(seed)

        for word in triple:
            assert 0 <= word <= 0xFFFF, f"{name}: word out of 16-bit range: {word}"

        assert pack_ms_triple(triple) == (seed & _U48_MASK), (
            f"{name}: round-trip reassembly does not reproduce the derived "
            "seed's low 48 bits — word order, shift, or mask error"
        )


def test_truncation_is_observably_lossy():
    """Round-2 fix: construct two UInt64s differing only in their top 16
    bits (bits 48-63) and assert the mapping collapses them to the
    identical triple — the lossy-truncation property made observable,
    not merely described. (Two independently SHA-256-derived seeds almost
    never differ *only* in their top 16 bits by chance, so this property
    is tested with a constructed pair rather than real derived seeds.)"""
    base_seed = derive_stream_seed(EVIDENCECORE_RNG_V1, 1, "second-world-coalescent")
    low_48 = base_seed & _U48_MASK
    seed_a = low_48 | (0x0001 << 48)
    seed_b = low_48 | (0xFFFE << 48)
    assert seed_a != seed_b

    assert derived_seed_to_ms_triple(seed_a) == derived_seed_to_ms_triple(seed_b)
