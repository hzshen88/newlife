# 第十四个里程碑 —— 同一个世界跑在两个运行时上

- **goal**：`exloop` `goals/2026-09-03-newlife-cross-runtime-verification.md`（冻结 `ae8b081`）
- **预注册**：`preregistrations/2026-09-03-newlife-cross-runtime-verification.md`（冻结 `1b9257a`）
- **判定**：**H1** —— `results/fourteenth/summary.json`
- **goal 收尾判定**：`achieved`（见 goal §6，与 verdict 分开写）

---

## 1. 问的是什么

文献给了这个问题的准确名字：**verification** = 不同仿真引擎跑同一计算实验产出相同
结果（区别于 **reproducibility** = 科学主张能通过重放被验证）。文献同时说明它
**理论上该容易、实践上不容易**：SBML 社区跨五个 ODE 引擎做验证，是在「进一步改进了
模型、包装器和引擎本身」之后才得到结果；455 个 BioModels 里只有 51% 直接复现原文。

本项目的具体版本：`adapters/process_bigraph/` 752 行，**零个世界在用**。压力测试当年
判的是四个对抗性切片，不是一个真实世界。而 B（执行后端）这道接缝开不了，正因为
它的第二个 provider 是死的。

## 2. 结果

| 单元 | 结果 |
|---|---|
| U0 安全绳（harness 改收工厂后 RK 产物不变） | PASS，`results/fourth-world/summary.json` 逐字节不变 |
| U1 pb 跑完两个阶段 | 2101 / 2101 |
| U2 两条路径逐字节相同 | 2101 / 2101 |
| 负控（改坏 pb 的 store 写入） | 变红 —— 比对有判定力 |
| 用时 | 6.8s（IC-3 阈值 300s）——**计时只打印，不进产物** |

**process-bigraph 真的把 World 4 跑起来了，而且逐字节一致。**

## 3. 两个负控各自的信息

- **改坏 pb 写树时的 `time`** → `segsites` 9 → 0，比对变红。证明 pb 的写入在关键
  路径上：observer 读到的确实是 pb 存进去的东西，不是从别处拿的。
- **把声明里的阶段顺序颠倒** → **pb 照样跑对**（按接线依赖定序），
  **RK 直接抛 `TypeError`**（按 `spec.stages` 列表顺序）。
  **pb 在这一点上严格更强。** 这是本次唯一一条「留着 pb 的理由」的正面证据。

## 4. 事前预见的四处落差，实际命中三处

预注册 §5 事前列了四处，为的是让「H0 出现在别处」成为可识别的信息：

| | 事前预见 | 实际 |
|---|---|---|
| ① | `StructuralRewrite(before=None, after=<映射>)` 无 store handler | **命中**。补 `mapping-direct-structural`（8 行），属 F1 允许的接线 |
| ② | records 返回路径不同 | **命中**。RK 随 result 返回，pb 走 `take_trace()` |
| ③ | 阶段顺序来源不同 | **命中，但方向相反**——不是分歧来源，是 pb 的优势 |
| ④ | 容器类型被 schema 归一 | **未命中**。tuple→list 没走到产物里（observer 做了 `list(...)`） |

## 5. 事前未预见的那条：接缝的形状对不上

**这是本里程碑最重要的产出，比 H1 本身重要。**

`core/runtime.py` 是 B 的 Definition，四个操作是**从 `core/harness.py` 读出来的**——
harness 改动前只碰 `ReferenceKernel` 的四个方法。但那四个操作是一个 **pull 接口**：
逐阶段 `guarded_read` → `apply_batch`。

**pb 不是那个形状。** 它要先拿到整张图，再由自己的调度器按接线依赖驱动各节点——
一个 **push 运行时**。所以：

> **`adapters/process_bigraph/world_runtime.py` 不是 `WorldRuntime` 的一个实现。**
> 它是 `WorldSpec` 的**第二个消费者**，一条平行的执行路径。

后果要说清楚：**B 接缝在今天仍然只有一个 provider 满足它的 Definition。**
H1 说的是「同一份声明能被两个运行时跑出相同结果」，**不是**「接缝已经能容纳两者」。
按「一道接缝不许在少于三个 provider 时定型」的规矩，`core/runtime.py` 现在的形状
**已知是错的**——它把 RK 的 pull 形状当成了通用形状。下一次改它，方向由本次给出：
Definition 该规定的是**图与依赖**，不是**逐阶段读写**。

## 6. 顺手闭合与顺手发现

**闭合**：架构图标红的第①条（契约层焊死在一个运行时上）没了。`core/harness.py`
不再 import 任何运行时，`backend` 改为必填。中途试过「把 import 挪进函数体」，
被本项目自己的 import lint R6 当场咬住——它是对的。

**发现一：依赖声明自第八个里程碑起就是陈旧的。** World 4 从那时起跑在通用 harness 上，
但 `verdict_rot.DEPENDS_ON` 里 `fourth` / `eighth` 都没声明 `core/harness.py`。已补。

**发现二：第七世界的判定记录是烂的。** 重跑 `seventh_world_verdict` 得到
`enumerated_parts` 38（记录是 42）、4 个 phantom 部件全是 `MoranGenealogyWorld.*`
——那个类在第八个里程碑（`6bbc05c`）被删除，而第七世界的判定写于其前（`7e3b7a5`）。
**现在重跑得到的是 INVALID，不是已记录的 H0。**
`verdict_rot.impacted_by(['mechanisms/fourth_world/world.py'])` 正确返回包含
`'seventh'`——**第十三个里程碑造的工具回溯适用，抓住了第八个里程碑的破坏**，
只是当时没人跑它。本次**没有覆盖**那份已判定的产物（不在预注册范围内），单独立项。

**发现三：`tests/fourth_world/test_reuse.py` 有 5 个测试自第八个里程碑起一直红**
（同一根源：引用已删除的 `MoranGenealogyWorld`）。与发现二合并立项。

**发现四：对账器自己有一个假绿。**
`verify_doc_claims.py <doc>` **不带 `--ledger` 时，`@frozen` 检查根本不跑**，
打印「0 claims checked」并 exit 0——一份内容已被改动、冻结哈希已失效的 goal，
在这条命令下看起来是绿的。本次正是这样先看到绿、加了 `--ledger` 才看到 FAIL。
真实 gate 路径（`run_gates.py`）把 `--ledger` 列为必填，所以门禁本身没漏；
漏的是**人手工跑这条命令时**。与前四次同形：尝试失败/没跑 → 输出一个对自己有利的
样子。**本次未修**（不在预注册范围），记在此处。

**发现五：我自己差点制造一次判定腐烂。** verdict runner 第一版把 `seconds` 写进了
`summary.json`，重跑必不逐字节相同——正是第十一个里程碑测的那种腐烂，由我亲手制造。
收尾时重跑发现，改成只存布尔量 `within_time_budget`。产物现已两次重跑逐字节相同
（`8ab6ba0b…`）。

## 7. 规模估计对照

| | 事前估计 | 实际 |
|---|---|---|
| 实现行数 | 330 | **460**（+39%） |
| 判据条数 | 1 | 1 |
| 可判定的失败方式 | 1 | 1 |

**超出近五次的 ±25%。** 低估的成分是 `core/runtime.py`（估计里根本没有它——事前
以为「把 RK 的方法名抄一遍」，实际要处理 `_fast` 命名、必填 backend、import lint
三件事）与 pb 侧接线的类工厂。教训与第九、十个里程碑同形：
**成分列全不等于成分拆对。**
