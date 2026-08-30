"""D1 named RNG stream seed derivation + D4 bank semantics (port of
EvidenceCore.jl's `derive_stream_seed` and `RngBank`, current encoding only).

Discipline (docs/design/proposal.md §5.10): the `evidencecore-rng-v1` encoding
is ported byte-for-byte — Python output must match the Julia oracle bit-for-bit
(`vectors/evidencecore_rng_v1.json`). The three legacy encodings
(`parcells-rng-v1`, `parreact-rng-v1`, `parworlds-rng-v1`) are deliberately NOT
ported: their reason to exist is exact reproduction of historical ParaLife runs.

Charter boundary: the cross-language contract ends at the derived seed. Random
*sequences* depend on the host generator (Julia's Xoshiro; Python consumers
choose their own), so `RngBank` takes an injectable `stream_factory` instead of
hardcoding a generator. The bank invariants below are generator-independent.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

EVIDENCECORE_RNG_V1 = "evidencecore-rng-v1"

_UINT64_MASK = (1 << 64) - 1
# Guards reproducibility: an invalid or colliding name would silently change
# the derived seed. Matched against the name as declared, before lowercasing —
# same as the oracle.
_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


class RngDerivationError(ValueError):
    """Raised for unknown derivation versions (D1) or invalid bank inputs (D4)."""


def derive_stream_seed(version: str, root_seed: int, name: str) -> int:
    """Derive a per-stream seed from the root seed and a stable stream name.

    Declaration order and other streams' consumption cannot change a given
    stream. Only the current encoding is supported; anything else raises
    (legacy encodings live in ParaLife's EvidenceCore.jl, not here).
    """
    if version != EVIDENCECORE_RNG_V1:
        raise RngDerivationError(f"unknown rng derivation version: {version!r}")
    if not 0 <= root_seed <= _UINT64_MASK:
        raise RngDerivationError(f"root seed out of UInt64 range: {root_seed!r}")

    payload = bytearray()
    payload += b"parworlds-rng-v1"  # fixed encoding tag, byte-identical to the
    payload += b"\x00"  # parworlds form; the version argument is NOT spliced in
    payload += (root_seed & _UINT64_MASK).to_bytes(8, "little")
    payload += b"\x00"
    payload += name.encode("utf-8")

    digest = hashlib.sha256(bytes(payload)).digest()
    return int.from_bytes(digest[:8], "little")


class RngBank:
    """A bank of named RNG streams (D4 semantics, ported from EvidenceCore.jl).

    Invariants ported from the oracle:

    - streams are *declared* at construction; consuming an undeclared name is
      an error, never a silent new stream;
    - access keys are lowercased, so declaration order is case-insensitive at
      lookup (declared names must already match ``^[a-z][a-z0-9_-]*$``);
    - ``rng_stream`` returns the *same cached object* every call: consuming a
      stream advances it, it is never re-seeded (forward-only);
    - ``stream_seeds()`` snapshots the derived seeds — the provenance product
      (e.g. rng_streams.toml) that must hash identically across builds;
    - a derived-seed collision across declared streams is a construction error.

    ``stream_factory`` maps each derived seed to a stateful stream object (the
    host generator choice; proofroot does not standardize one). It must be
    injective enough that each stream gets its own object. Pass ``None`` to
    track seeds only.
    """

    def __init__(
        self,
        root_seed: int,
        names: list[str],
        rng_strategy: str = EVIDENCECORE_RNG_V1,
        stream_factory: Callable[[int], Any] | None = None,
    ) -> None:
        if not 0 <= root_seed <= _UINT64_MASK:
            raise RngDerivationError("root seed must fit in UInt64")
        if not names:
            raise RngDerivationError("an RNG bank requires at least one stream")
        if len(set(names)) != len(names):
            raise RngDerivationError("RNG stream names must be unique")
        for name in names:
            if not _NAME_RE.match(name):
                raise RngDerivationError(f"invalid RNG stream name: {name}")

        self.root_seed = root_seed
        self.rng_strategy = rng_strategy
        self._stream_seeds: dict[str, int] = {}
        self._streams: dict[str, Any] = {}
        for name in names:
            key = name.lower()
            seed = derive_stream_seed(rng_strategy, root_seed, key)
            self._stream_seeds[key] = seed
            if stream_factory is not None:
                self._streams[key] = stream_factory(seed)
        if len(set(self._stream_seeds.values())) != len(self._stream_seeds):
            raise RngDerivationError("derived RNG stream seed collision")

    def stream_seeds(self) -> dict[str, int]:
        """Snapshot of the derived per-stream seeds (the provenance product)."""
        return dict(self._stream_seeds)

    def rng_stream(self, name: str) -> Any:
        """Return the cached stream for ``name`` (case-insensitive lookup).

        The same object is returned on every call, so consuming it advances
        the stream rather than re-seeding it.
        """
        key = name.lower()
        if key not in self._streams:
            raise RngDerivationError(f"undeclared RNG stream {key!r}")
        return self._streams[key]
