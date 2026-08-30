"""Canonical serialization spec vectors + rejection rules (§5.9).

The committed vectors ARE the spec's acceptance record: any second
implementation must reproduce `canonical_hex` byte-for-byte and the float
bit patterns exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proofroot import bits_to_float, canonical_bytes, float_to_bits

VECTORS = json.loads(
    (Path(__file__).parent.parent / "vectors" / "canonical_vectors.json").read_text()
)


@pytest.mark.parametrize(
    "case", VECTORS["canonical_bytes"], ids=lambda c: c["name"]
)
def test_canonical_bytes_matches_committed_vectors(case):
    assert canonical_bytes(case["input"]) == bytes.fromhex(case["canonical_hex"])


def test_key_order_is_codepoint_order():
    out = canonical_bytes({"😀": 1, "中": 2, "é": 3, "a": 4, "Z": 5}).decode("utf-8")
    assert out == '{"Z":5,"a":4,"é":3,"中":2,"😀":1}'


def test_output_is_utf8_no_whitespace():
    raw = canonical_bytes({"k": "café", "n": [1, 2]})
    assert b" " not in raw and "\n".encode() not in raw
    assert raw.decode("utf-8") == '{"k":"café","n":[1,2]}'


@pytest.mark.parametrize("case", VECTORS["float_bits"], ids=lambda c: c["decimal"])
def test_float_bits_match_committed_vectors(case):
    assert float_to_bits(bits_to_float(case["bits_hex"])) == case["bits_hex"]


@pytest.mark.parametrize(
    "value,bits",
    [
        (0.0, "0x0000000000000000"),
        (-0.0, "0x8000000000000000"),
        (5e-324, "0x0000000000000001"),
        (float("inf"), "0x7ff0000000000000"),
        (float("nan"), "0x7ff8000000000000"),
    ],
)
def test_known_bit_patterns(value, bits):
    assert float_to_bits(value) == bits


def test_signed_zero_is_distinct_at_byte_level():
    # 0.0 == -0.0 as floats; the spec's whole point is that traces compare the
    # bit patterns, where they differ.
    assert float_to_bits(0.0) != float_to_bits(-0.0)


def test_nan_payload_roundtrips_exactly():
    payload = "0x7ff8000000000001"
    assert float_to_bits(bits_to_float(payload)) == payload


@pytest.mark.parametrize("value", [0.1, -0.0, float("nan"), float("inf")])
def test_raw_float_is_rejected_not_formatted(value):
    # A float reaching the canonicalizer would be formatted by host rules —
    # the exact failure this spec exists to prevent.
    with pytest.raises(TypeError, match="pre-encode comparison fields"):
        canonical_bytes({"x": value})


def test_raw_float_nested_reports_the_key():
    with pytest.raises(TypeError, match="at key 'budget'"):
        canonical_bytes({"a": {"budget": 1.5}})


@pytest.mark.parametrize("value", [3, True, None, "s", [1], {"k": 1}])
def test_float_free_values_pass_through(value):
    canonical_bytes(value)


@pytest.mark.parametrize("value", [{1: "a"}, {None: 1}, set(), (1, 2), b"x"])
def test_non_json_types_rejected(value):
    with pytest.raises(TypeError):
        canonical_bytes(value)


def test_non_string_key_rejected():
    with pytest.raises(TypeError, match="must be strings"):
        canonical_bytes({1: "a"})
