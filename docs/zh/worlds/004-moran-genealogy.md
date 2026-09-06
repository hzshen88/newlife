# World 4：Moran 谱系 vs Kingman 溯祖，以及第一次跨世界机制复用

- **状态**：已判定（2026-09-02）。H1 支持；goal 的 P1 判为 `achieved`——**移离零，
  不是解决**。两者独立判定，见 §5。
- **证据**：`results/fourth-world/summary.json`（`passed: true`，schema
  `newlife.fourth-world.gate.v1`）
- **实现**：`packages/newlife/src/newlife/mechanisms/fourth_world/`
  （`genealogy.py` 回溯建树 + `world.py` 注册表组装）；verdict runner
  `packages/newlife/src/newlife/conform/fourth_world_verdict.py`
- **预注册**：exloop
  `docs/science-superpowers/preregistrations/2026-09-02-newlife-fourth-world-cross-world-mechanism-reuse.md`
  ，冻结于 `24bb02e`，`prereg.sh audit` PASS

---

## 1. 世界选择

这是第一个**没有任何外部程序作为对标**的世界。World 1 对标 Julia 录制的 draw，
World 2 对标 `ms` 二进制自己的 draw；两者的逐位精确都建立在"存在一个可重放的外部
参考实现"之上，而 question 阶段确认前向选择动力学没有这样的程序。

第四世界改为对标**项目自己推导并验证的数学**。中性 Moran 过程的谱系与 Kingman 溯祖
的关系给了一个天然的两层结构，而这个结构本身就是这个世界要说清的东西。

选择同时受一个约束：goal 要求推进 P1（跨世界机制复用），且明确警告"为了让复用容易
而选世界"是主要失败模式。所以顺序是先确认 World 2 的 observer 只依赖树的形状、再问
有没有值得答的问题需要一棵树被观测——不是反过来。

## 2. 比对层级：一个精确、一个统计，而且是被数学逼出来的

**拓扑精确一致，时间不一致。** 载荷事实两条：(a) Moran 一步只死一个个体，所以每步
至多一次合并且必然二叉；(b) 条件在发生合并上，合并的 pair 在 `C(k,2)` 上均匀，与
Kingman 同分布。给定 (a)(b)，每步合并概率 `p(k)` 从拓扑分布里整个约掉——**无论它是
什么函数**。

早先的推导把"`p(k)/C(k,2)` 与 n 无关"当作载荷理由，被红队用两个精确反例双向证伪：
比值随 n 变的模型拓扑却与 Kingman 逐项相同（非必要）；比值恒定的模型拓扑却 177/180
不同（非充分）。**结论对，理由错**——两个反例作为永久 check 保留在
`exloop` 的 `questions/verification/moran_genealogy_check.py`。

时间则不同：Moran 的等待是几何分布、Kingman 是指数分布，有限 N 下不等，差距按 `1/N²`
收缩。所以：

| 层 | 检什么 | 结果 |
|---|---|---|
| **claim (i)** 拓扑 | shipped builder 自己步规则诱导的 ranked labelled history 精确分布，对 Kingman 的闭式 `2^(n−1)/(n!(n−1)!)` | `n ∈ {3,4,5,6,7}`，**0 mismatch**，56,700 条 history 在预算内 |
| **claim (ii)** 观测量 | 2101 个 replicate 的 `S̄` 对解析靶 `θ·H_(n−1) = 137/30` | `S̄ = 4.5307` ∈ `[4.4286, 4.7047]` |

**claim (ii) 的靶是解析常数，不是另一个模型的分布**——这一条是红队第五轮救回来的。
原本写成"两模型的 segsites 分布在等价边界内一致"，而两模型的 `E[S]` 在**每个有限 N
上恒等**（都等于 Watterson 的 `θ·H_(n−1)`，逐段相等，连 N 都不依赖）。那不是弱检验，
是**不可证伪的检验**：跑完必然"H1 supported"，却什么都没证明。改为对照解析靶后，
失败会指向实现而非 Moran–Kingman 关系，判据重新有了牙齿。

