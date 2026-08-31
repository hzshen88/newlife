"""Import-boundary lint for the newlife monorepo.

Rules (proposal v0.6 §5.1 / §4):
1. proofroot and newlife.core must have ZERO third-party imports
   (stdlib only). The zero-dependency promise is enforced here, not by trust.
2. `process_bigraph` / `bigraph_schema` may ONLY be imported inside
   packages/newlife/src/newlife/adapters/process_bigraph/ — vendor types
   never leak past the adapter layer.
3. newlife may import proofroot; proofroot imports nothing but stdlib.
4. (v0.3 compare prereg R6) newlife.core must not import newlife.mechanisms
   or newlife.adapters — core stays domain-free even though rule 1's
   zero-third-party check alone would not catch an intra-newlife leak.

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


def imported_full_modules(path: Path) -> list[tuple[str, int]]:
    """Return (full dotted module path, lineno) for every import in a file —
    unlike imported_roots, this keeps 'newlife.mechanisms' distinct from
    'newlife.core' rather than collapsing both to 'newlife'."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append((node.module, node.lineno))
    return modules


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

# R4.7 (v0.1b preregistration): orchestration is compiled by staging.py —
# the case path may not construct Composite directly, negatives included.
# No exemptions: an exemption would be a hole.
for py in sorted((NEWLIFE_SRC / "adapters" / "process_bigraph").glob("cases.py")):
    if "Composite(" in py.read_text(encoding="utf-8"):
        violations.append(
            f"{py}: manual Composite construction in the case path (rule R4.7)"
        )

# v0.2 gate (proposal §2 goal 5): the application layer is configuration
# data — any Python under examples/ is a runtime-code violation.
examples_dir = ROOT / "examples"
if examples_dir.is_dir():
    for py in sorted(examples_dir.rglob("*.py")):
        violations.append(
            f"{py}: runtime code in the application layer (rule v0.2-gate)"
        )

# R6 (v0.3 compare prereg): core stays domain-free — it may not import
# newlife.mechanisms or newlife.adapters, even though rule 1's zero-third-
# party check alone would not catch that intra-newlife leak.
CORE_DIR = NEWLIFE_SRC / "core"
FORBIDDEN_CORE_PREFIXES = ("newlife.mechanisms", "newlife.adapters")

for py in sorted(CORE_DIR.rglob("*.py")):
    for module, lineno in imported_full_modules(py):
        if any(
            module == prefix or module.startswith(prefix + ".")
            for prefix in FORBIDDEN_CORE_PREFIXES
        ):
            violations.append(
                f"{py}:{lineno}: newlife.core must not import '{module}' (rule R6)"
            )

for src_dir in (PROOFROOT_SRC, NEWLIFE_SRC):
    for py in sorted(src_dir.rglob("*.py")):
        for module, lineno in imported_roots(py):
            if is_stdlib(module):
                continue
            if module == "proofroot":
                if src_dir == PROOFROOT_SRC:
                    violations.append(
                        f"{py}:{lineno}: proofroot must not import itself"
                    )
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
