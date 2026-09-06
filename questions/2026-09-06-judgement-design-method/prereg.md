# 判据设计方法论

**Frozen at commit:** 55feaeb9f18ab3a86f6e613715cee9b5a9175816

- **slug**：`newlife-judgement-design-method`
- **上游**：goal（exloop-archive，frozen `f3b9b19`）· design（同处，`7d35796`）

<!--@reproduction_class: stochastic — 被测的两个世界都是随机的（远端 LLM、Moran 溯祖）。
S0 因此作用在**判定层**：给定同一份采样数据，两次运行的判定产物逐字节相同。本轮的 S0
不证明「世界可复现」，只证明「判定不引入新的不确定性」——与第二十一个里程碑同一处降级，
理由相同，写在这里而不是让它冒充原来那个 S0。-->

## 0. 起草时已经看过的量

| 已看过 | 值 | 来源 |
|---|---|---|
| 合成重尾数据上 `trimmed` 与 `mean` 的 N | **64** 与 **在 256 预算内达不到 0.8 功效** | `design.py` selftest |
| AR(1) φ=0.85 下推出的 N 的真实功效 | **0.74**（声明目标 0.80） | 自我评审时实测 |
| 尾比 `sd/(1.4826·MAD)` | 正态 **0.94** · 第二十一个里程碑那批（含 −400）**10.76** | 同上 |
| 世界 B（`theta=1.0/2.0`, `nsam=8`）`segsites` | 变异系数 **0.64 / 0.54** | 本日实跑 30 次 |
| 世界 A 单批（第二十一个里程碑遗留） | `A2/-4.0` sd **138.28**，变异系数 **2.36** | 该里程碑产物 |

**以上全部来自合成数据或既有产物。未按本方法论在任何真实世界上导出过判据，
也未做过 S5/S6/S7 的任何检验。**

## 1. 假设

- **H1**：同一套方法论作用于两个噪声结构迥异的世界，各自导出的判据**都有判定力**
  （S5、S6），且两个判据**确实不同**（S7）。
- **H0**：任一不成立。**H0 必须指名**：S5 假 = 方法论在重尾世界失灵；S6 假 = 在轻尾世界
  失灵；S7 假 = 方法论是**伪装成方法的常量**，两个世界填出同一个答案。

## 2. 判定单元（机械合取，runner 计算，**绝不手填**）

| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | **判定层**自我复现 | 给定同一份采样数据，两次运行的判定产物逐字节相同 | mechanical |
| **S1** | 环境未变 | 运行时已装的发行包恰是 `env.lock` 记下的那些 | mechanical |
| **S2** | 推导器在**合成输入**上正确 | 重尾下 `trimmed` 的 N 小于 `mean` 的；效应量更大时 N 不更大；「预算内判不了」可达 | seen |
| **S3** | 每条判据都能变红 | 每个谓词在合成反例上返回 false | mechanical |
| **S4** | **门逮得住不自洽** | 把 `result.n` 改成非导出值，门变红；改回则绿 | seen |
| **S5** | **世界 A 的判据有判定力** | 按导出的 N 采样：同配置判**等价** ∧ 换模型判**不等价** | **blind** |
| **S6** | **世界 B 的判据有判定力** | 同上，换 `theta` | **blind** |
| **S7** | **两个世界导出的判据确实不同** | `n` 或 `location.statistic` 至少一项不同 | **blind** |

**verdict = S0 ∧ S1 ∧ S2 ∧ S3 ∧ S4 ∧ S5 ∧ S6 ∧ S7.** 任一为假 → H0；**S0 为假 → INVALID**。

**S5/S6/S7 三格全盲**：pilot 只跑 S2 与 S4，两者都只用合成输入，**不做任何真实世界的
判定力检验**。runner 在 `NEWLIFE_PILOT` 置位时不进入这三格，该条件单向——只由
`newlife pilot` 设置，正式 run 从不设置，故只能让 pilot 少算，永不让判定少算。

**S7 是防「方法论退化成常量」的那一格。** 两个变异系数差四倍的世界若填出同一个答案，
方法论没有在起作用，而使用者无从察觉。

## 3. 冻结的实现约束

