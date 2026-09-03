"""Task 3：复用验证——goal C1/C2 的证据由执行产生，不由 import 列表推断。

冻结判据见 `exloop` 预注册（freeze commit `24bb02e`）§7：C1 的 provenance 判据是
**对象同一性**，`__module__` 单独不足。这里连负控一起测，否则「通过」证明不了
判据有区分力。

---

**2026-09-03 移植说明。** 本文件自第八个里程碑（`6bbc05c`）起一直是红的：那次把
World 4 搬上通用 harness，删掉了 `MoranGenealogyWorld`，而这些测试还在引用它。
**红了七个里程碑没人发现**，直到第十四个里程碑顺手跑了一次完整 `pytest`。

移植的是**接法**，不是判据——上面那段冻结判据一个字没动。世界的构造从
`MoranGenealogyWorld(...)` 换成 `GenericWorld(WORLD, ...)`，被替换的函数从
`world.observer_fn` 换成 `world._steps[OBSERVER_IDENTITY]`（通用 harness 在
`__init__` 里把点分路径解析成的那个对象——对象同一性判据盯的正是它）。
"""

from __future__ import annotations

import random

import pytest

from newlife.adapters.reference_kernel.world_runtime import ReferenceKernelRuntime
from newlife.core.harness import GenericWorld
from newlife.mechanisms.fourth_world.spec import OBSERVER_IDENTITY, WORLD
from newlife.mechanisms.fourth_world import world as w4
from newlife.mechanisms.second_world import mechanisms as w2
from newlife.mechanisms.second_world.ms_coalescent import RecordedDrawStream

N_SAMPLE, N_POP, THETA = 6, 10, 2.0


class _Dev:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def next(self) -> float:
        return self._rng.random()


def _world(seed: int = 1) -> GenericWorld:
    orng = random.Random(seed + 500)
    return GenericWorld(
        WORLD,
        streams={
            "builder": _Dev(seed),
            "observer": RecordedDrawStream([orng.random() for _ in range(400)]),
        },
        runtime={
            "n_sample": N_SAMPLE,
            "n_pop": N_POP,
            "nsam": N_SAMPLE,
            "theta": THETA,
            "replicate_index": 0,
        },
        backend=ReferenceKernelRuntime,
    )


def test_observer_is_reached_at_run_time_not_merely_imported():
    """C1 的正面：跑一次，被调用的确实是 World 2 的那个函数对象。"""
    world = _world()
    calls: list[str] = []
    original = w2.observer_step

    def traced(*args, **kwargs):
        calls.append("observer")
        return original(*args, **kwargs)

    world._steps[OBSERVER_IDENTITY] = traced
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
    world._steps[OBSERVER_IDENTITY] = local_copy
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
        s for s in w4.build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
    )
    theirs = next(
        s for s in w2.build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
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
    """R3：builder 与 observer 各用各的流。

    **2026-09-03 加强。** 原断言是 `observer_draws > 0 and len(consumed) > 0`——
    它名字说的是「流分离」，断言的却只是「两次运行都取过 draw」。把两个阶段改成
    共用一条流，它照样绿（变异实测）。**空心断言比红的测试更糟**：它让人以为
    R3 被守着。

    现在的判据：两条流**都**被取用，且 builder 的取用**全部早于** observer 的
    第一次取用、两者不交错。共用一条流时 `_Dev.next` 一次都不会被调，立刻红。
    """
    world = _world(seed=7)
    order: list[str] = []
    dev_next, rec_next = _Dev.next, RecordedDrawStream.next

    def tagged_dev(self):
        order.append("builder")
        return dev_next(self)

    def tagged_rec(self):
        order.append("observer")
        return rec_next(self)

    monkeypatch.setattr(_Dev, "next", tagged_dev)
    monkeypatch.setattr(RecordedDrawStream, "next", tagged_rec)
    world.run()

    assert "builder" in order and "observer" in order, "两条流都必须被真正取用"
    first_observer = order.index("observer")
    assert set(order[:first_observer]) == {"builder"}, "observer 之前只许 builder 取"
    assert set(order[first_observer:]) == {"observer"}, "observer 开始后不许再回到 builder"
