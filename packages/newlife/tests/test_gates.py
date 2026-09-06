"""随包发布的门 —— 每条自己的负控必须真的红。

**门用来替代人工核对，所以「门对不对」成了新的关键。** 这里只做一件事：
把每条门的 `--selftest` 拉进日常测试里跑。**「能抓住」和「会被跑」是两件事**——
本项目刚栽过一次：六个门单独自检 12/12 全绿，而聚合入口八个门全部打不开文件。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def test_repository_gate_selftest_passes() -> None:
    """仓库级的**元自检**也必须在日常路径里跑——它坏过，而且没人发现。

    `scripts/gates/gate_selftest.py` 把门拷进临时工作区、注入变异、要求每条变异
    都让门变红。它先建立基线：未变异时必须全绿。**2026-09-06 查出这条基线自
    `4d10686` 起就是红的**——那次 skill 改名重构改了自检语料 `corpus/goals/example.md`
    的正文，却没有重算它的 `@frozen` 哈希。

    `@frozen` 机制本身没有失灵，它正是设计来抓这个的、也确实抓住了。塌的是别处：
    基线红被报成「前提不成立」，读起来像环境问题而不是「有东西真的变了」；
    而这个脚本不在 pytest、不在 CI（`workflow_dispatch`），于是**十四条 fixture
    一条都没在守什么，持续了整整一次重构到现在**。

    与本文件开头那条教训同形，只是这次塌的是自检自己：**「门能抓住」和「门会被跑」
    是两件事。** 这个测试就是让第二件也有人守。
    """
    script = Path(__file__).resolve().parents[3] / "scripts/gates/gate_selftest.py"
    if not script.exists():
        pytest.skip("仓库工具不随 wheel 发布；只有在源码树里才跑得到")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                          cwd=script.parents[2])
    assert proc.returncode == 0, (
        "仓库级 gate_selftest 未通过——门的变异检测本身失效了：\n"
        + (proc.stdout or "") + (proc.stderr or ""))
