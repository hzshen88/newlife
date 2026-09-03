"""第十五个里程碑：接第三方 process 的契约边界。

判定本身在 `conform/foreign_process_verdict.py`（预注册 `8d65582`）。这里锁住
判定之后补上的那道守卫——**store handler 假定的算符必须被校验**。
"""

from __future__ import annotations

import pytest

from newlife.adapters.process_bigraph.foreign import PortBinding
from newlife.core.errors import SpecValidationError
from newlife.mechanisms.foreign_growth import declaration as D


def test_mis_declared_operation_hard_fails():
    """把代写的算符从 add 填成 set，必须硬失败。

    修复前它**产出完全相同的轨迹、没有任何东西报警**——而这张声明表正是接第三方
    时由我们代写的，最容易填错也最没人复核。
    """
    from newlife.conform.foreign_process_verdict import _admitted_trajectory

    wrong = (PortBinding("mass", D.MASS_PATH, "set"),)
    with pytest.raises(SpecValidationError, match="假定算符"):
        _admitted_trajectory(D.SPEC, wrong)


def test_correct_declaration_still_runs():
    """正控：守卫不能把正确的声明也挡住。"""
    from newlife.conform.foreign_process_verdict import _admitted_trajectory

    traj = _admitted_trajectory(D.SPEC, D.BINDINGS)
    assert traj[0] == 1.0 and traj[-1] > traj[0]


def test_unbound_port_hard_fails():
    """第三方写了一个我们没为它声明的端口 → 硬失败，不静默丢弃。"""
    from newlife.conform.foreign_process_verdict import _admitted_trajectory

    with pytest.raises(SpecValidationError, match="未声明的端口"):
        _admitted_trajectory(D.SPEC, (PortBinding("other", D.MASS_PATH, "add"),))
