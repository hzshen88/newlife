"""M7 在一次真实险情的形状上回放：同一个已知真值，两个估计器，一红一绿。

**险情**：研究仓库里的一次临界指数探索（2026-09-23）。拟注册的判据是 β/ν 落在
Ising 值 1/8 的 ±0.03 之内；读数是「高 1.6 倍」。复核时用**与拟合族不同**的函数族
生成合成数据、输入已知 β/ν = 0.125、跑完同一条分析链 200 次，量出：

| 估计器 | 200 次读数 | 偏差 |
|---|---|---|
| 4 点直线（旧口径） | 0.1575 ± 0.0179 | **+0.0325** |
| 全曲面 | 0.1150 ± 0.0104 | −0.0100 |

旧口径的偏差**大于**它要分辨的 0.03——「效应存在」和「估计器有这个偏」落在同一个
数上。那次是人在复核时自己发现的；这里证明 M7 会**机械地**发现它，并且放过偏差
在效应之内的那一个。

**原始的 200 个读数没有存档**，只记了均值与标准差。所以读数由固定种子生成，再精确
缩放到记录的均值与标准差——回放的是记录下来的那两个数，不是原始数据。
"""

from __future__ import annotations

import random
import statistics

from newlife.gates.judgement_design import calibration_problems

TRUTH = 0.125
EFFECT = 0.03  # 判据草案：β/ν = 0.125 ± 0.03


def _readings(
    mean: float, sd: float, n: int = 200, seed: int = 20260923
) -> list[float]:
    """n 个读数，样本均值与样本标准差**恰好**等于记录值。"""
    rng = random.Random(seed)
    raw = [rng.gauss(0.0, 1.0) for _ in range(n)]
    m, s = statistics.fmean(raw), statistics.stdev(raw)
    return [mean + sd * (x - m) / s for x in raw]


def _design(samples: str) -> dict:
    """只含 M7 所需字段的设计——`calibration_problems` 只读这些。"""
    return {
        "pilot": "results/pilot-samples.json",
        "quantities": [
            {
                "name": "beta_over_nu",
                "effect": {"value": EFFECT, "rationale": "判据草案的容差"},
                "location": {"statistic": "mean", "why": "读数近似正态，无重尾"},
                "calibration": {
                    "truth": TRUTH,
                    "family": "有序侧幂律 + 无序侧指数尾，非拟合族",
                    "samples": samples,
                    "bias_accepted": None,
                },
            }
        ],
    }


def test_readings_reproduce_the_recorded_numbers() -> None:
    old = _readings(0.1575, 0.0179)
    assert abs(statistics.fmean(old) - 0.1575) < 1e-12
    assert abs(statistics.stdev(old) - 0.0179) < 1e-12


def test_the_four_point_line_is_refused() -> None:
    pilot = {"beta_over_nu@line": _readings(0.1575, 0.0179)}
    problems = calibration_problems(_design("beta_over_nu@line"), pilot)
    assert len(problems) == 1
    assert "a bias of 0.0325" in problems[0] and "effect 0.03" in problems[0]


def test_the_full_surface_passes() -> None:
    pilot = {"beta_over_nu@surface": _readings(0.1150, 0.0104)}
    assert calibration_problems(_design("beta_over_nu@surface"), pilot) == []


def test_the_four_point_line_passes_only_on_the_record() -> None:
    design = _design("beta_over_nu@line")
    design["quantities"][0]["calibration"]["bias_accepted"] = "只报告方向，不报告倍数"
    pilot = {"beta_over_nu@line": _readings(0.1575, 0.0179)}
    assert calibration_problems(design, pilot) == []
