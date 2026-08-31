"""Checksum guard for the vendored `ms` oracle (vendor/ms/).

Mirrors the v0.1a pattern for the vendored canonical ruler
(`test_ruler.py`): a byte drift in a vendored third-party oracle must fail
loudly, not silently change what a downstream comparison is measured
against. These SHA-256 values are provisional until the second-world
preregistration (question doc:
`docs/science-superpowers/questions/2026-08-31-newlife-second-world-ms-coalescent-declarability.md`)
pins its own frozen data checksums — at that point this test should be
updated to import the frozen values rather than restate them.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

VENDOR_ROOT = Path(__file__).resolve().parents[1] / ".." / ".." / "vendor" / "ms"

FROZEN_MS_SHA256 = {
    "ms.c": "9bb5da6755b56a719966176504485499e5feb3442a0875c09020e25cdfe25622",
    "streec.c": "7574be71072ccdcbada67862987a4b89beb0c7ea8fdd977d07da9f34434c9cb4",
    "rand1.c": "70bd8a05a74e97340341cd45cef7b36b046b74f8c2d47564df6c18d7daf6bbfa",
    "ms.h": "7e22f96d48788b598d8d798753ea104955ecc7baa051fd05eb84601e5e603c98",
}


def test_vendored_ms_sources_are_byte_identical_to_the_pinned_fetch():
    for name, digest in FROZEN_MS_SHA256.items():
        path = (VENDOR_ROOT / name).resolve()
        assert path.is_file(), f"vendored ms source missing: {path}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
