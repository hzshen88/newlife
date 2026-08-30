"""Draw-stream abstraction for the Resource Foraging world.

The charter boundary (proofroot): the cross-language contract ends at the
derived seed; random *sequences* are the host generator's choice. The world
consumes streams through this interface, with two bindings:

- Dev streams: a seeded Python generator per derived seed (deterministic per
  stream) — for development and invariant tests, never for cross-language
  claims. Built on proofroot's RngBank with a stream factory.
- Recorded streams: replay a recorded Julia draw log (typed records: scalar
  float64 draws as 16-hex bit patterns, element picks as the chosen element,
  UInt64 draws, shuffles as permutations) — the L2 injection method. The
  bank is name-addressed: each stream's log comes from the Julia recorder
  for the same world seed.

Consumption order is strict: a record of the wrong kind, an exhausted log,
or a pick outside the offered options raises DrawLogMismatch.
"""

from __future__ import annotations

import json
import random
import struct
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class DrawLogMismatch(ValueError):
    """The recorded draw log disagrees with the consumption site."""


class DevStream:
    """Host-choice generator seeded by the derived stream seed."""

    def __init__(self, derived_seed: int) -> None:
        self._rng = random.Random(derived_seed)

    def draw_float(self) -> float:
        return self._rng.random()

    def pick(self, options: Sequence) -> Any:
        return options[self._rng.randrange(len(options))]

    def draw_u64(self) -> int:
        return self._rng.getrandbits(64)

    def permutation(self, items: Sequence) -> list:
        shuffled = list(items)
        self._rng.shuffle(shuffled)
        return shuffled


class RecordedStream:
    """Replays a recorded Julia draw log in strict consumption order."""

    def __init__(self, records: Iterable[Mapping[str, Any]]) -> None:
        self._records = list(records)
        self._cursor = 0

    def _next(self, kind: str) -> Mapping[str, Any]:
        if self._cursor >= len(self._records):
            raise DrawLogMismatch(
                f"recorded draw log exhausted at entry {self._cursor}"
            )
        record = self._records[self._cursor]
        self._cursor += 1
        if record["k"] != kind:
            raise DrawLogMismatch(
                f"draw #{self._cursor - 1}: expected {kind!r}, log has {record['k']!r}"
            )
        return record

    def draw_float(self) -> float:
        bits = self._next("f")["v"]
        return struct.unpack(">d", bytes.fromhex(bits))[0]

    def pick(self, options: Sequence) -> Any:
        value = self._next("p")["v"]
        if value not in options:
            raise DrawLogMismatch(
                f"recorded pick {value!r} not among options {list(options)!r}"
            )
        return value

    def draw_u64(self) -> int:
        return int(self._next("u64")["v"], 16)

    def permutation(self, items: Sequence) -> list:
        permuted = self._next("perm")["v"]
        # JSON round-trips tuples as lists — compare element-wise.
        if sorted(map(list, permuted)) != sorted(map(list, items)):
            raise DrawLogMismatch("recorded permutation is not a permutation of the items")
        return [list(position) for position in permuted]

    def remaining(self) -> int:
        return len(self._records) - self._cursor


class RecordedBank:
    """Name-addressed bank of recorded streams (one world seed's recording)."""

    def __init__(self, root_seed: int, logs: Mapping[str, Iterable[Mapping[str, Any]]]) -> None:
        self.root_seed = root_seed
        self._streams = {name: RecordedStream(records) for name, records in logs.items()}

    def rng_stream(self, name: str) -> RecordedStream:
        if name not in self._streams:
            raise KeyError(f"no recorded log for stream {name!r}")
        return self._streams[name]


def load_stream_log(path: Path | str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_recorded_bank(
    root_seed: int, log_dir: Path | str
) -> RecordedBank:
    """Load a recorded bank from <log_dir>/<stream>.jsonl for all six streams."""
    from newlife.mechanisms.resource_foraging.model import RNG_STREAM_NAMES

    directory = Path(log_dir)
    logs = {
        name: load_stream_log(directory / f"{name}.jsonl") for name in RNG_STREAM_NAMES
    }
    return RecordedBank(root_seed, logs)
