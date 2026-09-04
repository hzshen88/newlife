"""The minimal execution-backend contract required by ``GenericWorld``.

The seam exposes mechanism registration, guarded reads, and atomic batch
application. Backend-specific implementation distinctions stay behind it.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Protocol, runtime_checkable

from newlife.core.contracts import Effect, MechanismSpec


@runtime_checkable
class StageResult(Protocol):
    """The effects and trace records returned by one completed stage."""

    effects: Iterable[Effect]
    records: Iterable[Mapping[str, Any]]


@runtime_checkable
class WorldRuntime(Protocol):
    """Execution backend created from a mapping of state roots."""

    def register_mechanism(self, spec: MechanismSpec) -> None:
        """Register one mechanism declaration with this runtime."""
        ...

    def guarded_read(
        self, source_id: str, callback: Callable[[Mapping[tuple[str, ...], Any]], Any]
    ) -> Any:
        """Call ``callback`` with the read-only view authorized for ``source_id``."""
        ...

    def apply_batch(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        """Atomically apply effects and trace records, rejecting the whole unauthorized batch."""
        ...


RuntimeFactory = Callable[[Mapping[str, Any]], WorldRuntime]
"""Factory type accepted by the harness instead of a concrete backend class."""
