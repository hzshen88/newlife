"""判定不确定世界的那把尺 —— 它自己的自检必须被跑。

**今天已经在这件事上栽过一次**：`scripts/gates/gate_selftest.py` 坏了一天多没人发现，
因为它既不在 pytest 也不在 CI。`newlife.stochastic` 不在 `test_gates.py` 的扫描范围里
（那条按目录枚举的是 `newlife.gates`），所以这个文件把它接进日常路径。

**「能抓住」和「会被跑」是两件事**，而这个模块尤其经不起没人跑——它的 selftest 在第一次
运行时就抓到了两个真实缺陷（多重比较未校正、以及一条形状本身就错的 fixture）。
"""

from __future__ import annotations

import random

from newlife.stochastic import equivalence as eq


def test_selftest_passes() -> None:
    assert eq.main(["--selftest"]) == 0


def test_far_apart_samples_are_not_equivalent() -> None:
    """检验必须**能**说「不同」——只会说「相同」的尺子，敏感性方向永远通不过。"""
    rng = random.Random(7)
    a = {"p": [rng.gauss(0.0, 0.5) for _ in range(24)]}
    b = {"p": [rng.gauss(9.0, 0.5) for _ in range(24)]}
    ok, detail = eq.equivalent(a, b, level=eq.LEVEL, resamples=400, seed=eq.SEED)
    assert ok is False
    assert detail["p"]["contains_zero"] is False


def test_degenerate_inputs_raise_instead_of_returning_equivalent() -> None:
    """空组或空扫描点必须抛错。**静默返回「等价」正是恒真判据的形状**——
    本项目为此付过学费（第十九个里程碑的 Z5 恒真负控）。"""
    import pytest
    for a, b in (({"p": []}, {"p": [1.0]}), ({}, {}), ({"p": [1.0]}, {"q": [1.0]})):
        with pytest.raises(ValueError):
            eq.equivalent(a, b, level=eq.LEVEL, resamples=10, seed=eq.SEED)


def test_convergence_refuses_a_sample_too_small_to_split() -> None:
    ok, why = eq.converged({"p": [1.0, 2.0]}, level=eq.LEVEL, resamples=10, seed=eq.SEED)
    # 断言**行为**（拒绝，并说明是样本数问题），不断言措辞——两份独立实现的措辞本就
    # 不必逐字相同，把测试钉在文案上会让它在一次无害的改写里变红。
    assert ok is False
    assert "samples" in why["reason"]
