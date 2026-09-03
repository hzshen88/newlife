# World 7：六个世界的 harness，有多少是能生成的

- **状态**：已判定（2026-09-03）。**H0 支持**——42 个部件里 **4 个**落不进冻结词表。
  **本产物已不可重新评估（`unevaluable`）**，判定本身仍然成立——见 §6。
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


---

## 6. 判定产物的腐烂与处置（2026-09-03 补记）

### 发生了什么

本判定写于 commit `7e3b7a5`。之后 commit `6bbc05c`（第八个里程碑）从 §3.2 的
`mechanisms/fourth_world/world.py` 里**删掉了 `MoranGenealogyWorld` 类**——那是它的
成果：通用 harness 把 World 4 的手搭 harness 吃到零。

于是今天重跑本 runner 得到：枚举 **38**、声明 **42**、4 个 phantom
（`MoranGenealogyWorld.__init__/_run_stage/reuse_trace/run`）、`coverage.ok=false`
→ **INVALID**。

**这正是 §5 第三条负控（「声明幽灵部件 → INVALID」）被非自愿地触发。**
机器在正常工作。

### 被什么发现

不是靠人看出来的。`conform/verdict_rot.py` 把它归为 **`unevaluable`**
（「重跑后判定为 INVALID——判据引用的对象已不存在」），而
`verdict_rot.impacted_by(['mechanisms/fourth_world/world.py'])` 回溯运行时
**正确返回包含 `'seventh'`**——工具抓得住，只是第八个里程碑当时没跑它。
（`impacted_by` 本身是第十三个里程碑才造的，所以第八个里程碑手上并没有这件工具；
真正缺的是**收尾时跑一次**这个动作，已补进 skill 收尾清单。）

### 处置：**保留 H0，不改声明，不覆盖产物**

四条理由，每条都在本次重新实测过：

1. **预注册的 IC-3 不管这件事。** 它的原话是「§3.2 的文件在**判定前**被改动」。
   第八个里程碑的改动在判定**之后**。一份预注册管的是它那一次运行，
   不是往后所有代码状态。

2. **实质结论未受影响。** 4 个 `unclassified` **全部**在
   `mechanisms/resource_foraging/world.py`，第八个里程碑没碰这个文件；
   被删的 4 个当初的归类是 `simulator`×3 + `frame`×1，**没有一个是 unclassified**。
   稳健性探测（把 4 条已不存在的部件从声明里去掉后重跑，**仅作探测、不写进
   `results/`**）：38/38 覆盖干净，`unclassified` 仍是同样那 4 个，
   **结果仍是 H0**。

3. **runner 的改动被排除。** 第十个里程碑把本 runner 的判定改走了 D 接缝
   （`decide`/`emit`/`exit_code`），`invalid`/`h1`/`h0` 的算法未动。
   **用 `7e3b7a5` 当时的 runner 跑今天的代码**，结果与新 runner 逐项一致
   （38/42、同样 4 个 phantom、同样 4 个 unclassified、INVALID）。

4. **`classification.json` 不是冻结输入。** 预注册 §3.3 明写
   「归类**不预先冻结**——那等于预设答案；冻结的是词表与规则」。它是那一次判定的
   声明快照。所以「更新它再重判」不是修复，是**另做一次实验**；
   而 §3.4 的 42 明写是「可行性测量，非确证运行」——**部件数从来不是结论**，
   `unclassified` 集合才是。

**覆盖成 INVALID 会毁掉一份有效发现。** `INVALID` 的含义是「这次运行没有判定力」，
而 `7e3b7a5` 那次是有的。正确的词是 **`unevaluable`**：不能再被重新评估，
**不等于当初判错了**。

### 明确不做

- **不给 `summary.json` 补 `code_commit` 字段。** 那会改动已记录判定产物的字节，
  破坏第十一个里程碑的复现基线；而且代码状态本来就可从 git 反推
  （`verdict_rot.verdict_commit('seventh')` → `7e3b7a5e…`，本次实测）。
- **不编辑 `classification.json`**（理由 4）。
- **不重判**。要重判就该走一遍完整流水线（新 goal、新预注册），
  因为被判定的代码已经不是同一份了。

### 顺带查出的 bug

做陈旧扫描时，`fourteenth` / `fifteenth` 两个世界**硬失败**：`verdict_commit` 把产物
路径写死成 `results/{world}-world/summary.json`，而第十个里程碑起的产物目录不带
`-world` 后缀。**硬失败救了它**——若当初写成「找不到就当没变动」，这两个世界会
永远显示「无变动」，成为下一次腐烂的温床。已修为两种命名都试、都没有则硬失败。
