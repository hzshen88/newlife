"""第三世界：带选择的 Moran 过程（biological 平面的步进规则）。

判据冻结于 `exloop` 的预注册
`docs/science-superpowers/preregistrations/2026-09-02-newlife-third-world-moran-selection-declarability.md`
（freeze commit `aa052dd`）。本模块只实现该预注册冻结的东西。

**M1（预注册 §6）：本模块不得 import oracle 的阈值函数。** claim (i) 要检验的正是
「两个独立实现是否逐值一致」；若 mechanism 与 oracle 共用一份阈值代码，claim (i) 就
退化成「实现 vs 它自己」，恒真。所以这里从 question 的**规格**实现，不从它的代码：
只有一致性测试（`tests/third_world/`）才允许同时 import 两边做对账。

三条规格约定，逐条写明而不是留给读者推断：

- **阈值用字面浮点运算序列**：`i*r/(i*r+(N-i))` 是三次独立舍入的浮点运算（乘、加、
  除），**不是**先化简成精确分数再除一次。两者在 `r=5/3` 的某些 `(N,i)` 上差 1 ULP，
  question 的第三轮红队为此改过一次。
- **事件极性**：第二个 draw **永远**对「死者是 A」的阈值 `i/N` 比较，绝不另算一个
  「死者是 a」的阈值——后者在有限网格上是另一个被独立舍入的数。
- **with-replacement**：繁殖者与死者独立抽取，重合即空步；`steps` 计入空步
  （预注册 §3，两种口径差 2.55 倍）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class DrawStream(Protocol):
    """本模块只需要一个 `[0,1)` 均匀浮点源。"""

    def next(self) -> float: ...


@dataclass(frozen=True, slots=True)
class StepRecord:
    """一步的完整记录。字段顺序即消耗顺序（M2）。

    `draw1` 是**第一个被消耗**的 draw，不是「用于繁殖者的那个」。两者在正确实现下
    恰好相同，但记录语义必须是前者：按角色贴标签会让「抽签顺序互换」这类 bug 对
    oracle 重放完全不可见（预注册 §6 的 M2，实测 245,760/245,760 全部逃逸）。
    """

    pre_state: int
    draw1: float
    draw2: float
    post_state: int


def reproducer_is_A_threshold(n_pop: int, r: float, i: int) -> float:
    """繁殖者为 A 的概率阈值，按真实代码会做的字面浮点序列计算。

    `i * r` → 乘；`i * r + (n_pop - i)` → 加；再除。三次独立舍入。
    """
    numerator = i * r
    denominator = i * r + (n_pop - i)
    return numerator / denominator


def dier_is_A_threshold(n_pop: int, i: int) -> float:
    """死者为 A 的概率阈值 `i/N`。第二个 draw 永远对它比较（事件极性）。"""
    return i / n_pop


def moran_step(n_pop: int, r: float, i: int, draws: DrawStream) -> StepRecord:
    """一步 Moran：消耗两个 draw，返回含消耗顺序的记录。

    繁殖者为 A 且死者为 a → i+1；繁殖者为 a 且死者为 A → i−1；其余（含两者同型、
    以及繁殖者与死者是同一个体的等效情形）为空步，`i` 不变。
    """
    draw1 = draws.next()
    draw2 = draws.next()
    reproducer_is_A = draw1 < reproducer_is_A_threshold(n_pop, r, i)
    dier_is_A = draw2 < dier_is_A_threshold(n_pop, i)

    post = i
    if reproducer_is_A and not dier_is_A:
        post = i + 1
    elif not reproducer_is_A and dier_is_A:
        post = i - 1
    return StepRecord(pre_state=i, draw1=draw1, draw2=draw2, post_state=post)


def run_replicate(
    n_pop: int, r: float, i0: int, draws: DrawStream, step_cap: int
) -> tuple[list[StepRecord], int, int]:
    """跑一个 replicate 到吸收或撞上限，返回 `(records, final_state, steps)`。

    `steps` **计入空步**（M6）：步数上限 227 是在这个口径下导出的，换成「只数状态
    改变的步」会变成 89，相差 2.55 倍，会把正确实现判成删失。
    """
    records: list[StepRecord] = []
    i = i0
    steps = 0
    while 0 < i < n_pop and steps < step_cap:
        steps += 1
        record = moran_step(n_pop, r, i, draws)
        records.append(record)
        i = record.post_state
    return records, i, steps
