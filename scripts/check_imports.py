"""Import-boundary lint for the newlife monorepo.

Rules (proposal v0.6 §5.1 / §4):
1. proofroot and newlife.core must have ZERO third-party imports
   (stdlib only). The zero-dependency promise is enforced here, not by trust.
2. `process_bigraph` / `bigraph_schema` may ONLY be imported inside
   packages/newlife/src/newlife/adapters/process_bigraph/ — vendor types
   never leak past the adapter layer.
3. newlife may import proofroot; proofroot imports nothing but stdlib.

Run: python scripts/check_imports.py   (exit 0 = clean, 1 = violation)
No third-party dependency needed — stdlib ast + pathlib only.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOFROOT_SRC = ROOT / "packages" / "proofroot" / "src" / "proofroot"
NEWLIFE_SRC = ROOT / "packages" / "newlife" / "src" / "newlife"
ADAPTER_PB = NEWLIFE_SRC / "adapters" / "process_bigraph"

VENDOR_MODULES = {"process_bigraph", "bigraph_schema"}


def imported_roots(path: Path) -> list[tuple[str, int]]:
    """Return (top-level module name, lineno) for every import in a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append((node.module.split(".")[0], node.lineno))
    return roots


def is_stdlib(module: str) -> bool:
    return module in sys.stdlib_module_names


violations: list[str] = []

# R4.2 (v0.1a preregistration): no ADAPTER file may reference the removed
# bypass field — not even in comments/docstrings, so the free-form update
# channel cannot quietly grow back. (conform/ probes reference the name to
# assert its absence; they are the checker, not the checked surface.)
BANNED_IDENTIFIERS = {"engine_update"}
ADAPTER_DIR = NEWLIFE_SRC / "adapters"

for py in sorted(ADAPTER_DIR.rglob("*.py")):
    source = py.read_text(encoding="utf-8")
    for banned in BANNED_IDENTIFIERS:
        if banned in source:
            violations.append(
                f"{py}: removed bypass identifier {banned!r} referenced (rule R4.2)"
            )

for src_dir in (PROOFROOT_SRC, NEWLIFE_SRC):
    for py in sorted(src_dir.rglob("*.py")):
        for module, lineno in imported_roots(py):
            if is_stdlib(module):
                continue
            if module == "proofroot":
                if src_dir == PROOFROOT_SRC:
                    violations.append(f"{py}:{lineno}: proofroot must not import itself")
                continue
            if module in VENDOR_MODULES:
                if ADAPTER_PB not in py.parents:
                    violations.append(
                        f"{py}:{lineno}: vendor module '{module}' outside "
                        f"adapters/process_bigraph (rule 2)"
                    )
                continue
            if module == "newlife":
                continue
            violations.append(
                f"{py}:{lineno}: third-party import '{module}' in zero-dependency "
                f"zone {src_dir.relative_to(ROOT)} (rule 1)"
            )

if violations:
    print("IMPORT-LINT FAIL")
    for v in violations:
        print(f"  {v}")
    sys.exit(1)

print("import-lint OK: zero-dependency zones clean, vendor imports confined to adapter")
