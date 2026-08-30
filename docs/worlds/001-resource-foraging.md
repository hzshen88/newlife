# World 1：Resource Foraging（Parworlds Experiment 001）在 newlife 上的重表达

- **状态**：gate 已填空（2026-08-31）；重表达实现与比对进行中
- **来源协议**：`resource-foraging-v1`（冻结）——[`paralife/packages/Parworlds/experiments/001-resource-foraging/EXPERIMENT.md`](../../../../paralife/packages/Parworlds/experiments/001-resource-foraging/EXPERIMENT.md)，冻结决定 [`0004-experiment-001-freeze.md`](../../../../paralife/docs/decisions/0004-experiment-001-freeze.md)
- **Julia 实现**：`Parworlds/src/worlds/ResourceForaging/`（Model 284 + Dynamics 443 + EvidenceAdapter 235 + Assays 92 行）
- **冻结结果**：`experiments/001-resource-foraging/results/formal-seeds-101-120/aggregate.toml`

## 1. gate 填空决定

v0.2 gate 的填空选择 **Experiment 001（Resource Foraging）**，而非 000（Memory Benchmark）。理由：

1. **已知答案完整**：001 是唯一走完确认性 pilot 并冻结的正式研究——20 个配对 seed（101–120）× 双 treatment，判定 `freeze_candidate`；000 是校准实验（"不主张研究原创性"），其正式结果规模与完成度均次之。
2. **精确重放性质已验证**：冻结决定记录了 informative 与 cue-neutral 的 seed 101 在 Julia 侧完整重放、精确复现最终生态计数、账本误差与 assay 数值——录制 draw 序列注入法的前提成立。
3. **原报告自认适配**：001 PILOT §6.2 明言五位点查表控制器"适合作为 World 1 的平台校准"；§7 说明其只复用运行身份、命名随机流、artifact 生命周期、Observer、assay 契约——正是 newlife 契约层的对应物。
4. **它暴露的是真实痛点**：001 的两个"当前平台缺口"（§13，命名 RNG Bank、Observer 快照）恰是 newlife 已内建的能力（proofroot 流派生、Effect trace）。

## 2. 研究问题（原样照抄，不得改写）

> 在没有外部适应度分数、繁殖完全由资源和能量驱动时，可靠的局部资源信息能否使数字生命从不使用该信息的祖先进化出定向觅食策略？

三个假设：H1 信息条件产生定向觅食；H2 效果来自信号的因果使用；H3 效果不是任意移动或控制器复杂度造成。

## 3. 冻结已知答案（比对的目标数字）

来自 `aggregate.toml`（`paired-seed-bootstrap-v1`，20 seeds）：

| 量 | informative | cue_neutral |
|---|---|---|
| mean_harvest_contribution | 9.56328125 | −17.16640625 |
| positive_contribution_rate | 1.0 | 0.05 |
| mean_true_alignment_rate | 0.9840937500000001 | 0.2530439350907588 |
| mean_ablated_alignment_rate | 0.19935156249999997 | 0.21557447679664204 |
| survival_rate | 1.0 | 1.0 |

配对差：`paired_mean_difference = 26.7296875`，95% bootstrap CI `[22.35625, 31.3421875]`（10000 样本），下界 > 0 → 冻结门槛通过。

其他必须对得上的事实：真实信号边际频率 HERE 0.16282 / NORTH 0.21273 / EAST 0.21086 / SOUTH 0.20262 / WEST 0.21096（无单一方向偏置）；账本最大绝对误差约 `2.82e-11`；世界宪法 §3.5 的 tick 顺序与 §6 的六条命名流。

## 4. 比对方法（按冻结的 proposal §7 / §5.10 裁定执行）

合同边界：**种子可移植、序列不可移植**。分三层：

- **L1 派生种子层（已验证，2026-08-31）**：proofroot `evidencecore-rng-v1` 与 Julia oracle `parworlds-rng-v1`（两编码字节等同，charter 主张）对 seed 101 × 六条流（initialization / environment / sensing / mutation / selection / assay）派生种子逐位一致：

  | 流 | 派生种子（两侧相同） |
  |---|---|
  | initialization | `0x5392e858b549e055` |
  | environment | `0x38af112e76e48b1f` |
  | sensing | `0x13f881632b9bdc1a` |
  | mutation | `0xe525aeb0768f19b0` |
  | selection | `0x12f80eea7450898c` |
  | assay | `0x647dca9527840b9d` |

  这就是 proofroot 跨语言向量在真实冻结研究上的第一次载荷兑现。
- **L2 录制 draw 注入（优先法，冻结文本指定）**：在 Julia 侧重放 seed 101（冻结决定已证精确重放），以录制 harness 逐 tick 记录六条流的全部 draw 值；newlife 侧以注入器消费同序 draw。两侧比对的观测量：逐 tick 账本（外源输入、溢出、收获、代谢、移动、繁殖、死亡耗散、balance error）、最终生态计数（存活数、总资源、总能量、出生/死亡、移动尝试/成功）、assay 的 harvest_contribution 与对齐率。目标：注入 run 的观测量与 Julia 重放记录**逐值相等**（浮点经 proofroot canonical 形式——IEEE754 位模式——比对；这是 §5.9 spec 自 v0.2 起的第一个真实载荷）。
- **L3 观测量统计比较（退路）**：若注入法因流消费形态差异不可行，退到不注入、纯 Python 生成器跑同配置，对冻结聚合做分布级核对（不得声称为逐值复现）。

