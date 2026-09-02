"""IC-3 与 M1–M6 的实现期检查表（预注册 `aa052dd` §6）。

**只有本文件可以同时 import mechanism 与 oracle。** mechanism 自己不许 import
oracle——那会让 claim (i) 退化成「实现 vs 它自己」。这里做的正是两个独立实现的对账。
"""

from __future__ import annotations

import ast
import pathlib
import random
import sys

import pytest

from newlife.mechanisms.third_world import moran

_ORACLE_DIR = (
    pathlib.Path.home()
    / "Projects/exloop/docs/science-superpowers/questions/verification"
)
pytestmark = pytest.mark.skipif(
    not (_ORACLE_DIR / "moran_fixation_check.py").exists(),
    reason="oracle lives in the exloop repo; skipped when it is not checked out",
)
sys.path.insert(0, str(_ORACLE_DIR))

N_POP, I0 = 6, 1
R_VALUES = (0.5, 1.0, 1.5)
STEP_CAP = 227


class _Dev:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def next(self) -> float:
        return self._rng.random()


def _oracle():
    import moran_fixation_check as ora  # noqa: PLC0415

    return ora


# --- M1 ---------------------------------------------------------------------


def test_M1_mechanism_does_not_import_the_oracle():
    """机制模块（及其在 newlife 内的传递依赖）不得 import oracle。

    用 AST 解析真实的 import 图，不是字符串匹配——第一版写成了
    `assert "import" not in src`，那对任何有 `from __future__ import` 的模块都为假，
    是「形状像检查、内容不检验」的典型。
    """
    seen: set[str] = set()
    queue = [pathlib.Path(moran.__file__)]
    imported: set[str] = set()
    root = pathlib.Path(moran.__file__).parents[3]  # .../src/newlife/..

    while queue:
        path = queue.pop()
        if str(path) in seen or not path.exists():
            continue
        seen.add(str(path))
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            imported.update(names)
            # 顺着 newlife 内部依赖继续走，检查传递引用
            for name in names:
                if name.startswith("newlife."):
                    candidate = root / (name.replace(".", "/") + ".py")
                    queue.append(candidate)

    offenders = [
        m for m in imported if "moran_fixation_check" in m or "verification" in m
    ]
    assert not offenders, f"机制传递依赖里出现了 oracle: {offenders}"
    assert imported, "import 图为空——解析失败，这条检查没有真正执行"


