"""R2 — RNG-bank seed mapping: how a coalescent-world `stream_factory`
consumes an already-derived seed. Consumption-side only; does not touch
proofroot's `derive_stream_seed` itself.

`drand48`'s native `seed48()` wants three `unsigned short` (48 bits total,
big-endian by word). proofroot's `derive_stream_seed` returns a UInt64. The
mapping masks the derived seed to its low 48 bits and splits it into three
16-bit words — a lossy truncation (discards the derived seed's top 16
bits), not a new derivation algorithm.
"""

from __future__ import annotations

_U48_MASK = (1 << 48) - 1
_U16_MASK = 0xFFFF


def derived_seed_to_ms_triple(seed: int) -> tuple[int, int, int]:
    """R2's ruling: `seedv[0] = seed & 0xFFFF`, `seedv[1] = (seed>>16) &
    0xFFFF`, `seedv[2] = (seed>>32) & 0xFFFF`, applied to the low 48 bits of
    `seed`. The top 16 bits of `seed` are discarded."""
    low48 = seed & _U48_MASK
    return (
        low48 & _U16_MASK,
        (low48 >> 16) & _U16_MASK,
        (low48 >> 32) & _U16_MASK,
    )


def pack_ms_triple(seedv: tuple[int, int, int]) -> int:
    """Reassemble a triple in R2's own word order: `seedv[0] | seedv[1]<<16
    | seedv[2]<<32`. The inverse of `derived_seed_to_ms_triple`'s low-48-bit
    half — also how Task 2 packs a *literal* `-seeds` triple (not a derived
    one) into the single integer `stream_factory` expects."""
    w0, w1, w2 = seedv
    return w0 | (w1 << 16) | (w2 << 32)