1. **本轮的采样量不由人定，由被检验的方法论导出。** 流程：先采少量 pilot 样本 →
   按方法论填 `judgement-design.json`（两个世界各一个 quantity）→ **该文件以
   `newlife freeze --data` 钉住哈希** → run 按导出的 N 采样并检验。
   **若方法论导出的 N 是错的，S5/S6 就会失败——那正是本轮要测的。**
2. **两个世界固定如下，不得更换**：
   - **世界 A**：远端 ollama，`qwen3.5:4b` 对 `qwen3.5:9b`，`temperature=0.7`，
     `think=false`，扫描点 `-1.0` 与 `-4.0` eV，观测 log10(TOF)。
   - **世界 B**：`CoalescentWorld(nsam=8)`，`theta=1.0` 对 `theta=2.0`，观测 `segsites`。
     `theta` 须落在该世界 R3 边界（`u<=30`）之内。
3. **预算上限**：世界 A `max_n = 64`（单次调用约 2 秒）；世界 B `max_n = 2000`（本地毫秒级）。
   导出的 N 超上限时，对应的 S5/S6 **记为未建立判定力（`passed = false`）**，且产物必须以
   `undecidable_within_budget` 标出原因。

   **这一条起草时写错过，冻结前改正，理由记在这里**：原文写的是「记为『预算内判不了』
   **而非失败**」。那是自相矛盾的——S5 断言的是「这个世界的判据有判定力」，判不了就是
   没建立，合取不该因为原因体面就放行。**「方法论正确地输出了『判不了』」与「本轮建立了
   判定力」是两件事**，前者是方法论在起作用，后者没有发生。
   **H0 的解读须据此区分：不是方法论失灵，是这个世界在这个预算下判不了**——而那本身
   就是一个有用的结果，它给出了一个具体的资源需求。
4. **判定层与采样层分离**：采样落盘 `results/samples.json`；判定只读该文件；
   S0 的内层复现运行不重新采样。**采样失败（网络、空响应、越界）一律硬失败**，
   不许静默取部分样本。
5. verdict runner **独立实现**推导与检验，不得 import 或复用
   `newlife.stochastic.design` 与 `newlife.stochastic.equivalence`。
6. `judgement-design.json` 必须通过 `newlife.gates.judgement_design` 的两层检查
   （形状与自洽），且其 `applicability.comparison_form` 只能是 `two_group_location_shift`。

## 4. 结果作废条件（与判据分开）

- 远端服务不可达或返回空，导致样本数不足导出的 N → `INVALID`，不记 H0。
  **服务不可用不是科学失败。**
- `judgement-design.json` 在冻结之后被修改 → `INVALID`（`audit` 会 re-hash 它）。
- 两个世界的定义或预算上限在冻结后被更改 → `INVALID`。
- runner 复用了 `design`/`equivalence` 的实现（违反约束 5）→ `INVALID`。
- 世界 B 的 `theta` 越过 R3 边界 → `INVALID`（那是该世界声明过的适用范围之外）。

## 5. 事前声明：结论的边界

- **本方法论只覆盖 `two_group_location_shift`。** 趋势、多组、斜率、比例、方差都不在内。
  **第二十一个里程碑自己的科学问题（TOF 随吸附能单调）正是趋势类**——本轮即使 H1，
  也不能推论那类问题可以用同一套推导。这条写在这里，不靠沉默带过。
- 结论只覆盖**这两个世界**，不是关于「一切随机模拟」的断言，两个样本远谈不上覆盖噪声结构的空间。
- **`independence` 与 `pilot_adequacy` 两项在本轮只被检查「是否声明」，其取值的正确性不被检验。**
  AR(1) 那次实测（0.74 对 0.80）说明相关性修正是必要的，但**本轮不验证修正因子填得准不准**。
- **S0 的证明力被降级**，见 `@reproduction_class` 锚。
- H1 成立也不意味方法论对**更慢或更贵**的世界可用：预算上限是在「单次约 2 秒」与
  「本地毫秒级」的前提下选的。

## Frozen data checksums

- questions/2026-09-06-judgement-design-method/env.lock 92cf362308de94416271ad283b566717beb3dd56
- questions/2026-09-06-judgement-design-method/judgement-design.json 62f8bc845cadbfd0edf5baa78a3e683ea696423b
- questions/2026-09-06-judgement-design-method/results/pilot-samples.json fe99852f52f2e383583ba05194798f9d771b6d41
