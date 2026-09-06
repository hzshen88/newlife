# 复现类别的可声明性

**Frozen at commit:** 876ed29205e44535cadaf0d93db827bcd736116d

- **slug**：`newlife-reproduction-class-declarability`
- **上游**：goal（exloop-archive，frozen `1b0a113`）· design（同处，`38b8997`）
- **形态**：newlife **同仓形态的第一个样板**——预注册与产物同仓，CHRONOLOGY 可真正成立。

## 0. 起草时已经看过的量

**不是自白，是让读者分得清哪些单元是确证的、哪一格是盲的。**

| 已看过 | 值 | 来源 |
|---|---|---|
| `results/` 下 bundle 数 | 22 | `ls` |
| 产物中出现 `seed`/`rng`/`random` 的份数 | 6 / 22 | `grep -ril` |
| `conform/` runner 数 · 其中读环境变量的 | 23 · 3 | `grep -c os.environ` |
| **`verdict_rot` 当日结果** | **7 reproduced · 0 broken · 1 已知 `unevaluable`（seventh）** | 2026-09-06 实跑 |

最后一行给出一个**降低意外性的先验**，必须写明：八个旧 verdict 里七个逐字节复现，
所以这些世界**大概率不是** `stochastic`。但它不消除 S5 的盲——逐字节复现只说明
「该次重跑相同」，不说明**种子可追溯**，而 `deterministic` 与 `seeded` 的分界正在那里。
**未看过任何真实 bundle 的分类结果。**

## 1. 假设

- **H1**：三类复现声明在 **L2 级**（产物 ＋ runner 源码）覆盖冻结时刻 `results/` 下的**全部** bundle，`unclassified` 计数为 **0**。
- **H0**：存在至少一份 `unclassified`。**H0 由 S5 单独指认**。

## 2. 判定单元（机械合取，runner 计算，**绝不手填**）

| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | 自我复现 | 两次独立运行产出逐字节相同的产物 | mechanical |
| **S1** | 环境未变 | 运行时已装的发行包恰是 `env.lock` 在冻结时记下的那些 | mechanical |
| **S2** | 分类器在**合成样本**上正确 | 8 个人工构造样本（每类 2 个，含 2 个 `unclassified` 负例）全部命中预期类别 | seen |
| **S3** | 每条判据都能变红 | 每个谓词在合成反例上返回 false，运行时计算 | mechanical |
| **S4** | 安全绳：既有判定未被本轮打坏 | `verdict_rot` 报 `reproduced ≥ 7` 且 `broken = 0`（`seventh` 的已知 `unevaluable` 除外） | seen |
| **S5** | **L2 覆盖全部 bundle** | `unclassified` 计数 = 0 | **blind** |

**verdict = S0 ∧ S1 ∧ S2 ∧ S3 ∧ S4 ∧ S5.** 任一为假 → H0；**S0 为假 → INVALID**。

**S5 是唯一盲的一格。** runner 在 `NEWLIFE_PILOT` 置位时**不计算** S5，因此它在 pilot 产物的
`units` 里**根本不出现**（不是出现并为假）。

这确实是一个条件，所以必须说清它为什么不是「可选择性关闭判据」的口子：**它是单向的**——
`NEWLIFE_PILOT` 只由 `newlife pilot` 设置，正式 `run` 从不设置它，所以这个条件只能让 pilot
少算一项，**永远不能让正式判定少算一项**。而 pilot 的定义就是「冻结前的探索运行」；在 pilot 里
计算 S5，等于把本轮唯一携带信息的那一格当场烧掉。

**S2 与 S5 分开的理由**：S2 测实现对不对，S5 测划分够不够。只有 S2 绿而 S5 红，
才说明不是分类器写错、是三类**不足以**覆盖真实世界——那正是 goal 要买的边界。

## 3. 冻结的实现约束

1. **特征表冻结如下，不许扩。** 落不进任何一类的记 `unclassified` 并使 S5 红：

   | 类别 | 判定条件（合取） |
   |---|---|
   | `deterministic` | 无 RNG 痕迹 **且** 无外部不确定源 |
   | `seeded` | 有 RNG 痕迹 **且** 种子可追至记录在案的输入（`proofroot` 具名 RNG 流派生，或产物中的 seed 字段） |
   | `stochastic` | 存在不受控非确定源：网络/远端服务调用、并发执行、调用外部程序的子进程、读时钟 |
   | `unclassified` | 皆不成立，或同时命中 `seeded` 与 `stochastic` |

2. **一律走 AST，不得 grep 源码。** 第十八个里程碑栽过：按子串查禁用词，命中的是模块自己 docstring 里的散文。
3. **分类器不执行被分类的 runner**，只做静态分析与读产物。
4. **bundle 清单 = 冻结时刻 `results/` 下的全部子目录**，由 runner 枚举，不得人工挑选。
5. 产物必须同时给出 **L1（仅产物）与 L2（产物＋源码）** 两级分类结果，及每份的命中特征。
6. `unclassified` 的原因取自固定值域，散文不参与判定：
   `no_runner_found` · `rng_without_traceable_seed` · `mixed_seeded_and_stochastic` · `no_feature_matched`
7. verdict runner **独立实现分类**，不得 import 或复用 `newlife.gates.reproduction_class` 的代码路径。

## 4. 结果作废条件（与判据分开）

- S4 因**本轮之外**的改动而红 → 记 `INVALID`，不记 H0。**环境失败不是科学失败。**
- 分类器执行了被分类的 runner（违反约束 3）→ `INVALID`。
- 特征表在冻结之后被修改 → `INVALID`。
- bundle 清单被人工增删（违反约束 4）→ `INVALID`。
- verdict runner 复用了分类器实现（违反约束 7）→ `INVALID`。

## 5. 事前声明：结论的边界

- 结论**只覆盖本仓冻结时刻的 22 份 bundle**，不是关于「一切模拟」的断言。
- **不回答**「换几个种子才够」——那需要它自己的判定力论证。
- L1 与 L2 的差是**观测量**，不是判据。它给对手方的论证（「类别是意图不是属性」）一个定量形式，但本轮不据它判 H0/H1。
- **与 `verdict_rot` 的关系**：后者的四态说的是「重跑后发生了什么」（时间维度），本轮三类说的是「这个世界本质上能否字节复现」（性质维度），两者正交。本轮**不改动** `verdict_rot`。
  顺带记下一条本轮不处理的观察：`verdict_rot` 目前无法区分「代码变了导致答案变了」与「这个世界本来就不字节复现」——那是下一个里程碑的材料。
- H1 成立也**不意味**三类划分对 newlife 之外的模拟成立；样本全部来自本项目自己的里程碑，同源性很高。

## Frozen data checksums

- questions/2026-09-06-reproduction-class-declarability/env.lock 92cf362308de94416271ad283b566717beb3dd56
