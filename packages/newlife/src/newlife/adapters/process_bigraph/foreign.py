"""Admit a **third-party process-bigraph `Process`** into newlife's contract.

A third-party `Process` has no notion of an Effect: its `update()` **returns an engine
update directly**. newlife's contract requires every write to originate from an `Effect`
declared by a registered mechanism, validated by `BiologicalProfile.stage`. A translation
layer sits between the two.

**How**: `GuardedProcess.update` is already the three steps propose -> stage -> lower, with
validation in `stage`. So only `propose` is implemented here — the third party's output
**can only** reach a store through `stage`; the adapter never waves it through and never
returns an engine update itself.

**The third party's source is not modified**: it is *instantiated and called* here, not
subclassed and overridden. Its ports (`inputs()`/`outputs()`) are **asked of it** rather
than restated by us.

## The weak point of this layer, stated where it cannot be missed

The `PortBinding` table **can only be written by us**, and two pieces of information in it
are things the third party simply does not provide:

- **which state path a port corresponds to** — `outputs()` gives a type (`'float'`), never
  a location
- **whether a write is `add` or `set`** — a process returning an increment cannot say so in
  its signature, and getting it wrong (`set` where `add` was meant) overwrites the quantity
  with the increment **while still producing results that run**

FMI solves this by having the interface description shipped by the model author alongside
the implementation. There is no such thing here. So what this layer establishes is that
**the contract has force over a declaration written on the third party's behalf** — *not*
that a third party can be admitted with no hand-written declaration at all.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
from typing import Any, Mapping, Sequence

from process_bigraph import Composite, Process, allocate_core

from newlife.adapters.process_bigraph.wrapper import GuardedProcess, Proposal
from newlife.core.contracts import OPERATIONS, StateDelta
from newlife.core.errors import SpecValidationError


@dataclasses.dataclass(frozen=True, slots=True)
class PortBinding:
    """One third-party output port -> one newlife state path and write operator.

    **This is us speaking on the third party's behalf.** It is an assertion, not a fact
    read off the third party.
    """

    port: str
    path: tuple[str, ...]
    operation: str

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise SpecValidationError(
                f"unknown write operator {self.operation!r}; the vocabulary is closed: "
                f"{sorted(OPERATIONS)}"
            )


def admit(
    foreign_cls: type[Process],
    bindings: Sequence[PortBinding],
    lowering: Mapping[str, tuple[str, str]],
) -> type[GuardedProcess]:
    """Build a `GuardedProcess` subclass admitting `foreign_cls` into the contract."""
    bound = tuple(bindings)
    by_port = {b.port: b for b in bound}
    if len(by_port) != len(bound):
        raise SpecValidationError("the same port was declared twice")

    class _Admitted(GuardedProcess):
        # Merge the third party's config keys so pb can pass them down via node config
        config_schema = {
            "mechanism_id": "string",
            **dict(getattr(foreign_cls, "config_schema", {})),
        }
        lowering_table = dict(lowering)

        def __init__(self, config=None, core=None) -> None:
            super().__init__(config, core)
            foreign_keys = getattr(foreign_cls, "config_schema", {})
            self._foreign = foreign_cls(
                {k: self.config[k] for k in foreign_keys if k in self.config}, core
            )

        # Ports are asked of the third party, never restated by us
        def inputs(self) -> Any:
            return self._foreign.inputs()

        def outputs(self) -> Any:
            return self._foreign.outputs()

        def propose(self, state: dict[str, Any], interval: float) -> Proposal:
            raw = self._foreign.update(state, interval)
            if not isinstance(raw, Mapping):
                raise SpecValidationError(
                    f"{foreign_cls.__name__}.update returned {type(raw).__name__}; this "
                    "adapter accepts only a mapping keyed by port name"
                )
            effects = []
            for port, value in raw.items():
                binding = by_port.get(port)
                if binding is None:
                    # The third party wrote a port we never declared for it —
                    # **hard-fail**. Dropping it silently would make its write vanish
                    # with nobody the wiser.
                    raise SpecValidationError(
                        f"{foreign_cls.__name__} wrote the undeclared port {port!r}; "
                        f"declared ports are {sorted(by_port)}"
                    )
                effects.append(StateDelta(binding.path, binding.operation, value))
            return Proposal(effects=tuple(effects))

    _Admitted.__name__ = f"Admitted_{foreign_cls.__name__}"
    _Admitted.__doc__ = (
        f"{foreign_cls.__module__}.{foreign_cls.__name__} admitted through newlife's contract."
    )
    return _Admitted


def _wire(value: Any) -> Any:
    """One wiring: a whole port to one path, or **per key** to different stores.

    Added when a third-party `DynamicFBA` wired its `substrates` port as
    `{mol_id: path}`, one entry per substrate. **This was the third layer of one pit**:
    first "one wiring table is enough", then splitting it into separate read and write
    tables, and finally discovering that the *values* in the table are not of one shape
    either.
    """
    if isinstance(value, Mapping):
        return {k: list(v) for k, v in value.items()}
    return list(value)


def resolve_foreign(dotted: str) -> type[Process]:
    """Resolve a third-party class from a dotted path.

    **The string is data** — which keeps the declaring side free of vendor imports.
    """
    module_path, attr = dotted.split(":")
    return getattr(importlib.import_module(module_path), attr)


def build_composite(
    foreign_dotted: str,
    *,
    identity: str,
    bindings: Sequence[PortBinding],
    lowering: Mapping[str, tuple[str, str]],
    config: Mapping[str, Any],
    state_roots: Mapping[str, Any],
    in_wiring: Mapping[str, list[str]],
    out_wiring: Mapping[str, list[str]],
    contract: bool,
    register_types: Any = None,
    interval: float = 1.0,
) -> Composite:
    """Build a composite running a third-party process.

    With `contract=False` the **bare third-party class** is used, bypassing the contract —
    that path is exactly what a meta-negative-control needs.

    **Reads and writes are two separate wiring tables**: one table proved insufficient
    once a process read its `substrates` port from `local` and wrote it to `exchange`. The
    first process admitted read and wrote the same path, so a single table looked adequate.
    **It looks right with one provider and collapses with two.**
    """
    foreign_cls = resolve_foreign(foreign_dotted)
    cls = admit(foreign_cls, bindings, lowering) if contract else foreign_cls
    core = allocate_core()
    if register_types is not None:
        # A type vocabulary delivered by the third party (in the ontology literature, a
        # vocabulary is the interface contract between independent components).
        # **This half is not written on their behalf** — the first process admitted here
        # did not provide even this.
        register_types(core)
    core.register_link(identity, cls)
    node_config = dict(config)
    if contract:
        node_config["mechanism_id"] = identity
    state: dict[str, Any] = {
        # A top-level value need not be a mapping — one process had a scalar `mass`
        **copy.deepcopy(dict(state_roots)),
        "node": {
            "_type": "process",
            "address": f"local:{identity}",
            "config": node_config,
            "inputs": {k: _wire(v) for k, v in in_wiring.items()},
            "outputs": {k: _wire(v) for k, v in out_wiring.items()},
            # **This is the process's own timestep**, not the duration the caller passes
            # to `run_composite`. When the two disagree, pb accumulates the requests and
            # fires far fewer times, **making no sound at all** — the first real user
            # question was caught by exactly this: advancing by 0.02 against a hardcoded
            # 1.0 gave 251 sample points carrying 5 distinct values, and the numbers still
            # looked entirely plausible (0.98 against an analytic 0.99).
            "interval": interval,
        },
    }
    composite = Composite({"state": state}, core=core)
    composite.newlife_interval = float(interval)   # for run_composite to check against
    return composite


def third_party_types(dotted: str):
    """Resolve a type-registration entry point delivered by a third party.

    **The dotted path is data** — which keeps the judging side free of vendor imports.

    In the ontology literature a **vocabulary is the interface contract between
    independent components**, and here that entry point comes from the third party itself
    (`spatio_flux:register_types`). The first process admitted did not provide even this.
    """
    module_path, attr = dotted.split(":")
    return getattr(importlib.import_module(module_path), attr)
