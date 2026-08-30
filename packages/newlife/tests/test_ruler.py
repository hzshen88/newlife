"""R1 vendored-ruler checksum, frozen-fixture integrity, anti-masking probes.

The checksum test proves the vendored ruler is byte-identical to the frozen
pressure-test `normalize.py` (SHA-256 pinned in the v0.1a preregistration);
the anti-masking probes prove the ruler bites: damaging a trace in each of
the four frozen ways must remain detectably unequal.
"""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

from newlife.conform.contract import canonical_ruler
from newlife.conform.fixtures import (
    EXPECTED_ROOT,
    FROZEN_FIXTURE_SHA256,
    EXPECTED_FIXTURE_NAMES,
    fixture_hashes,
    load_fixture,
)
from newlife.conform.contract.canonical_ruler import (
    canonical_bytes,
    canonical_state,
    canonical_trace,
)

# Frozen v0.1a preregistration R1: vendored verbatim, byte-for-byte.
FROZEN_RULER_SHA256 = "f987aa761c66c963a886d229de90405c6978b249367eedc217d9ce6229da5604"


def test_vendored_ruler_is_byte_identical_to_frozen_source():
    digest = hashlib.sha256(
        Path(canonical_ruler.__file__).resolve().read_bytes()
    ).hexdigest()
    assert digest == FROZEN_RULER_SHA256


def test_vendored_ruler_is_the_only_canonicalizer_imported_by_the_verdict():
    # The verdict code imports only the vendored ruler (R1); guard against a
    # second canonicalization path (e.g. the proofroot spec) leaking in.
    assert "newlife.core.canonical" not in sys.modules
    assert canonical_ruler.__name__.endswith("canonical_ruler")


@pytest.mark.parametrize("name", EXPECTED_FIXTURE_NAMES)
def test_frozen_fixture_checksums_match_preregistration(name):
    assert fixture_hashes()[name] == FROZEN_FIXTURE_SHA256[name]
    assert (EXPECTED_ROOT / name).is_file()


def test_normalizer_applies_exactly_the_three_frozen_operations():
    state = {
        "z": 1.25,
        "global_time": 9.0,
        "nested": {"global_time": 2.5, "b": 2, "a": 1},
        "__runtime__": {"hidden": True},
    }
    assert canonical_state(state) == {
        "nested": {"a": 1, "b": 2, "global_time": "2.5"},
        "z": "1.25",
    }
    assert canonical_bytes({"b": 1, "a": 2}) == b'{"a":2,"b":1}'


def test_anti_masking_missing_mechanism_identity_remains_unequal():
    expected = load_fixture("execution_budget.json")["expected_trace"]
    damaged = copy.deepcopy(expected)
    del damaged[2]["source"]
    assert canonical_trace(damaged) != canonical_trace(expected)


def test_anti_masking_missing_contribution_remains_unequal():
    expected = load_fixture("coupled_mechanics_division.json")["expected_trace"]
    damaged = [
        record
        for record in copy.deepcopy(expected)
        if record.get("source") != "Repulsion"
    ]
    assert canonical_trace(damaged) != canonical_trace(expected)


def test_anti_masking_omitted_rejection_remains_unequal():
    expected = load_fixture("hook_authority.json")["negative_cases"]
    damaged = copy.deepcopy(expected[:-1])
    assert canonical_bytes(damaged) != canonical_bytes(expected)


def test_anti_masking_reordered_biological_event_remains_unequal():
    expected = load_fixture("continuous_next_event.json")["expected_trace"]
    damaged = copy.deepcopy(expected)
    damaged[1], damaged[2] = damaged[2], damaged[1]
    assert canonical_trace(damaged) != canonical_trace(expected)


def test_float_encoding_is_decimal_string_not_host_repr():
    # str(Decimal(str(value))) — e.g. 0.1+0.2 must encode as "0.30000000000000004"
    assert canonical_bytes({"v": 0.1 + 0.2}) == b'{"v":"0.30000000000000004"}'
