"""What the registered store types actually do when an update arrives.

These are **measurements, not documentation**. A lowering handler names the shape of the
update it produces; whether that update replaces or accumulates is decided by the port's
registered type, and the two are never checked against each other. `list-direct` said
"overwrite" in a comment for as long as it existed, while a `list` port appends — a
process returning its whole state through one doubles that state every tick with nothing
raising. These tests pin the semantics so the mismatch cannot come back unnoticed.

Found by admitting a real local checkout (a hexagonal-grid simulator returning its whole
ownership array) into a contracted world: the run succeeded, the contract passed, and the
array silently grew from 1526 entries to 3052.
"""

from __future__ import annotations

import pytest
from bigraph_schema.methods import apply
from newlife.adapters.process_bigraph.derive import allocate_probe_core


@pytest.fixture(scope="module")
def registry():
    core = allocate_probe_core("process_bigraph:register_types")
    return core.registry.registry if hasattr(core.registry, "registry") else core.registry


def test_list_store_appends(registry) -> None:
    """`list` accumulates. A whole-state return through such a port grows without bound."""
    result, _ = apply(registry["list"](), [1, 2], [9], [])
    assert result == [1, 2, 9]


@pytest.mark.parametrize("type_name", ["overwrite", "object", "tree"])
def test_replacing_types_replace(registry, type_name: str) -> None:
    """These replace, and are what a port carrying a whole new value needs."""
    result, _ = apply(registry[type_name](), [1, 2], [9], [])
    assert result == [9]


def test_list_and_overwrite_disagree(registry) -> None:
    """The point of the pair: the same update, two registered types, two outcomes.

    Choosing between them is a modelling decision that no current check makes for you.
    """
    appended, _ = apply(registry["list"](), [1, 2], [9], [])
    replaced, _ = apply(registry["overwrite"](), [1, 2], [9], [])
    assert appended != replaced
