"""Regression checks for the English-only installed user surface."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from newlife import cli
from newlife.gates import silent_degradation_scan

HAN = re.compile(r"[\u3400-\u9fff]")
PUBLIC_MODULES = (
    "adapters/process_bigraph/bare_control.py",
    "adapters/process_bigraph/derive.py",
    "adapters/process_bigraph/world_runtime.py",
    "adapters/process_bigraph/wrapper.py",
    "adapters/reference_kernel/world_runtime.py",
    "core/harness.py",
    "core/runtime.py",
    "core/verdict_seam.py",
    "gates/__init__.py",
)



def test_public_docstrings_are_english() -> None:
    package = Path(cli.__file__).resolve().parent
    offenders: list[str] = []
    for relative in PUBLIC_MODULES:
        path = package / relative
        tree = ast.parse(path.read_text(encoding="utf-8"))
        objects = [("module", tree)] + [
            (node.name, node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        ]
        for name, node in objects:
            docstring = ast.get_docstring(node, clean=False)
            if docstring and HAN.search(docstring):
                offenders.append(f"{relative}:{name}")
    assert offenders == []


@pytest.mark.parametrize("entrypoint", [cli.main, silent_degradation_scan.main])
def test_public_help_is_plain_english(entrypoint, capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        entrypoint(["--help"])
    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert not HAN.search(output)
    assert "**" not in output
