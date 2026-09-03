# World 7：六个世界的 harness，有多少是能生成的

- **状态**：已判定（2026-09-03）。**H0 支持**——42 个部件里 **4 个**落不进冻结词表。
- **证据**：`results/seventh-world/summary.json`（`verdict: "H0"`）
- **verdict runner**：`packages/newlife/src/newlife/conform/seventh_world_verdict.py`
- **预注册**：exloop `preregistrations/2026-09-03-newlife-harness-generability.md`，
  冻结于 `c10dcb3`，`prereg.sh audit` PASS
- **回溯审计，非新世界**。目标是产出通用 harness 的规格，**本里程碑不建 harness**。

---

## 1. 结论

四个世界的 harness 共 **42 个顶层部件、872 行**。按 Zeigler 的 DEVS 三分
（model / simulator / experimental frame）加本项目补的 `rng`：

| 类 | 部件数 |
|---|---|
| `simulator` | 21 |
| `frame` | 12 |
| `rng` | 3 |
| `model` | 2 |
| **`unclassified`** | **4** |

**词表不封闭 → H0。** 而且落不进的那 4 个恰好聚成**两种能力**：

### 1.1 数值复现（3 个部件）

`_julia_simd_sum` · `julia_array_sum` · `julia_matrix_sum`——复现 Julia 的 SIMD 浮点
求和顺序。它不是生物学（`model`）、不决定执行顺序（`simulator`）、不是观测（`frame`）、
不是抽样（`rng`）。**它是「与参考实现逐位一致」这件事本身**，而 DEVS 三分里没有这一类。

原因很实在：World 1 的判据是「对 Julia 录制逐位精确复现」，浮点求和顺序因此成为判据的
一部分。**任何以「逐位复现另一个实现」为判据的世界都会长出这类代码。**

### 1.2 运行时契约强制（1 个部件）

`_validate_world_invariants`——越界即抛 `WorldProtocolError`。同样落不进四类。

**这一条正是本项目的痛点 P2**（「证据纪律靠治理而非运行时」的解法）。
**DEVS 的三分里没有它，因为 DEVS 不关心「谁有权写什么」。** 这不是 DEVS 的疏漏——
是本项目相对经典模拟架构**多出来的那一层**，也正是它存在的理由（`proposal.md` §1.5：
把 ParaLife 靠仓库治理扛着的证据纪律下沉为运行时强制的代码）。

## 2. 通用 harness 的规格（本里程碑的产出）

**五块，不是三块：**

| 块 | 部件数 | 现状 |
|---|---|---|
| `simulator` 阶段执行与 tick 循环 | 21 | `staging.py` 覆盖了阶段编排一段；三个世界各自手写了 `_run_stage` |
| `frame` 观测收集、replicate 迭代、入口 | 12 | **完全没有对应物** |
| `rng` 命名流派生与装配 | 3 | proofroot/EvidenceCore 已有，未被 harness 化 |
| **数值复现** | 3 | 无——DEVS 未名 |
| **运行时契约强制** | 1 | 有实现（`authority`/`evidence`），未被 harness 化；即 P2 |

**最大的一块是 `simulator`（21/42），而它正是 `staging.py` 本该覆盖的地方**——
三个世界各自手写了一遍 `_run_stage`。

## 3. World 3 的裁定（与 verdict 分开）

**S2 成立：World 3 根本没有 harness。** 它既不装配 `ReferenceKernel`、也不注册机制、
不跑阶段；verdict runner 直接调机制函数。

**它是 P3 唯一「成立」的实例，但代价是完全不接入 registry 与引擎。** 这不是 P3 达成，
是绕开了 P3 要解决的问题——如实记在这里，不计入 P3 进度。

## 4. 边界

- **DEVS 是离散事件系统的形式化，newlife 不见得处处是那个形状**（design §3 事前声明）。
  §1.2 的结果表明这个假设确实不完备——**但不完备的方向是本项目多一层，不是 DEVS 错了**。
- **归类是声明的，不是机械的**（预注册 §3.3）。判一个函数属 `simulator` 还是 `frame`
  是判断；工具保证的是**漏项不可能**，不是替人判断。42 条归类各自附了理由，可复核。
- **`ForagingWorld.__init__` 等少数部件跨类**（既装配引擎又建 RngBank），按主体归类并
  写明，未触发 IC-2。

## 5. 负控

四条，全部按预期翻转：把 4 个 `unclassified` 硬塞进 `simulator` → **H1**（证明 H0 依赖
归类而非 bug）；漏声明一条 → **INVALID**；声明幽灵部件 → **INVALID**；
**偷偷用词表外的取值 → INVALID**（这条防的正是「扩词表就能永远 H1」）。

verdict runner **独立重做枚举**，不读 design 阶段那份台账——判定不能建立在被判定方
自己的输出上。
