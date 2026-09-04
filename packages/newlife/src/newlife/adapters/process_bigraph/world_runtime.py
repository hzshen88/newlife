"""Execute a ``WorldSpec`` through process-bigraph's graph scheduler.

Input and output wiring is derived mechanically from the world's state claims.
"""

from __future__ import annotations

import importlib
from typing import Any, Mapping

from process_bigraph import Composite

from newlife.adapters.process_bigraph.wrapper import (
    BiologicalProfile,
    GuardedStep,
    Proposal,
    allocate_profile_core,
    run_composite,
    step_node,
)
from newlife.core.errors import SpecValidationError
from newlife.core.harness import WorldSpec


def _resolve(dotted: str) -> Any:
    module_path, attr = dotted.split(":")
    return getattr(importlib.import_module(module_path), attr)


def _port(path: tuple[str, ...]) -> str:
    return "__".join(path)


_STORE_TYPE_FOR_EFFECT = {
    "StructuralRewrite": "mapping-direct-structural",
    "Event": "noop",
}
"""Effect 类别 → store handler。**封闭表，缺项硬失败**，不取默认值。

对不上的 Effect 说明这个世界需要 pb 侧一个还不存在的 store 语义——那正是要
如实报出来的东西，不是就近找个 handler 顶上。
"""


def _lowering_table(spec: Any, write_paths: tuple[tuple[str, ...], ...]) -> dict[str, tuple[str, str]]:
    table: dict[str, tuple[str, str]] = {}
    for kind in sorted(spec.allowed_effects):
        store = _STORE_TYPE_FOR_EFFECT.get(kind)
        if store is None:
            raise SpecValidationError(
                f"{spec.identity} declares Effect {kind}, but process-bigraph has no "
                "corresponding store semantics"
            )
        port = _port(write_paths[0]) if store != "noop" else ""
        table[kind] = (port, store)
    return table


def run_world(
    spec: WorldSpec,
    streams: Mapping[str, Any],
    runtime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one replicate and return observations shaped like ``GenericWorld.run()``."""
    runtime = dict(runtime or {})
    profile = BiologicalProfile()
    mechanisms = {m.identity: m for m in _resolve(spec.specs_from)()}

    process_types: list[tuple[str, type]] = []
    nodes: dict[str, Any] = {}

    for stage in spec.stages:
        mech = mechanisms[stage.identity]
        reads = tuple(c.path for c in mech.claims if c.permission == "read")
        writes = tuple(c.path for c in mech.claims if c.permission == "own")

        kwargs = dict(stage.params)
        for name, stream in stage.streams.items():
            kwargs[name] = streams[stream]
        for name, value in runtime.items():
            if name in stage.params or name in stage.streams:
                kwargs[name] = value

        step_fn = _resolve(stage.step)
        cls = _make_stage_class(stage.identity, step_fn, kwargs, reads, writes,
                                _lowering_table(mech, writes))
        process_types.append((stage.identity, cls))
        nodes[f"node__{_port((stage.identity,))}"] = step_node(
            stage.identity,
            stage.identity,
            inputs={_port(pth): list(pth) for pth in reads},
            outputs={_port(pth): list(pth) for pth in writes},
        )

    core = allocate_profile_core(*process_types)
    for stage in spec.stages:
        profile.register_mechanism(mechanisms[stage.identity], stage.identity)

    state = {**{k: dict(v) for k, v in spec.state_roots.items()}, **nodes}
    composite = Composite({"state": state}, core=core)
    run_composite(composite, 1.0, profile)

    trace = profile.take_trace()
    obs = spec.observation
    subject = [r for r in trace if r.get("source") == obs.stage]
    payload = subject[obs.record]["payload"]
    out: dict[str, Any] = {}
    for field in obs.fields:
        value = payload[field]
        out[field] = list(value) if field in obs.list_fields else value
    return out


def _make_stage_class(
    identity: str,
    fn: Any,
    kwargs: Mapping[str, Any],
    reads: tuple[tuple[str, ...], ...],
    writes: tuple[tuple[str, ...], ...],
    table: Mapping[str, tuple[str, str]],
) -> type:
    """Build a ``GuardedStep`` subclass that translates port views back to path views."""
    in_schema = {_port(p): {"_type": "map"} for p in reads}
    out_schema = {_port(p): {"_type": "map"} for p in writes}

    class _Stage(GuardedStep):
        lowering_table = dict(table)

        def inputs(self) -> dict[str, Any]:
            return dict(in_schema)

        def outputs(self) -> dict[str, Any]:
            return dict(out_schema)

        def propose(self, state: dict[str, Any], interval: float) -> Proposal:
            del interval
            view = {p: state[_port(p)] for p in reads}
            result = fn(view, **kwargs)
            return Proposal(
                effects=tuple(result.effects), trace_records=tuple(result.records)
            )

    _Stage.__name__ = f"Stage_{identity.replace('-', '_')}"
    return _Stage
