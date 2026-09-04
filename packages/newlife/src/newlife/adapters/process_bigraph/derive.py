"""Derive authority declarations from third-party wiring and type behavior.

Input paths become read claims, output paths become ownership claims, and a
behavioral probe distinguishes additive from replacing store semantics.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence

from newlife.core.contracts import StateClaim
from newlife.core.errors import SpecValidationError

PROBE_STATE = 1.0
PROBE_UPDATE = 0.5


def unwrap(value: Any) -> Any:
    """Remove a third-party schema wrapper while preserving plain values."""
    if isinstance(value, Mapping) and "_default" in value and "_type" in value:
        return value["_default"]
    return value


def process_nodes(tree: Any, address_suffix: str) -> Iterator[Mapping[str, Any]]:
    """Yield process or step nodes whose address ends with ``address_suffix``."""
    if isinstance(tree, Mapping):
        node = unwrap(tree)
        if isinstance(node, Mapping) and node.get("_type") in {"process", "step"}:
            address = unwrap(node.get("address"))
            if isinstance(address, str) and address.endswith(address_suffix):
                yield node
        for value in (node.values() if isinstance(node, Mapping) else ()):
            yield from process_nodes(value, address_suffix)
    elif isinstance(tree, (list, tuple)):
        for item in tree:
            yield from process_nodes(item, address_suffix)


def config_of(node: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the first configuration mapping from a third-party node."""
    value = unwrap(node.get("config", {}))
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (list, tuple)):
        for item in value:
            item = unwrap(item)
            if isinstance(item, Mapping):
                return dict(item)
    return {}


def wiring_of(node: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract unwrapped input and output wiring from a process node."""
    return dict(unwrap(node.get("inputs", {}))), dict(unwrap(node.get("outputs", {})))


def common_prefix(paths: Sequence[tuple[str, ...]]) -> tuple[str, ...]:
    """Return the longest common prefix of a sequence of paths."""
    if not paths:
        return ()
    prefix = paths[0]
    for path in paths[1:]:
        cut = 0
        while cut < min(len(prefix), len(path)) and prefix[cut] == path[cut]:
            cut += 1
        prefix = prefix[:cut]
    return prefix


def paths_in(wiring: Mapping[str, Any]) -> set[tuple[str, ...]]:
    """Return the claimable path for each port in a wiring declaration.

    Keyed wiring collapses to its longest common path prefix because the
    adapter emits one ``StateDelta`` per port.
    """
    found: set[tuple[str, ...]] = set()
    for value in wiring.values():
        value = unwrap(value)
        if isinstance(value, Mapping):
            found.add(common_prefix([tuple(p) for p in value.values()]))
        else:
            found.add(tuple(value))
    return found


def derive_claims(
    in_wiring: Mapping[str, Any], out_wiring: Mapping[str, Any]
) -> tuple[StateClaim, ...]:
    """Derive read claims from inputs and ownership claims from outputs."""
    owned = paths_in(out_wiring)
    read_only = paths_in(in_wiring) - owned
    return tuple(
        sorted(
            [StateClaim(p, "own") for p in owned]
            + [StateClaim(p, "read") for p in read_only],
            key=lambda c: (c.path, c.permission),
        )
    )


def element_type(type_expr: Any) -> str:
    """Return the element type of one container layer, or the scalar type itself."""
    text = str(unwrap(type_expr))
    if "[" in text and text.endswith("]"):
        return text[text.index("[") + 1 : -1].strip()
    return text.strip()


def probe_operation(core: Any, type_expr: Any) -> str:
    """Probe whether a store type adds an update or replaces the current value."""
    from bigraph_schema.methods import apply  # noqa: PLC0415

    name = element_type(type_expr)
    registry = core.registry.registry if hasattr(core.registry, "registry") else core.registry
    schema_cls = registry.get(name)
    if schema_cls is None:
        raise SpecValidationError(f"cannot probe unregistered store type {name!r}")
    result, _ = apply(schema_cls(), PROBE_STATE, PROBE_UPDATE, [])
    if result == PROBE_STATE + PROBE_UPDATE:
        return "add"
    if result == PROBE_UPDATE:
        return "set"
    raise SpecValidationError(
        f"store type {name!r} is neither additive nor replacing "
        f"({PROBE_STATE} + {PROBE_UPDATE} produced {result}); refusing to guess"
    )


def derive_operations(core: Any, outputs: Mapping[str, Any]) -> dict[str, str]:
    """Derive each output port's operation from its declared third-party type."""
    return {port: probe_operation(core, expr) for port, expr in outputs.items()}


ALLOWED_EFFECTS = frozenset({"StateDelta"})
"""这条接入路径上，第三方的输出只可能降级成 `StateDelta`——结构性事实，不是选择。

`admit()` 把引擎 update 的**每一个端口条目**翻成一条 `StateDelta`；
第三方没有别的出口（Event / StructuralRewrite / Transfer / Contribution 都进不来）。
"""


def derive_spec(
    core: Any,
    node: Mapping[str, Any],
    outputs_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive claims, effects, operations, and wiring for a third-party process node."""
    in_wiring, out_wiring = wiring_of(node)
    return {
        "claims": derive_claims(in_wiring, out_wiring),
        "allowed_effects": ALLOWED_EFFECTS,
        "operations": derive_operations(core, outputs_schema),
        "in_wiring": in_wiring,
        "out_wiring": out_wiring,
    }


def probe_selftest(core: Any) -> dict[str, str]:
    """Self-test that the probe distinguishes additive and replacing store types."""
    from bigraph_schema.methods import apply  # noqa: PLC0415
    from spatio_flux.types.positive import PositiveFloat, SetFloat  # noqa: PLC0415

    registry = core.registry.registry if hasattr(core.registry, "registry") else core.registry
    out: dict[str, str] = {}
    for cls in (PositiveFloat, SetFloat):
        name = next((k for k, v in registry.items() if v is cls), None)
        if name is not None:
            out[cls.__name__] = probe_operation(core, name)
            continue
        result, _ = apply(cls(), PROBE_STATE, PROBE_UPDATE, [])
        out[cls.__name__] = (
            "add" if result == PROBE_STATE + PROBE_UPDATE
            else "set" if result == PROBE_UPDATE else "?"
        )
    return out


def allocate_probe_core(register_types_dotted: str) -> Any:
    """Allocate a core with the requested third-party type registry installed."""
    from process_bigraph import allocate_core  # noqa: PLC0415

    from newlife.adapters.process_bigraph.foreign import third_party_types  # noqa: PLC0415

    core = allocate_core()
    third_party_types(register_types_dotted)(core)
    return core


def outputs_declared_by(cls: Any, config: Mapping[str, Any], core: Any) -> tuple[dict, str]:
    """Read output types from an instance, falling back to the class declaration."""
    try:
        return dict(cls(dict(config), core).outputs()), "instantiated"
    except Exception:  # noqa: BLE001 —— 退路本身是产物里要交代的事实
        return dict(cls.outputs(cls.__new__(cls))), "declared_only"