`ms` 的时间单位是关键实现细节：它用 `-log(u)/(n(n−1))`，分母是 `n(n−1)` 而非
`C(n,2)`，所以其时间单位是 Kingman 标准的一半，Moran 每步对应 `1/N²`（用 `2/N²`
树长翻倍）。

## 3. 复用：范围由 registry 裁定，不是设计偏好

第四世界注册**自己的** Moran builder（`biological`，own `TREE_PATH`）+ World 2 的
`second-world-observer`（**原样，零字段修改**）。

不能同时注册 World 2 的 coalescent：两者都会 `own TREE_PATH`，registry 抛
`StructuralOwnershipConflictError`。这条边界由执行确认并写进测试，不是偏好。

**C1 的判据是对象同一性**，不是模块名。实测三种假复用：源码复制、本地包装遮蔽、
**手工改写 `__module__` 的复制品**——第三种能骗过字符串判据，被同一性挡住。
`reuse-trace.json` 记录 `observer_is_world2_object`，由 verdict runner **读**而非写。

## 4. 痛点对照（P1）

| | 事前判据（goal §3，冻结于 question 之前） | 实际 |
|---|---|---|
| C1 | 机制被 import **且运行时真被调到**，非本地重实现 | `observer_is_world2_object = true`；traced run 确认每个 replicate 恰调一次 |
| C2 | 无冻结产物跨世界 | `execution_input_paths = []` |
| C3 | 被复用机制的声明未改变，或改动被记录 | `observer_spec_unedited = true`，走第一支；IC-2 从未触发 |
| C4 | P1 判定与 verdict 物理分开 | 本文 §5 与 goal §8 由人写；`summary.json` 经检查不含任何 goal 词汇 |

**P1 判为 `achieved`，含义窄且事前冻结：一个运行时跨世界机制复用的实例现在存在，
P1 移离零。不是"P1 解决"。**

## 5. 如实记录

**判定与 verdict 分开**：H1 支持是 verdict runner 从合取机械算出的；P1 的四选一是
人按 goal §3 的判据写的。两者独立取值——本世界恰好都是正面，但 R15 明写"H1 的结果
不进入 P1 的判定规则"，World 2 记录的 `H1 支持 + P1 倒退` 组合在本流程里仍可表达。

**代价一：消费方迁就了生产方的命名空间。** `TREE_PATH` 是 World 2 的模块常量
`("second_world", "tree")`，第四世界的 kernel 状态里因此带一个名为 `second_world`
的键。参数化它会改动 World 2 的声明、触发 C3 第二支、并要求重跑 World 2 的 verdict，
plan R2 权衡后选择接受耦合。**这个组合不是干净的**，写在这里而不是抹平。

**代价二：`staging.py` 第四次被绕过。** `{stage, after}` 的 DAG 仍不能表达"重复到
吸收"。这是 goal §5.1 事前预声明的，不是新发现；四连的信号进 `proposal.md` §8 的
风险清单。

**范围**：P1 的可组合性现在是**被演示过**，不是**被大规模确立**。一个实例。

## 6. 方法学：本世界是「审核可让渡」这套机制的第一个完整样本

question 与 plan 全程用机器可验的锚点与追溯链（`exloop` 的
`docs/science-superpowers/verification/`），文档里每个载荷数字都绑定到脚本台账，
goal 的每条 criterion 都被下游文档显式认领。question 经五轮独立红队，plan 经三轮。

最值得记的一条：**第五轮才发现 claim (ii) 原本不可证伪**，而前四轮的攻击面是"找
问题"，第五轮改成"只找科学问题、不报措辞"。红队的产出取决于攻击面的指定，不取决于
轮数——细节在 `~/.claude/skills/newlife-milestone/SKILL.md`。
