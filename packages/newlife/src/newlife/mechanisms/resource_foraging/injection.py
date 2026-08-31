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
from collections import deque
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

    def __init__(
        self,
        records: Iterable[Mapping[str, Any]] = (),
        *,
        source: Iterable[Mapping[str, Any]] | None = None,
    ) -> None:
        if source is not None and records:
            raise ValueError("RecordedStream accepts records or source, not both")
        self._records = deque(records)
        self._source = iter(source) if source is not None else None
        self._consumed = 0

    @classmethod
    def from_jsonl(cls, path: Path | str) -> "RecordedStream":
        """Create a bounded-memory stream over the recorder's JSONL file."""

        def records():
            with Path(path).open(encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        yield from json.loads(line)["d"]

        return cls(source=records())

    def _fill(self) -> bool:
        if self._records:
            return True
        if self._source is None:
            return False
        try:
            self._records.append(next(self._source))
        except StopIteration:
            self._source = None
            return False
        return True

    def _next(self, kind: str) -> Mapping[str, Any]:
        if not self._fill():
            raise DrawLogMismatch(
                f"recorded draw log exhausted at entry {self._consumed}"
            )
        record = self._records.popleft()
        cursor = self._consumed
        self._consumed += 1
        if record["k"] != kind:
            raise DrawLogMismatch(
                f"draw #{cursor}: expected {kind!r}, log has {record['k']!r}"
            )
        return record

    def draw_float(self) -> float:
        bits = self._next("f")["v"]
        return struct.unpack(">d", bytes.fromhex(bits))[0]

    def pick(self, options: Sequence) -> Any:
        value = self._next("p")["v"]
        if isinstance(value, list):
            value = tuple(value)  # JSON round-trips tuples as lists
        if value not in options:
            raise DrawLogMismatch(
                f"recorded pick {value!r} not among options {list(options)!r}"
            )
        return value

    def draw_u64(self) -> int:
        return int(self._next("u64")["v"], 16)

    def permutation(self, items: Sequence) -> list:
        permuted = self._next("perm")["v"]
        # JSON round-trips tuples as lists — compare element-wise and return
        # the same element type as the input items.
        normalized = [tuple(position) if isinstance(position, list) else position for position in permuted]
        # The initialization permutation contains (x, y) tuples while the
        # assay permutation contains scalar organism IDs. Both are ordinary
        # permutations; compare their elements without assuming coordinates.
        if sorted(normalized) != sorted(items):
            raise DrawLogMismatch("recorded permutation is not a permutation of the items")
        return normalized

    def remaining(self) -> int:
        # Normally this only advances the file iterator to EOF (one record at
        # a time after the last consumption). If a caller asks early, the
        # unread tail is materialized solely to report the exact count.
        if self._source is not None:
            self._records.extend(self._source)
            self._source = None
        return len(self._records)


class RecordedBank:
    """Name-addressed bank of recorded streams (one world seed's recording)."""

    def __init__(self, root_seed: int, logs: Mapping[str, Iterable[Mapping[str, Any]]]) -> None:
        self.root_seed = root_seed
        self._streams = {
            name: records if isinstance(records, RecordedStream) else RecordedStream(records)
            for name, records in logs.items()
        }

    def rng_stream(self, name: str) -> RecordedStream:
        if name not in self._streams:
            raise KeyError(f"no recorded log for stream {name!r}")
        return self._streams[name]

    def remaining(self) -> dict[str, int]:
        """Return unread entries by stream for an end-to-end L2 audit."""
        return {name: stream.remaining() for name, stream in self._streams.items()}

    def assert_exhausted(self) -> None:
        unread = {name: count for name, count in self.remaining().items() if count}
        if unread:
            raise DrawLogMismatch(f"recorded draw log has unread entries: {unread}")


def load_stream_log(path: Path | str) -> list[dict[str, Any]]:
    """The recorder writes one JSON object per tick: {"t": tick, "d": [draws]}.
    The loader flattens the per-tick draw lists into the strict consumption
    order (the tick envelope is debugging metadata)."""
    records: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.extend(json.loads(line)["d"])
    return records


def load_recorded_bank(
    root_seed: int, log_dir: Path | str
) -> RecordedBank:
    """Load a recorded bank from <log_dir>/<stream>.jsonl. Streams with no
    recorded file (never drawn under this scope) bind an empty log — any
    unexpected consumption raises DrawLogMismatch immediately."""
    from newlife.mechanisms.resource_foraging.model import RNG_STREAM_NAMES

    directory = Path(log_dir)
    logs = {
        name: (
            RecordedStream.from_jsonl(directory / f"{name}.jsonl")
            if (directory / f"{name}.jsonl").exists()
            else RecordedStream()
        )
        for name in RNG_STREAM_NAMES
    }
    return RecordedBank(root_seed, logs)
