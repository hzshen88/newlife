"""Run manifest: the five versions + immutable-input integrity (prereg).

Five versions decide one run's reproducibility (proposal §5.5): profile,
mechanism, engine (lock-pinned), conform contract suite, proofroot. The
installed-source digest algorithm is inherited verbatim from the frozen
2026-08-30 preregistration.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any, Mapping

from newlife.adapters.process_bigraph.wrapper import PROFILE_VERSION
from newlife.conform.fixtures import EXPECTED_FIXTURE_NAMES, EXPECTED_ROOT, sha256_file

CONTRACT_VERSION = "v1"  # Effect taxonomy v1; v0.1a does not extend payloads
CONFORM_SUITE_VERSION = "1.1.0"  # re-derived suite + v0.1b staging negatives
MECHANISM_VERSION = "1.0.0"  # frozen fixture mechanisms
UPSTREAM_COMMITS = {
    "process-bigraph": "40fdb161cfc6d38df5af2571cbf64526549585a1",
    "bigraph-schema": "019a1eb20d86eaef29c6d05c715bbd01d350c983",
}
ENGINE_PACKAGES = ("process-bigraph", "bigraph-schema")


class ManifestValidationError(ValueError):
    """Raised when a required provenance field is absent or inconsistent."""


def source_tree_digest(root: Path) -> str:
    """Exact installed-source algorithm frozen in the 2026-08-30 preregistration:
    regular files, excluding __pycache__ and *.pyc/*.pyo, sorted by POSIX
    relative path, rows '<relative-path>\\0<file-sha256>' joined with '\\n',
    UTF-8, SHA-256."""
    rows: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if not path.is_file():
            continue
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        rows.append(f"{relative.as_posix()}\0{sha256_file(path)}")
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def fixture_hashes(root: Path = EXPECTED_ROOT) -> dict[str, str]:
    return dict(sorted((name, sha256_file(root / name)) for name in EXPECTED_FIXTURE_NAMES))


def _installed_root(module_name: str) -> Path:
    module = __import__(module_name)
    return Path(module.__file__).resolve().parent


def five_versions() -> dict[str, Any]:
    return {
        "profile_version": PROFILE_VERSION,
        "mechanism_version": MECHANISM_VERSION,
        "engine_versions": {
            name: importlib.metadata.version(name.replace("_", "-")) for name in ENGINE_PACKAGES
        },
        "conform_suite_version": CONFORM_SUITE_VERSION,
        "proofroot_version": importlib.metadata.version("proofroot"),
        "contract_version": CONTRACT_VERSION,
    }


def build_manifest() -> dict[str, Any]:
    roots = {name: _installed_root(name.replace("-", "_")) for name in ENGINE_PACKAGES}
    manifest = {
        "schema_version": 1,
        "python": platform.python_version(),
        **five_versions(),
        "upstream_commits": dict(UPSTREAM_COMMITS),
        "expected_fixture_sha256": fixture_hashes(),
        "installed_source_roots": {name: str(path) for name, path in roots.items()},
        "installed_source_sha256_before": {
            name: source_tree_digest(path) for name, path in roots.items()
        },
    }
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "profile_version",
        "mechanism_version",
        "engine_versions",
        "conform_suite_version",
        "proofroot_version",
        "contract_version",
        "upstream_commits",
        "expected_fixture_sha256",
        "installed_source_sha256_before",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ManifestValidationError(f"missing manifest fields: {missing}")
    for package in ENGINE_PACKAGES:
        if package not in manifest["engine_versions"]:
            raise ManifestValidationError(f"missing engine version: {package}")
        if package not in manifest["upstream_commits"]:
            raise ManifestValidationError(f"missing upstream commit: {package}")
        if package not in manifest["installed_source_sha256_before"]:
            raise ManifestValidationError(f"missing installed source hash: {package}")
    if tuple(sorted(manifest["expected_fixture_sha256"])) != EXPECTED_FIXTURE_NAMES:
        raise ManifestValidationError("expected fixture set is not exact")


def canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    validate_manifest(manifest)
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
