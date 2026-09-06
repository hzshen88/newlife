# World 2：`ms` 最小溯祖模型在 newlife 上的重表达

- **状态**：已判定（2026-09-01）。H1 支持，`ms_minimal_coalescent_reproducible`。
- **证据**：`results/second-world/summary.json`（`passed: true`，schema
  `newlife.second-world.gate.v1`）+ 30 份逐复制品记录 `results/second-world/replicates/`。
- **实现**：`packages/newlife/src/newlife/mechanisms/second_world/`
  （`ms_coalescent.py` 独立移植 + `mechanisms.py`/`world.py` 注册表）；
  verdict runner `packages/newlife/src/newlife/conform/second_world_verdict.py`。
- **预注册**：exloop `docs/science-superpowers/preregistrations/2026-08-31-newlife-second-world-ms-coalescent-declarability.md`
  （冻结于 `c450072`/`fb61994`，冻结前两轮红队）。
- **补记说明**：本文件在里程碑收尾之后补写（2026-09-01）。收尾当时漏了
  `docs/zh/worlds/` 这一项，遗漏由 `newlife-milestone` skill 的收尾清单发现。
  补写不改动任何判定，只把已判定内容归位；本文所有数字均取自上列证据文件。

---

## 1. 世界选择决定

第二世界最初设想的对标是 SLiM / msprime，**最终没有采用**。question 阶段的调研
发现那条路会把证明标准从"逐位精确"降级为"统计上差不多"：SLiM / msprime /
fwdpy11 / simuPOP 都不公布可从 spec 复现的 draw 消费契约（RNG 或委托给 GSL，
或内部实现未公开），因此无法像 World 1 那样精确对账。

改选 Hudson 的 `ms`（1980 年代经典溯祖模拟器，该领域公认的验证标准答案）：
它只有 1851 行，能真正啃透源码，保住了最高标准。代价是它**只做中性模型**——
正向选择动力学要等第三世界。

`vendor/ms/` 逐字 vendored 并按 SHA-256 钉死。理由记录在 `vendor/ms/README.md`：
`ms` 没有正式版本号，从个人学术主页分发，作者已退休，这类页面会无预告消失；
vendoring 是钉住特定 build 做跨语言比对的唯一办法。

## 2. 研究问题

newlife 的五类 Effect 契约与机制注册表，能否表达 `ms` 的最小溯祖模型
（单群体、无重组、无基因转换、无指数增长、`-t theta` 无限位点突变），
并逐位精确复现 `ms` 二进制自身的输出？

## 3. 冻结已知答案（比对目标）

**目标不是文献数字，是真实 `ms` 二进制当场编译运行后自己打印的输出。**

冻结网格（R6）：`nsam=4`、`theta=2.0`、三组种子三元组
`(3579, 27011, 59243)` / `(12345, 6789, 999)` / `(101, 202, 303)`，
每组 10 个复制品，共 **30 个复制品**。

主判据比的是整数与字符，不是浮点——因此**不需要任何浮点容差**：

- 每个复制品的 segsites 计数：整数相等
- 每个复制品的完整基因型矩阵：字符串相等
- （`positions` 是唯一的浮点打印量，按 R3 显式排除在比对之外）

## 4. 比对方法

### 与 World 1 的层级关系

同属 **L2 录制 draw 注入**（`001-resource-foraging.md` §4 定义的优先法），
但 oracle 换成了 C 程序：用 `vendor/ms/verification/rand1_instrumented.c`
在 build 时替换 `rand1.c`，记录真实 `ms` 运行中每一次 `ran1()` 调用及其返回值，
再把这条 draw 序列按 R3 规定的调用顺序重放进 Python 移植。

**结构差异，必须写明：L1 派生种子层不在本世界的比对路径上。** World 1 的六条
命名流经 `derive_stream_seed` 派生，L1 逐位一致是比对的第一层；本世界的冻结网格
直接把手选的种子三元组喂给 `ms -seeds`，这些三元组**不经过** `derive_stream_seed`。
R2 的 UInt64 → `drand48` 三元组映射裁定因此是**独立测试的**，不是比对链条的一环
（红队一轮发现的正是这个：原始 R2 检查从未被任何东西真正执行到）。

### 两层判据（合取，缺一不可）

判定是 tier_a ∧ tier_b，**不许被单层结果冒领**——这是红队第三轮的修正项。

| 层 | 检的是什么 | 结果 |
|---|---|---|
| **tier_a** 算法层 | 独立、无依赖的 Python 移植，重放真实 `ms` 二进制自身记录的 `drand48()` draw 序列 | 30/30 逐位精确复现 |
| **tier_b** 注册表层 | 同一算法包进 `MechanismSpec` 两机制注册表后，逐复制品复现 tier_a 自身的输出 | 30/30 |

两层的 draw 消费量逐种子相同，且**零剩余、零提前耗尽**：

| 种子组 | draws_logged | draws_consumed | leftover |
|---|---|---|---|
| seedA | 177 | 177 | 0 |
| seedB | 163 | 163 | 0 |
| seedC | 191 | 191 | 0 |

