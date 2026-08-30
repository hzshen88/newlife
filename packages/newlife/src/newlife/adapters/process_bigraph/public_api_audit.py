"""Static audit for the frozen Process-Bigraph extension boundary."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
ADAPTER_FILES = (
    PACKAGE_ROOT / "wrapper.py",
    PACKAGE_ROOT / "lowering.py",
    PACKAGE_ROOT / "cases.py",
)
ALLOWED_PROCESS_BIGRAPH = {"Composite", "Process", "Step", "allocate_core"}
ALLOWED_BIGRAPH_METHODS = {"apply", "reconcile"}
ALLOWED_RUNTIME_ATTRIBUTES = {"process_paths", "register_link", "register_type", "run", "state"}
FORBIDDEN_ATTRIBUTES = {"apply_updates", "front", "process_queue"}
SUPPRESSION_MARKERS = ("# noqa", "# type: ignore", "# public-api-ignore")


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    result: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            result[child] = parent
    return result


def audit_file(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    parents = _parents(tree)
    failures: list[str] = []
    runtime_names: set[str] = set()
    core_names: set[str] = set()

    for marker in SUPPRESSION_MARKERS:
        if marker in source:
            failures.append(f"{path.name}: suppression marker {marker!r}")

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for module in modules:
                if module != "__future__" and any(
                    part.startswith("_") for part in module.split(".")
                ):
                    failures.append(f"{path.name}:{node.lineno}: private module import {module}")
            if isinstance(node, ast.ImportFrom) and node.module == "process_bigraph":
                names = {alias.name for alias in node.names}
                if not names <= ALLOWED_PROCESS_BIGRAPH:
                    failures.append(
                        f"{path.name}:{node.lineno}: unsupported process_bigraph symbols {sorted(names)}"
                    )
            if isinstance(node, ast.ImportFrom) and node.module == "bigraph_schema.methods":
                names = {alias.name for alias in node.names}
                if not names <= ALLOWED_BIGRAPH_METHODS:
                    failures.append(
                        f"{path.name}:{node.lineno}: unsupported bigraph methods {sorted(names)}"
                    )

        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(value, ast.Call):
                call_name = (
                    value.func.id if isinstance(value.func, ast.Name) else None
                )
                for target in targets:
                    if not isinstance(target, ast.Name):
                        continue
                    if call_name == "Composite":
                        runtime_names.add(target.id)
                    if call_name in {"allocate_core", "allocate_profile_core"}:
                        core_names.add(target.id)

        if isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                failures.append(
                    f"{path.name}:{node.lineno}: forbidden runtime attribute {node.attr}"
                )
            if isinstance(node.value, ast.Name) and node.value.id in runtime_names | core_names:
                if node.attr.startswith("_") or node.attr not in ALLOWED_RUNTIME_ATTRIBUTES:
                    failures.append(
                        f"{path.name}:{node.lineno}: non-public runtime attribute {node.attr}"
                    )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"setattr", "delattr"}:
                failures.append(f"{path.name}:{node.lineno}: monkeypatch-like call {node.func.id}")

        if isinstance(node, ast.Constant) and node.value == "_divide":
            parent = parents.get(node)
            if not isinstance(parent, ast.Dict) or node not in parent.keys:
                failures.append(
                    f"{path.name}:{node.lineno}: _divide outside a literal update-data key"
                )

    return failures


def audit_public_surface() -> list[str]:
    failures: list[str] = []
    for path in ADAPTER_FILES:
        failures.extend(audit_file(path))
    return failures


def audit_reference_dispatch() -> list[str]:
    source = (PACKAGE_ROOT.parent / "reference_kernel" / "kernel.py").read_text(encoding="utf-8")
    fixture_names = (
        "execution_budget",
        "coupled_mechanics_division",
        "hook_authority",
        "continuous_next_event",
        "effect_algebra_transfer",
    )
    return [name for name in fixture_names if name in source]
