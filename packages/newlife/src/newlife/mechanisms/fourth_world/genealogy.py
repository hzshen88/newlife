"""第四世界：中性 Moran 过程的谱系构造（biological 平面）。

判据冻结于 `exloop` 的预注册
`docs/science-superpowers/preregistrations/2026-09-02-newlife-fourth-world-cross-world-mechanism-reuse.md`
（freeze commit `24bb02e`）。本模块只实现该预注册冻结的东西，不多做。

三条冻结约定，写在这里而不是留给读者推断：

- **with-replacement**：繁殖者与死者独立均匀抽取，重合即空步（prereg §3）。
- **时间单位**：一步 = `1/N²`。`ms` 用 `-log(u)/(n(n−1))` 抽等待时间，分母是
  `n(n−1)` 而非 `C(n,2)`，所以 `ms` 的时间单位是 Kingman 标准的一半，`E[tt]`
  = `H_(n−1)`。Moran 每步合并概率为 `k(k−1)/N²`，期望 `N²/(k(k−1))` 步；乘
  `1/N²` 正好得到 `ms` 的 `1/(k(k−1))`。用 `2/N²` 会让树长翻倍。
- **树编码**：`ms` 形状的 `(time, abv)`，叶子 `0..n−1`、内部节点 `n..2n−2`，
  `time[i]` 是节点 i 的合并时刻、`abv[i]` 是父节点索引（prereg §3、plan R11）。

回溯语义（plan R14 的 provenance 之外，这是本世界唯一的建模内容）：死者槽位上的
个体是这一步新生的，其父母在繁殖者槽位，所以往回一步，该谱系位于繁殖者槽位。若
繁殖者槽位已有谱系，二者在上一步是同一条——合并；若没有，谱系只是转移过去，
谱系数不变。
"""

from __future__ import annotations

from typing import Protocol


class DrawStream(Protocol):
    """本模块只需要一个 `[0,1)` 均匀浮点源；与 World 2 的流类结构一致。"""

    def next(self) -> float: ...


def moran_step_outcome(
    slots: list[int | None], reproducer: int, dier: int
) -> tuple[str, int | None, int | None]:
    """一步 Moran 的**回溯结果**，作为纯函数暴露。

    返回 `(kind, a, b)`：`kind` ∈ {"null", "transfer", "merge"}；merge 时 `a`/`b`
    是被合并的两个树节点（`a` 来自死者槽位，`b` 来自繁殖者槽位），transfer 时
    `a` 是被移动的节点，null 时二者为 None。

    建树与「claim (i) 的精确枚举」共用这一个函数——预注册 R5 要求枚举跑在
    shipped builder 自己的步规则上，共享而非各写一份是唯一能保证这点的做法。
    """
    if reproducer == dier or slots[dier] is None:
        return ("null", None, None)
    if slots[reproducer] is None:
        return ("transfer", slots[dier], None)
    return ("merge", slots[dier], slots[reproducer])


def build_moran_genealogy(
    n_sample: int, n_pop: int, draws: DrawStream
) -> tuple[list[float], list[int], int]:
    """回溯构造一棵 Moran 谱系树，返回 `(time, abv, steps)`。

    每步消耗 **两次** draw（繁殖者、死者各一次），与 prereg §3 的 draw parity
    约定一致；空步同样消耗两次，因为它在真实过程里也发生了。
    """
    if not 2 <= n_sample <= n_pop:
        raise ValueError(f"need 2 <= n_sample <= n_pop, got {n_sample}, {n_pop}")

    n_nodes = 2 * n_sample - 1
    time = [0.0] * n_nodes
    abv = [0] * n_nodes

    # slots[s] = 槽位 s 上那条祖先谱系当前对应的树节点，或 None。
    # 样本占据前 n_sample 个槽位；其余槽位不携带样本谱系。
    slots: list[int | None] = [None] * n_pop
    for leaf in range(n_sample):
        slots[leaf] = leaf

    step_time = 1.0 / (n_pop * n_pop)
    next_node = n_sample
    t = 0.0
    steps = 0
    alive = n_sample

    while alive > 1:
        steps += 1
        t += step_time
        reproducer = int(n_pop * draws.next())
        dier = int(n_pop * draws.next())

        kind, child_a, child_b = moran_step_outcome(slots, reproducer, dier)
        if kind == "null":
            continue

        if kind == "transfer":
            slots[reproducer] = slots[dier]
            slots[dier] = None
            continue

        time[next_node] = t
        abv[child_a] = next_node
        abv[child_b] = next_node
        slots[reproducer] = next_node
        slots[dier] = None
        next_node += 1
        alive -= 1

    return time, abv, steps
