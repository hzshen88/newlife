"""Adapt ``ReferenceKernel`` to the generic runtime contract."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.core.contracts import Effect, MechanismSpec


class ReferenceKernelRuntime:
    """Reference implementation of the ``WorldRuntime`` protocol."""

    def __init__(self, state_roots: Mapping[str, Any]) -> None:
        self.kernel = ReferenceKernel(dict(state_roots))

    def register_mechanism(self, spec: MechanismSpec) -> None:
        self.kernel.register_mechanism(spec)

    def guarded_read(
        self, source_id: str, callback: Callable[[Mapping[tuple[str, ...], Any]], Any]
    ) -> Any:
        return self.kernel.guarded_read_fast(source_id, callback)

    def apply_batch(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        self.kernel.apply_batch_fast(source_id, list(effects), list(trace_records))
