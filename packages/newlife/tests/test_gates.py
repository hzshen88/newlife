"""随包发布的门 —— 每条自己的负控必须真的红。

**门用来替代人工核对，所以「门对不对」成了新的关键。** 这里只做一件事：
把每条门的 `--selftest` 拉进日常测试里跑。**「能抓住」和「会被跑」是两件事**——
本项目刚栽过一次：六个门单独自检 12/12 全绿，而聚合入口八个门全部打不开文件。
"""

from __future__ import annotations

import subprocess
import sys

import pytest

import newlife.gates
from newlife.gates import unit_alignment


EXEMPT: frozenset[str] = frozenset()
"""`newlife.gates` 下**不**要求带 `--selftest` 的模块。例外写在这里，留在 diff 里。"""


def _gates() -> list:
    """`newlife.gates` 下的每一个模块。**排除式，不是手写清单，也不是属性嗅探。**

    原来这里是一条手写元组，加第四条门（`goal_ready`）时它一声不响地漏掉了——
    与 `test_public_english.py` 的 `PUBLIC_MODULES` 同一个形状（`e8c53a1`）。

    **第一版的修法自己犯了同一个错**：按 `hasattr(module, "_selftest")` 发现，
    而 `silent_degradation_scan` 的那个函数叫 `run_selftest`，于是它被静默漏掉：
    测试数是 8，**本该是 10**，而屏幕上全是绿点、看不出任何异常。
    **属性嗅探是伪装成发现式的白名单。**

    所以按目录枚举，例外显式声明：没有 `--selftest` 的模块会让 argparse 报错
    而变红，逼出一次明确的决定——**不会被悄悄跳过**。
    """
    import importlib
    import pkgutil

    found = [
        importlib.import_module(f"newlife.gates.{info.name}")
        for info in pkgutil.iter_modules(newlife.gates.__path__)
        if info.name not in EXEMPT
    ]
    assert len(found) >= 4, f"只发现 {len(found)} 个门——发现逻辑坏掉的样子恰好是「全绿」"
    return found


GATES = _gates()


@pytest.mark.parametrize("module", GATES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_gate_selftest_passes(module) -> None:
    assert module.main(["--selftest"]) == 0


@pytest.mark.parametrize("module", GATES, ids=lambda m: m.__name__.rsplit(".", 1)[-1])
def test_gate_runs_as_a_standalone_script(module) -> None:
    """**必须保持可单独运行**：newlife 仓库的 `gate_selftest.py` 靠把它们拷进
    临时工作区、变异、再要求变红——那要求它们是 stdlib-only 的独立脚本，
    不是只能 `import` 的模块。"""
    proc = subprocess.run([sys.executable, module.__file__, "--selftest"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_alignment_catches_a_unit_declared_but_never_computed() -> None:
    """预注册写 `verdict = S0 ∧ S1 ∧ S2 ∧ S3`、runner 只算三个 —— **没人会发现**。

    这是走通用户流程时当场犯的错：负控被折进正控的一个子字段，
    于是合取比它看起来的弱了一格。
    """
    declared = {"S0", "S1", "S2", "S3"}
    problems = unit_alignment.check(declared, declared, {"S0", "S1", "S2"})
    assert len(problems) == 1 and "S3" in problems[0]


def test_alignment_distinguishes_empty_parse_from_missing_units() -> None:
    """解析器一个键都没认出来 ≠ 每条判据都没算。

    起草时正则错了一个字符，四条单元全被报成缺失——**诊断把人指向了完全错的地方**。
    """
    declared = {"S0", "S1", "S2"}
    problems = unit_alignment.check(declared, declared, set())
    assert len(problems) == 1 and "no judgement unit parsed" in problems[0]
