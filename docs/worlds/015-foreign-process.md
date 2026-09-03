# 第十五个里程碑 —— 接一个第三方 process

- **goal**：`exloop` `goals/2026-09-03-newlife-foreign-process.md`（冻结 `be047cf`）
- **预注册**：`preregistrations/2026-09-03-newlife-foreign-process.md`（冻结 `8d65582`）
- **判定**：**H1** —— `results/fifteenth/summary.json`（`a4f92066…`，两次重跑稳定）
- **goal 收尾判定**：`achieved`（**成色降级**，见 §5）

---

## 1. 先说负面结果：已发布的生态包装不起来

按「能被一次几秒的运行证伪的预测，先跑那次运行」，冻结 goal 之前先试了**真正独立的**
Vivarium-2 生态包：

| 包 | 版本 | 结果 |
|---|---|---|
| `biosimulator-processes` | 0.3.19 | `ImportError: cannot import name 'ProcessTypes' from 'process_bigraph'` |
| `vivarium-interface` | 0.0.5 | 同一处，同一错误 |

`ProcessTypes` 在**任何**能与 `bigraph_schema` 1.6.0 配对的 pb 版本里都不存在
（实测 1.8.3 / 1.8.2 / 1.8.0 / 1.7.1 / 1.5.0 / 1.4.18；0.0.28 因 `bigraph_schema.registry`
缺失根本装不起来）。**两个包都没有声明 pb 的版本下界**——安装静默成功，import 才炸。

> **「接上 pb 就接上了它的生态」这句话，今天不成立。**

这与文献一致：SBML 跨引擎验证需要「改进模型、包装器和引擎本身」三样一起动。
所以本里程碑改用 `process_bigraph.processes` 里 pb 自带的领域 process
（相对 newlife 仍是第三方代码）。**未安装那两个包**——已证装不起来，再装是纯成本。

## 2. 结果

接的是 `process_bigraph.processes.growth_division.Grow`，**源码零改动、不子类化覆写
`update`**。

| 单元 | 结果 |
|---|---|
| V1 第三方未被改动 | 仍定义在 `process_bigraph.processes.growth_division`，位于 site-packages |
| V2 忠实性：与**裸 pb**（不 import 任何 newlife）同配置 | 轨迹逐字节相同 |
| V3 正控 | 质量按每 tick `mass*rate*interval` 增长 |
| V4 负控甲：代写声明 `own` 在另一条路径 | `CommitAuthorityError`，状态不变 |
| V5 负控乙：`allowed_effects` 不含 `StateDelta` | `CommitAuthorityError`，状态不变 |
| 元负控：同一份错误声明**绕开契约** | **不被拒** —— 拒绝确实是契约干的 |

**V2 是关键**：包装若改变了它的行为，那就不是「未经修改地接进来」。

## 3. 接法

`GuardedProcess.update` 本来就是 `propose → stage → lower`，校验在 `stage`。
所以适配器只实现 `propose`：实例化第三方类 → 调它的 `update` → 把返回的**端口键**
引擎 update 按声明表翻成**路径键** `StateDelta` → 交回 `Proposal`。
**第三方的输出只能经 `stage` 进入 store，没有旁路。**

端口（`inputs()`/`outputs()`）**向第三方要**，不由我们重述。

## 4. 判定之后补的那道守卫

判定录完之后，把预注册 §5 事前声明的那一点钉了一下：**把代写的算符从 `add` 填成
`set`**。结果是——**产出完全相同的轨迹，没有任何东西报警。**

追下去：`lower_effect` **确实**把 `operation` 映射成 `OP_SET` / `OP_ADD`
（`core/lowering_contract.py:74`），丢失发生在 **store handler**：`_sum_float_add`
假定进来的是 ADD，却从不校验。而 `_budget_proposal_projection` 与
`_resolved_position_envelope` **本来就有这个校验**——同一个仓库里，正确的写法有两处，
`StateDelta` 那几个 handler 漏了。

已补齐 5 个（`integer-count` / `sum-float-add` / `map-direct` / `sum-float-set` /
`list-direct`）。填错的算符现在硬失败。**四份已判定产物（fourth / eighth /
fourteenth / fifteenth）在修复后逐字节不变**，零回归。

**顺序是刻意的**：先把判定录完，再修。判定之后发现的缺陷不许倒回去改判定所依据的代码。

## 5. 成色必须降级的那一点

预注册 §5 事前就写了，这里如实兑现：

**端口 → (路径, 算符) 那张表只能由我们代写。** 第三方两处信息都不提供——
`outputs()` 只说类型不说位置，`update()` 的签名说不出返回的是增量还是覆写。

对照 **FMI**：那里的答案是**接口描述由模型作者随实现一起交付**，工具才敢在不看内部
的前提下接。这里没有那个东西。

> **H1 证明的是「契约对被代写的声明有强制力」，不是「第三方生态可以安全地接」。**

§4 的守卫把「算符填错」从**静默**变成了**硬失败**，这是真的收窄。但
**「路径填对了但填的是别人的路径」这类错误，只有当那条路径已被他人 `own` 时才会被抓**
——填一条无人认领的路径，契约不会说话。这是今天的边界。

## 6. 规模估计对照

| | 事前估计 | 实际 |
|---|---|---|
| 实现行数 | 345 | —— |
| 判据条数 | 1 | 1 |
| 可判定的失败方式 | 1 | 1 |

## 7. 途中的两处自我纠正

- **V3 第一版用 `(1+rate)**k` 做期望值**，与迭代累乘的浮点末位不同 → 判据算不出
  同一个数，**本身就是无效判据**。改为逐 tick 迭代，这才是预注册 V3 的忠实编码。
  同一形状本项目已犯过两次（「用一个检测不出任何东西的变异去判定通过」的镜像）。
- **对照组原放在 `conform/`**，被 import-lint 规则 2 咬住（vendor import 只许在
  adapter 内）。「对照组要用裸 pb」与该规则的交点就是
  `adapters/process_bigraph/bare_control.py`；runner 改为**零 vendor import**，
  第三方类由点分路径字符串解析。**规则冲突时先找交点，别给自己开例外。**