def test_M1_the_import_check_would_catch_a_violation(tmp_path):
    """负控：给同样的检查喂一个真的引用了 oracle 的模块，它必须发现。"""
    fake = tmp_path / "violating.py"
    fake.write_text("import moran_fixation_check\n")
    tree = ast.parse(fake.read_text())
    imported = {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    assert any("moran_fixation_check" in m for m in imported)


# --- IC-3：阈值逐位对账 ------------------------------------------------------


def test_IC3_thresholds_match_the_oracle_bit_for_bit():
    """机制独立算出的两个阈值，必须与 oracle 的逐位相同。

    穷尽冻结网格的全部 `(r, i)`：3 × 5 = 15 个组合（question 的 R5 要求穷尽而非抽样）。
    """
    ora = _oracle()
    from fractions import Fraction as F  # noqa: PLC0415

    checked = 0
    for r_float, r_exact in zip(R_VALUES, (F(1, 2), F(1), F(3, 2)), strict=True):
        for i in range(1, N_POP):
            mine = moran.reproducer_is_A_threshold(N_POP, r_float, i)
            theirs = float(ora.repro_A_threshold_literal_float_ops(N_POP, r_exact, i))
            assert mine == theirs, f"r={r_float} i={i}: {mine!r} != {theirs!r}"

            mine_die = moran.dier_is_A_threshold(N_POP, i)
            theirs_die = float(ora.simple_ratio_threshold(i, N_POP))
            assert mine_die == theirs_die, f"r={r_float} i={i} dier"
            checked += 1
    assert checked == 15


def test_IC3_the_two_threshold_algorithms_are_INDISTINGUISHABLE_on_the_frozen_grid():
    """诚实记录 IC-3 在**冻结网格上**的实际覆盖范围。

    question 的第三轮红队区分了两种阈值算法（字面浮点序列 vs 先化简成 Fraction 再除
    一次），差异出现在 `r=5/3`。但冻结网格是 `r ∈ {1/2, 1, 3/2}`——**在这个网格上
    两者给出逐位相同的 float**，实测确认。

    因此：IC-3 的逐位对账在冻结网格上**无法区分这两种算法**，实现用哪个都不改变任何
    可观测量。这不是缺陷，是网格选择的性质；写成断言是为了不让读者以为 IC-3 覆盖了
    这一类。verdict runner 的负控也确认了这一点：把机制换成先化简再除，H1 仍然通过。
    """
    ora = _oracle()
    from fractions import Fraction as F  # noqa: PLC0415

    frozen_diffs = 0
    for r_exact in (F(1, 2), F(1), F(3, 2)):
        for i in range(1, N_POP):
            literal = float(ora.repro_A_threshold_literal_float_ops(N_POP, r_exact, i))
            reduced = float(ora.repro_A_threshold_reduce_then_divide(N_POP, r_exact, i))
            if literal != reduced:
                frozen_diffs += 1
    assert frozen_diffs == 0, "冻结网格上竟出现差异——本测试记录的事实已过时"

    # 网格外确实可区分，所以「两种算法等价」是网格的局部性质，不是普遍事实
    off_grid_diffs = sum(
        1
        for i in range(1, N_POP)
        if float(ora.repro_A_threshold_literal_float_ops(N_POP, F(5, 3), i))
        != float(ora.repro_A_threshold_reduce_then_divide(N_POP, F(5, 3), i))
    )
    assert off_grid_diffs > 0, "连 r=5/3 都无差异——两种算法根本不可区分，规格是空的"


# --- M2：记录语义是消耗顺序，不是角色 -----------------------------------------


def test_M2_record_order_is_consumption_order():
    """`draw1` 必须是第一个被消耗的值，与它扮演什么角色无关。"""
    values = [0.11, 0.22]
    stream = iter(values)

    class _Fixed:
        def next(self) -> float:
            return next(stream)

    record = moran.moran_step(N_POP, 1.5, 3, _Fixed())
    assert (record.draw1, record.draw2) == (0.11, 0.22)


def test_M2_role_swap_changes_outcomes_so_the_order_matters():
    """负控：互换两个 draw 的角色确实会改变结果——所以记录顺序不是无关紧要的约定。"""
    changed = 0
    total = 0
    for r in R_VALUES:
        for i in range(1, N_POP):
            th_repro = moran.reproducer_is_A_threshold(N_POP, r, i)
            th_die = moran.dier_is_A_threshold(N_POP, i)
            for k in range(64):
                u1, u2 = k / 64, (63 - k) / 64
                total += 1
                spec = _post(i, u1, u2, th_repro, th_die)
                swapped = _post(i, u2, u1, th_repro, th_die)
                if spec != swapped:
                    changed += 1
    assert changed > 0, "角色互换若从不改变结果，M2 就无从检验"


def _post(i: int, u1: float, u2: float, th_repro: float, th_die: float) -> int:
    repro_A, dier_A = u1 < th_repro, u2 < th_die
    if repro_A and not dier_A:
        return i + 1
    if not repro_A and dier_A:
        return i - 1
    return i


# --- M3 / M4：provenance 与 parity -------------------------------------------


def test_M3_replay_from_the_seed_reproduces_the_draw_sequence():
    """同一个种子重放，必须得到逐位相同的 draw 序列与轨迹。"""
    a, _, _ = moran.run_replicate(N_POP, 1.5, I0, _Dev(4242), STEP_CAP)
    b, _, _ = moran.run_replicate(N_POP, 1.5, I0, _Dev(4242), STEP_CAP)
    assert [(r.draw1, r.draw2) for r in a] == [(r.draw1, r.draw2) for r in b]
    assert [r.post_state for r in a] == [r.post_state for r in b]


def test_M4_draw_parity_two_draws_per_step():
    """每步恰好消耗两个 draw，计数取自真实消耗而非手推。"""
    consumed = []

    class _Counting:
        def __init__(self, seed: int) -> None:
            self._rng = random.Random(seed)

        def next(self) -> float:
            consumed.append(1)
            return self._rng.random()

    records, _, steps = moran.run_replicate(N_POP, 1.5, I0, _Counting(7), STEP_CAP)
    assert len(consumed) == 2 * steps == 2 * len(records)


# --- M5：轨迹完整性 ----------------------------------------------------------


@pytest.mark.parametrize("r", R_VALUES)
def test_M5_trajectory_integrity(r: float):
    """首步 pre==i₀；pre[t+1]==post[t]；末步吸收或撞上限。"""
    records, final, steps = moran.run_replicate(
        N_POP, r, I0, _Dev(int(r * 100)), STEP_CAP
    )
    assert records[0].pre_state == I0
    for earlier, later in zip(records, records[1:], strict=False):
        assert later.pre_state == earlier.post_state
    assert records[-1].post_state == final
    assert final in (0, N_POP) or steps == STEP_CAP


# --- M6：steps 含空步 --------------------------------------------------------


def test_M6_steps_count_null_steps():
    """`steps` 必须计入空步——227 的上限是在这个口径下导出的。"""
    records, _, steps = moran.run_replicate(N_POP, 1.0, I0, _Dev(99), STEP_CAP)
    assert steps == len(records)
    null_steps = sum(1 for rec in records if rec.post_state == rec.pre_state)
    assert null_steps > 0, "本 replicate 未出现空步，这条检查未被真正行使"
    state_changing = steps - null_steps
    assert steps > state_changing
