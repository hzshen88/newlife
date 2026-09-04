"""Regression checks for the English-only installed user surface."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from newlife import cli
from newlife.gates import silent_degradation_scan

HAN = re.compile(r"[\u3400-\u9fff]")
INTERNAL_DIRS = ("conform", "mechanisms")
"""Directories whose docstrings stay in the author's own language.

`conform/` holds this project's own milestone verdict runners and `mechanisms/` its world
implementations — working records, not surface a user of the library ever reads.

**The rule is stated as an exclusion on purpose.** The first version was a hand-written
list of nine included modules, which silently omitted `foreign.py` (the API the README's
"writing your own world" section is built on), `provenance.py`, `cli.py` and all three
gates. They happened to be English already, so the guard passed while covering none of
them. **A hand-written allowlist drifts; an exclusion fails safe** — a new module is
covered from the moment it exists, and leaving it out takes a deliberate edit here.
"""


def _public_modules() -> list[str]:
    package = Path(cli.__file__).resolve().parent
    return sorted(
        str(p.relative_to(package))
        for p in package.rglob("*.py")
        if "__pycache__" not in p.parts and p.relative_to(package).parts[0] not in INTERNAL_DIRS
    )



def test_public_docstrings_are_english() -> None:
    package = Path(cli.__file__).resolve().parent
    offenders: list[str] = []
    for relative in _public_modules():
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