尺度决定：比对在 **seed 101 配对 × 冻结配置全量（32×32、5000 tick）** 上做注入验证；20-seed 全套件统计重跑不是 gate 门槛（原判据已由 Julia 侧完成，Python 侧全套件属 gate 之后的可选扩展）。

## 5. 重表达架构：宪法 → newlife 声明

宪法 §3.5 的固定 tick 顺序直接映射为 v0.1b 的 stage 声明（每 tick 一个回合的编排）：

```text
replenish（environment 流：外源补给 + 容量溢出）
  -> perceive-and-intend（sensing 流：cue -> action 查表；informative/cue_neutral 之分）
  -> resolve-movement（selection 流：目标冲突等概率结算，成功者同时提交）
  -> harvest（收获 + 固定效率转化）
  -> metabolize（移动成本 + 维持成本，能量不足即死）
  -> reproduce（selection 流出生冲突 + mutation 流变异 + 尝试成本）
  -> age-and-die（寿命死亡，剩余能量按声明比例回格）
  -> observe（Observer 快照 + 资源-能量账本核验）
```

机制注册表条目（`mechanisms/`，全部由本问题导出，不再有压力测试的人造切片）：

| 机制 | 平面 | 权属（claims） | Effect 种类 | 流 |
|---|---|---|---|---|
| `resource-environment` | biological | 各格资源路径 own | StateDelta(add/set)、Event(溢出) | environment |
| `forager-perception` | biological | 各生命 controller 槽 own | Event(决策) | sensing |
| `forager-movement` | biological | 占用格 own；能量 contribute | StateDelta、Transfer(移动成本→耗散)、StructuralRewrite(位置) | selection |
| `forager-harvest` | biological | 格资源 contribute；生命能量 own | Transfer(资源→能量) | —（确定性） |
| `forager-metabolism` | biological | 生命能量 own；死亡回格 | StateDelta、Transfer、StructuralRewrite(死亡) | —（确定性） |
| `forager-reproduction` | biological | 出生格 own；亲本能量 own | StructuralRewrite(出生)、StateDelta、Event(变异) | selection、mutation |
| `assay-runner` | protocol | 只读 + own 的 assay 产物路径 | Event(assay 结果) | assay |

实现要点（与 Julia 逐行对齐的硬约束）：

- 坐标环绕 `mod1`、五值感知字母表（HERE/NORTH/EAST/SOUTH/WEST）、并列对称破平规则 `start = mod(x + 2y + tick + seed mod 5, 5)`（Dynamics.jl:90）逐条照搬——它不消耗任何 RNG 流（宪法 §3.3）；
- 冲突结算的遍历顺序（目标按排序、竞争者按排序、平局才用流）照 Dynamics.jl:147-183/236-311 原样——顺序本身是世界语义；
- tick 账本公式（§9）逐 tick 核验，误差超 `1e-8` 即 Failed（宪法：账本失败是实现错误）；
- 祖先控制器五位全 STAY；变异每独立位点以 mutation 流先判是否变异、再抽新行动（Dynamics.jl:71-79 的两次 rand 消费顺序必须一致）。

## 6. 痛点对照（gate 验收的测量项）

| 痛点 | ParaLife（001 的实现形态） | newlife 重表达 | 测量 |
|---|---|---|---|
| P1 机制可组合 | 世界实现 package-local（`src/worlds/ResourceForaging/`），不可跨世界复用 | 六机制入注册表，assay 与环境机制理论上可被 World 2 复用 | 机制清单 + 后续世界复用数 |
| P2 证据纪律运行时化 | `check_architecture.jl` 脚本 + 章程注释；RNG 隔离靠测试枚举 | authority 越界/旁路在 profile 校验期拒绝；流身份进 trace；import-lint | 运行时拒绝负例数 vs 脚本检查数 |
| P3 harness 手工度 | `scripts/common_grid.jl`/`common_orchestration.jl`/`run_foraging_*.jl` + `test/resource_foraging_tests.jl`（483 行）手搭账本、Observer、流绑定 | 世界组装 = examples 配置 + 机制声明（staging 声明因果阶段）；harness 代码只剩注入器与比对器 | 双侧行数/文件数对照（v0.2 关闭时填写） |

## 7. 范围与明确不做

- **做**：双 treatment 全 tick 语义、六条命名流、账本、Observer 快照、assay（L2 注入法）、机制注册表、examples/first-world 零 runtime 代码（import-lint 证明）。
- **不做**：20-seed 全套件 Python 统计重跑（gate 后可选）；000 Memory Benchmark 重表达；对协议语义的任何"改进"（宪法条文原样照搬；发现疑义记差异文档，不顺手修）；live RNG 的跨语言一致性主张（charter 边界）；发表级统计。

## 8. 与两个已关闭预注册的关系

- v0.1a（lowering）提供"机制只发 Effect、update 机械推导"的写入路径——本世界的每一笔资源/能量/位置变更走同一条路；
- v0.1b（staging）提供"tick 顺序 = 声明 DAG"的编排——宪法 §3.5 不再是代码顺序，而是声明；
- proofroot canonical 形式（IEEE754 位模式）自本世界起成为跨语言比对的尺子（§5.9 切换点）。
