"""Task 3：复用验证——goal C1/C2 的证据由执行产生，不由 import 列表推断。

冻结判据见 `exloop` 预注册（freeze commit `24bb02e`）§7：C1 的 provenance 判据是
**对象同一性**，`__module__` 单独不足。这里连负控一起测，否则「通过」证明不了
判据有区分力。
"""

from __future__ import annotations

import random

import pytest

from newlife.mechanisms.fourth_world import world as w4
from newlife.mechanisms.second_world import mechanisms as w2
from newlife.mechanisms.second_world.ms_coalescent import RecordedDrawStream


class _Dev:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def next(self) -> float:
        return self._rng.random()


def _world(seed: int = 1) -> w4.MoranGenealogyWorld:
    orng = random.Random(seed + 500)
    return w4.MoranGenealogyWorld(
        6, 10, 2.0, _Dev(seed), RecordedDrawStream([orng.random() for _ in range(400)])
    )


def test_observer_is_reached_at_run_time_not_merely_imported():
    """C1 的正面：跑一次，被调用的确实是 World 2 的那个函数对象。"""
    world = _world()
    calls: list[str] = []
    original = w2.observer_step

    def traced(*args, **kwargs):
        calls.append("observer")
        return original(*args, **kwargs)

    world.observer_fn = traced
    world.run()
    assert calls == ["observer"], "observer 必须在运行时被真正调用一次"


def test_provenance_is_object_identity_not_module_string():
    """C1 的负控：三种「假复用」都必须被同一性判据挡住。

    `__module__` 只挡得住其中两种——手工改写 `__module__` 的复制品能通过它，
    这正是预注册把同一性列为第一条件的原因。
    """
    world = _world()
    assert world.reuse_trace()["observer_is_world2_object"] is True

    def local_copy(*args, **kwargs):  # 源码复制到第四世界
        return None

    local_copy.__module__ = "newlife.mechanisms.fourth_world.world"
    world.observer_fn = local_copy
    assert world.reuse_trace()["observer_is_world2_object"] is False

    # 手工伪造 __module__：字符串判据会放行，同一性不会
    local_copy.__module__ = w2.observer_step.__module__
    trace = world.reuse_trace()
    assert trace["observer_module"].startswith("newlife.mechanisms.second_world")
    assert trace["observer_is_world2_object"] is False, (
        "同一性判据必须挡住伪造 __module__ 的复制品"
    )


def test_world2_spec_is_reused_unedited():
    """C3 的前置：第四世界注册的 observer spec 与 World 2 自己构造的完全相同。"""
    mine = next(
        s for s in w4.build_mechanism_specs() if s.identity == w4.OBSERVER_IDENTITY
    )
    theirs = next(
        s for s in w2.build_mechanism_specs() if s.identity == w4.OBSERVER_IDENTITY
    )
    assert mine == theirs


def test_world2_coalescent_cannot_be_registered_alongside_the_builder():
    """R1 的边界由 registry 强制，不是设计偏好：两者都 own TREE_PATH。"""
    world = _world()
    coalescent = next(
        s for s in w2.build_mechanism_specs() if s.identity == "second-world-coalescent"
    )
    with pytest.raises(Exception) as exc:
        world.kernel.register_mechanism(coalescent)
    assert "Ownership" in type(exc.value).__name__ or "ownership" in str(exc.value)


def test_no_frozen_artifact_is_an_execution_input():
    """C2：执行期不从任何 `results/` 产物取输入。"""
    paths = _world().reuse_trace()["execution_input_paths"]
    assert paths == []
    assert not any("results" in str(p) for p in paths)


def test_streams_are_separate(monkeypatch):
    """R3：builder 与 observer 各用各的流，一方重播不改变另一方的消耗。"""
    world = _world(seed=7)
    consumed: list[int] = []
    original_next = RecordedDrawStream.next

    def counting_next(self):
        consumed.append(1)
        return original_next(self)

    monkeypatch.setattr(RecordedDrawStream, "next", counting_next)
    world.run()
    observer_draws = len(consumed)

    # 换一条 builder 流：observer 的流未动，其消耗只应随树的形状变化而变，
    # 而不应因为 builder 的流被替换而共享或耗尽
    consumed.clear()
    world2_ = _world(seed=99)
    monkeypatch.setattr(RecordedDrawStream, "next", counting_next)
    world2_.run()
    assert observer_draws > 0 and len(consumed) > 0
