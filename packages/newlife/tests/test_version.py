"""`newlife --version` —— 用户报问题时要说得清自己装的哪版；此前没有这个开关。"""

from __future__ import annotations

import importlib.metadata

import pytest
from newlife import cli


def test_version_prints_the_installed_distribution_version(capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"newlife {importlib.metadata.version('newlife')}"