draw parity 的纪律与 World 1 的 `injection.py` 同源：draw 数只能来自真实的
consumed/leftover 计数，不许手推。任何错位都会在重放时立刻炸成 exhaustion 或
divergence，而不是悄悄给出一个错答案。

### 附加结构检查

- **R2 映射正确性**（独立执行，不经比对网格）：三个 16-bit 字取值合法、
  往返重装 `seedv[0] | seedv[1]<<16 | seedv[2]<<32` 精确还原派生 UInt64 的低 48 位、
  截断可观测有损（只差高 16 位的两个 UInt64 映射到同一三元组）。全部通过。
  红队二轮删掉了原来的"两两互异"断言——2–4 个样本上它近乎恒真
  （低 48 位碰撞概率 ≈2⁻⁴⁸），与映射是否正确无关。
- **`segsites == 0` 覆盖率**：该输出形态由一次独立的从零重实现发现（原 question
  未声明），因此断言冻结网格真的覆盖到它。实际命中 6 次
  （seedA 0 / seedB 4 / seedC 2）。

### 非门（仅供参考，不参与判定）

冻结网格 30 个复制品的 segsites 均值 **3.1**，Watterson 闭式期望
`E[S] = theta·Σ1/i = 3.6667`。这个小网格本就不该钉死解析期望，所以这项检查
**不附任何数值容差**，也不进判定——不给一个从未打算当门的检查安一个门的样子。

## 5. 重表达架构：两条机制声明

契约零改动（R7）：`core/contracts.py`、`MechanismSpec` dataclass 形状、
profile 版本全部未动。

| 机制 | 面 | 权限 | 允许的 Effect | 调度 |
|---|---|---|---|---|
| `second-world-coalescent` | `biological` | `StateClaim(TREE_PATH, "own")` | `StructuralRewrite` | `{"stage": "coalesce"}` |
| `second-world-observer` | `evidence` | `StateClaim(TREE_PATH, "read")` | `Event` | `{"stage": "observe", "after": ["coalesce"]}` |

溯祖建树的每一次合并事件发一条 `StructuralRewrite`；观测者只读已提交的树，
把 segsites 计数与基因型矩阵作为一条真实的 `Event` 发出。写入权限的排他性由
path authority 保证，不靠约定。

## 6. 痛点对照（如实记录，不润色）

**本世界不推进 P1，且相对 P1 小幅倒退。**

- **P1（机制跨包不可组合）——倒退**。这是一个新机制加一个观测者，不是跨世界
  机制复用的演示。World 1 的任何机制都没有在这里被复用。
- **P3（每个世界手搭 harness）——未推进**。整个溯祖事件循环
  （`while(nchrom > 1)`）收在**单个** `MechanismSpec` 的 step 函数内部，
  与 World 1 的 tick 循环同样是手写 Python 循环，不是 `staging.py` 编译出的 DAG。

**这是连续第二个 bypass `staging.py` 的真实世界。** 原因不是疏忽：拆分一个
"多个竞争指数等待里挑最早一个"的事件循环，早于 schedule 形状问题解决之前
就是过早结构化（v0.1b 明确把重复/单 Composite 语义留作 open，风险 4 至今未解）。
代价如实记下：**`staging.py` 在本世界之后仍然只是压力测试期的机器。**

- **P2（证据纪律靠治理而非运行时）——本世界未构成新证据**，但也未被绕过：
  两条机制的写入权限由 path authority 在运行时约束，观测者只读。

**没有事前 goal 文档。** goal 环节是本世界收尾之后才加进流水线的
（见 `newlife-milestone` skill）。上面的痛点对照因此是**事后记录**，不是对
事前声明的对账——这正是 goal 环节要消除的形态。第三世界起改由 goal 文档事前声明。

## 7. 范围与明确不做

- **只做最小模型**：单群体、无重组（`r=0`）、无基因转换（`f=0`）、
  无指数增长（`alphag=0`）、无迁移。
- **不做正向选择**：`ms` 是中性模型；选择动力学是第三世界的题目。
- **不改任何契约**：五类 Effect 分类学、`MechanismSpec` 形状、profile 版本零改动。
- **不扩 `staging.py`**：不提议为"重复某 stage 直到群体级条件成立"扩展调度声明。
- **不归档原始 draw log**：draw 日志与 `ms` 真实输出可从 vendored build（R1）
  加冻结种子三元组按需复现，记录的是取回路径而非逐字快照——它们是确定性 build 的
  瞬时产物，不是会消失的第三方资源（`vendor/ms/` 本身才是）。

## 8. 与已闭合判定的关系

不触及 v0.1a / v0.1b / v0.2 / v0.3-compare 的任何判定。本世界的两层判据独立成立，
其否定结果也不会回溯影响上述任何一条。

三条实现期澄清（均不改判据）记录在 `results/second-world/implementation-log.json`。

## 9. 复现方式

```bash
uv run --package newlife python -m newlife.conform.second_world_verdict --output /tmp/second-world
```

自己编译 vendored `ms`，只需要 `cc`。退出码非零即判据不成立。
预期：`"passed": true`、`"verdict": "ms_minimal_coalescent_reproducible"`、30 个复制品。
