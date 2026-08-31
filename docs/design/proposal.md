- **注**：本文件自 v0.6 起是活版本，随本仓库演化。冻结母本（v0.6，2026-08-30）在 exloop 探索档案：`exloop/explorations/2026-08-29-biological-sim-architecture/artifacts/biosim-library-proposal.md`。

# BiologicalProfile 库建设方案

- **日期**：2026-09-01　**状态**：v0.10（v0.1a/v0.1b 均已判定：H1 支持，`compatible_for_frozen_slices_v1_lowered` 与 `staging_declarable_for_frozen_slices`；**v0.2 gate 已关闭**：World 1 = Resource Foraging 双条件 L2 逐位精确复现，`results/v0.2/gate.json` `passed: true`；**v0.3 compare 主线已判定**：H1 支持，`causal_attribution_declarable_for_world1_pairs`，预注册冻结于 exloop `322a8dc8`，实现见 `packages/newlife/src/newlife/core/compare.py`；**第二世界（`ms` 最小溯祖模型）已判定**：H1 支持，`ms_minimal_coalescent_reproducible`，预注册冻结于 exloop `c450072`，实现见 `packages/newlife/src/newlife/mechanisms/second_world/`）
- **性质**：完整建设方案——从背景、证据、架构到里程碑。自含背景，不依赖对话上下文。
- **决策记录**：[`architecture-discussion-record.md`](architecture-discussion-record.md)（另一场对话的架构讨论）
- **正式证据**：[`../process/03-formal-pressure-test.md`](../process/03-formal-pressure-test.md)

---

## 1. 背景与动机

### 1.1 根问题

如何设计一个充分解耦、可扩展、可承载多类生物与人工生命模型的模拟系统？

2026-08-29 至 08-30 的探索把这个问题收窄成一个可检验的问题：**四项基础契约能否表达四个对抗性切片，Process-Bigraph 能否在不破坏模块边界的前提下承载同一组切片？** 该问题已经以预注册压力测试的方式回答（§1.3）。本方案回答它的后继问题：**如果把"可以采用"的判定落成真正可用的代码，这个库长什么样？**

### 1.2 文献谱系：两条脉络都没提供科学语义层

- **Bigraph**（Robin Milner，CONCUR 2001；专著 *The Space and Motion of Communicating Agents*，2009）生于普适计算与移动交互，理论目标是统一并发演算（place graph 表层级嵌套 + link graph 表通信连接）。生物学是 2008 年经 Stochastic Bigraphs 侧门进来的应用，不是理论自带的部分。详细谱系见 [`../process/04-bigraph-lineage.md`](../process/04-bigraph-lineage.md)。
- **Process-Bigraph**（Agmon & Spangler，arXiv:2512.23754；Agmon，arXiv:2408.00942）自称是 Milner bigraph 的"进化扩展"：把 link graph 换成**带类型端口的 process 连到带类型 store**，加上编排模式（multi-timestepping 离散事件协同仿真、workflow DAG、`_add`/`_remove`/`_divide` 结构重写）和类型系统（`bigraph-schema` 的类型注册与 reconcile/apply 合并语义）。它放弃了 Milner 的形式演算核心（RPO、bisimulation），自称 "compositional runtime and protocol"。
- **关键事实**：两代框架都只规定"积木如何组装、如何运转"，不规定"谁可读写什么、贡献何时完整、什么算科学证据"。默认 reconcile（浮点求和、overwrite last-writer-wins）是计算语义不是所有权语义；端口限制可见形状但不保证只读；RNG 没有命名流契约。见 [`vivarium2-api-survey.md`](vivarium2-api-survey.md)。

### 1.3 压力测试结论（2026-08-30 冻结）及其边界

四个异构切片（Avida-like 执行预算、CC3D/PhysiCell-like 耦合力学与分裂、SLiM-like hook 权限、连续时间随机事件）在双实现（最小参考内核 + Process-Bigraph 1.8.3）下通过冻结的逐字段比较：

| 判定对象 | 结果 |
|---|---|
| 四项契约（`StateClaim`、`MechanismSpec`、五类 `Effect`、`Resolver`） | `compatible_for_frozen_slices` |
| Process-Bigraph 1.8.3 | `compatible_runtime_with_mandatory_profile` |
| 总体决策 | `adopt_process_bigraph_only_with_mandatory_versioned_profile` |

计数：8/8 target-slice cell、16/16 正向执行、18/18 负例、1/1 Transfer 微夹具、66/66 完整测试、预注册审计 PASS（0 warning）。机器判定以 [`pressure-test/results/summary.json`](pressure-test/results/summary.json) 为准。

**必须如实写明的三个边界**（对本方案的工作量估计有直接影响）：

1. 判定证明的是"Effect 声明 + 机制手写的 runtime update 能产出一致 trace"。**"Effect 载荷本身信息量足以机械推导 runtime update"（lowering 完备性）在两个实现里都从未存在过**——参考内核的 `_apply_to` 直接消费 Effect 对象；Process-Bigraph 一侧的机制返回手写的 `engine_update` 字典（`vivarium_cases.py` 的 `{"budget": value}` 等），`GuardedProcess.update()` 原样放行。见 §5.2。
2. 判定只对**契约 v1**（五类 Effect 分类学）成立。任何载荷扩充或新增类别都超出冻结判定的适用范围，必须按 §5.6 的扩展程序重新版本化。
3. 命名 RNG 流在测试中是"注入预定抽样序列"实现的；真实随机数实现与跨机制命名流 discipline 未被测试（列入 §8 风险）。

### 1.4 为什么值得做：配置化与 AI 可参与性

这条探索的后续讨论确立了三层判断：

1. **组装现有积木 → 配置文件**。profile 把"谁可读写什么"从代码约定升级成可声明数据；四切片已证明这条路能走通。
2. **新机制 + 已有动力学 DSL → 部分配置化**。反应网络/ODE 类动力学若以类型化 Effect 注册进引擎（`Core.register_type()` 挂点），也可配置化；ABM 行为目前没有公认 DSL，仍是代码。
3. **真正新的机制语义 → 永远是代码**（新 Effect 类、新协议）。这是特性：Effect 分类学封闭是"什么算合法科学操作"可审计的前提——但封闭必须与**合法的扩展程序**（§5.6）一起存在，否则封闭只是未定义的禁区。

配置化的红利在 AI 参与：受约束的生成空间 + 廉价可验证的反馈（schema 校验在边界拦截）+ **可比性**。可比性不是天然成立的——"两次运行的差异必须只来自声明的差异"是一条需要专门兑现的红线，因此本方案给它一个正式落点：`core/compare.py`（§5.7），而不是把它留在动机论述里。

### 1.5 从 ParaLife 到 newlife：痛点清单（真实动机）

本方案的动机有一半来自文献（§1.2），另一半来自用户自己的第一代系统。[`~/Projects/paralife`](../../../../../paralife/README.md) 是一个已运转的 Julia 三包 monorepo——Parreact（分子）/ Parcells（细胞）/ Parworlds（种群）+ EvidenceCore（信任核心：`derive_stream_seed(version, root_seed, name)` 版本化命名流派生、RngBank、RunPhase、冻结 run binding）。其 README 原则"One world answers one specific question"正是讨论记录决策规则第 1 条的出处；证据契约是它的稳定中心（"The stable center is the evidence contract, not a generic Life/Cell/Agent base class"）。

所以 newlife 的正确定位是**第二代重建**：把 ParaLife 靠仓库治理扛着的证据纪律**下沉为运行时强制的代码**，同时补上 ParaLife 刻意不做的事——**机制组合**（三包 "share no biological mechanism and do not form a single connected multi-scale model"，互不 `using`，跨尺度只准走冻结 artifact）。

设计压舱石（每条 v0.1/v0.2 设计决策必须能指回一条真实痛点，指不回的即第二系统效应在说话，一律缓建）：

| # | 痛点（ParaLife 中的表现） | 对应契约/模块 | 什么算解决 |
|---|---|---|---|
| P1 | 机制跨包不可组合：三包互不 `using`，跨尺度组合靠人肉搬运冻结 artifact | 四项契约 + `mechanisms/` 注册表 | 同一机制可在 newlife 内跨世界组合，无需包间冻结文件 |
| P2 | 证据纪律靠治理而非运行时：ADR-S3 人工签核、文件冻结、`check_architecture.jl` 脚本——违反只能事后发现 | `authority.py` / `evidence.py` / lowering 唯一写入路径 | 权限越界与旁路写入在运行时被拒绝；治理脚本降级为补充而非唯一防线 |
| P3 | 每个世界手搭 harness：多 Composite 因果连线、抽样注入、trace 拼装均为手工 | `staging.py` + conform + RNG 流 | 新世界以配置 + 机制声明接入，无 harness 代码 |

证据状态：P1、P2 已由 ParaLife README 与 `EvidenceCore.jl` 直接核实；P3 已由用户确认（2026-08-30），旁证为压力测试 harness 的手工连线。**痛点清单三/三条闭合，自此成为设计压舱石的正式基线**：v0.1/v0.2 每个设计决策必须能指回其中一条，清单之外的通用化一律缓建。

---

## 2. 目标与非目标

### 目标

1. **独立版本化的 BiologicalProfile 库**：承载 path authority、只读别名保护、Effect 验证、贡献完整性与规范 trace。命名 RNG 流**不在**已验证能力之列，其实现与测试方案在 v0.1 预注册中一并解决（§8 风险 4）。
2. **窄依赖边界，且由打包机制强制**：`process-bigraph` / `bigraph-schema` 只出现在 adapter 层并作为**可选 extras**（`newlife[process-bigraph]`）；裸安装零第三方依赖，参考内核是默认后端。依赖边界从纪律变成机制。
3. **契约即数据**：所有声明（权属、机制 spec、Effect）JSON 可序列化，实现与定义分离。
4. **一致性测试即验收门，分两层**：契约级测试（语言无关：声明 + 规范 trace 字节比对 + AST/import-lint）是公共协议；宿主特定洞清单（每语言/实现自行推导，如 Python 的可变引用别名）不是公共协议。conform 自身带版本号，并作为第四个版本写入运行 manifest（§5.5）。
5. **应用层配置化**：世界组装与实验协议是数据，应用代码不直接触碰 runtime——以 import-lint 落地，不停留在意图。
6. **可比性有专门组件**：`core/compare.py` 兑现"同声明 → 同 trace、单声明 delta → 可归因差异报告"（§5.7）。

### 非目标（明确不做）

- 不做生物真实性、涌现能力或校准结论。
- 不做规模/吞吐优化与分布式/GPU 执行（列为未来边界）。
- 不复刻完整 Vivarium 2 生态（其 wrapper 与研究项目仅作受控第三方适配的参考）。
- 不在本方案范围内设计动力学描述语言（SBML 类第二层 DSL）——列为独立后续探索。
- 不追求普适 SOTA；runtime 选择以"下一个世界问题"为准，不以抽象偏好为准。
- **不把四个对抗性切片当作首批生产机制**：切片是表达力反例，不是任何人想回答的科学问题。机制注册表的启动以"选定第一个世界问题"为显式门槛（§7 v0.2 gate）。

---

## 3. 总体架构

### 3.1 分层

```text
┌─────────────────────────────────────────────────────┐
│ 模拟应用层：世界组装 + 实验协议（配置数据）          │
│   初态 · 参数 · 干预窗口 · 对照 · 停止条件           │
├─────────────────────────────────────────────────────┤
│ 机制层：mechanisms/ 注册表（以第一个世界问题启动）    │
│   每个机制 = MechanismSpec 声明(JSON) + 版本化代码   │
│   家族：环境与空间 / 遗传与变异 / 发育与表达 /        │
│         个体运行 / 相互作用 / 生命周期（可交叠）      │
├─────────────────────────────────────────────────────┤
│ BiologicalProfile 核心（本库，裸安装零第三方依赖）    │
│   authority · 别名保护 · Effect 验证 · Resolver ·    │
│   lowering 语义契约 · 规范 trace · compare           │
├─────────────────────────────────────────────────────┤
│ runtime adapter 层（可替换；各自携带 lowering 实现   │
│ 与因果阶段编排）                                     │
│   reference_kernel（默认） │ process_bigraph（extra）│
├─────────────────────────────────────────────────────┤
│ 第三方 runtime                                       │
│   process-bigraph 1.8.3 → bigraph-schema 1.6.0       │
└─────────────────────────────────────────────────────┘
```

### 3.2 四平面与模块的映射

讨论记录确立的四个平面（详见其架构图 [`latest-biological-simulation-architecture.svg`](latest-biological-simulation-architecture.svg)）：

| 平面 | 落点 | 不负责 |
|---|---|---|
| 生物机制 | `mechanisms/` 注册表 | 直接修改全局状态、自定提交次序 |
| 管理 | 应用层（world lifecycle 配置） | 产生生物学 Effect |
| 实验协议 | 应用层（experiment 配置） | **决定调度顺序**——见 §5.8 |
| 证据 | `core/trace.py` + `core/manifest.py` + `core/compare.py`（原语来自 proofroot） | 反向驱动未声明的模型变化 |

### 3.3 设计原则

1. **core 零第三方依赖，且由打包强制**。契约是声明式协议：定义用中立数据格式发布，实现按语言各自提供。契约内容语言无关；但**负例清单与宿主语言执行语义相关**，移植时须按目标语言重新推导（conform 的 host 层，§5.4）。
2. **lowering 是唯一写入路径，且 lowering 实现属于 adapter**。core 只定义 lowering 必须保持的语义契约（中间表示 + 不变量清单）；update 的形状取决于目标 store 的注册类型语义，那是 adapter 层的知识（§5.2）。
3. **mechanism 与连线分离**。模块内是可独立替换、版本化、带局部不变量的机制；连线只表达显式状态声明、Effect、时间/因果依赖、拓扑变化与证据关系，不得暗藏生物学规则。
4. **新能力先以显式版本化 mechanism 进入**；跨多个世界重复出现且经测试后才提升为通用模块。
5. **对顺序敏感的科学规则显式写进 profile 的因果阶段，因果阶段声明由 MechanismSpec 的调度声明驱动、由 adapter 编排**——不落在应用层（调度顺序是科学语义，见 §5.8）。
6. **引擎升级 = 重跑 conform**。`process-bigraph` 的版本升级以 conform 套件全绿为门槛，这是验收门的又一个用途。

---

## 4. 包结构

定名 **`newlife`**（2026-08-30 用户确认；替代此前的工作名 `bioprofile`）。选名理由与配套决定：

- 名字不需要与功能对应（可检索、不撞名、不误导三条才是硬约束）；愿景名比实现名更经得起平台的成长——`bioprofile` 只描述 profile 一层，平台长大后名字会显窄。
- PyPI 已核查可用（2026-08-30，`pypi.org/pypi/newlife` 404）；**发布前待办**：GitHub 同名仓库检索与 COMBINE/BioSimulators 生态重名检查。
- 已知代价，接受：检索噪音（"new life" 是高频词，SEO 靠组合词经营）；品牌承诺超前于 v0.1 内容（契约校验引擎）的落差期。
- 结构配套：**包名是品牌，模块名保持描述性**——`newlife/core/contracts.py` 等；文档 tagline："a verifiable profile layer for composable biological simulation"。

```text
newlife/                            # monorepo（uv workspace，双发行版）
├── packages/
│   ├── proofroot/                  # 信任核心：零依赖、零领域语义（定名见下）
│   │   ├── src/proofroot/
│   │   │   ├── rng.py              # D1 现行编码 evidencecore-rng-v1 + D4 bank 语义不变量（§5.10）
│   │   │   ├── phase.py            # D2 RunPhase + 终态判定；D5 证据分层词汇表（安全方向默认）
│   │   │   ├── canonical.py        # 规范序列化 spec + canonicalization 函数（§5.9 移居于此）
│   │   │   └── vectors/            # 跨语言测试向量（EvidenceCore.jl 作 oracle 生成）
│   │   └── README.md               # 独立入口：spec、向量、与 EvidenceCore.jl 的血统声明
│   └── newlife/
│       ├── pyproject.toml          # 依赖 proofroot；process-bigraph 走 extras
│       ├── src/newlife/
│       │   ├── core/
│       │   │   ├── contracts.py    # 四契约 —— dataclass + 手写最小校验器（选型理由见 §5.3）
│       │   │   ├── authority.py    # 路径权属、plane/role authority、贡献完整性、只读别名保护
│       │   │   ├── lowering_contract.py  # Effect→update 语义契约：IR + 不变量（runtime 无关）
│       │   │   ├── trace.py        # Effect 类型化 trace schema + RNG 流身份（构建于 proofroot 原语之上）
│       │   │   ├── manifest.py     # 五版本 manifest 组装（形状归 newlife，理由见 §5.10）
│       │   │   ├── compare.py      # 可比性引擎（§5.7）
│       │   │   └── errors.py       # 冻结的异常分类
│       │   ├── adapters/
│       │   │   ├── reference_kernel/   # 默认后端；含纯 Python xoshiro（零依赖确定性生成器）
│       │   │   └── process_bigraph/    # extras 安装：wrapper（无自由 engine_update）+ lowering + staging
│       │   ├── conform/
│       │   │   ├── contract/       # 语言无关公共协议：声明 + trace 字节比对 + AST/import-lint；带版本号
│       │   │   └── host/           # 宿主特定洞清单：每语言/实现自行推导，不入公共协议
│       │   └── mechanisms/         # 机制注册表（v0.2，以第一个世界问题为启动门槛）
│       └── examples/first-world/   # 仅在 §7 v0.2 gate 通过后创建
└── docs/
```

**发布形态与入口设计**（单 monorepo 的认知负担消解）：Python 用户的正门是 PyPI——`proofroot` 与 `newlife` 是两个独立发行版，安装彼此解耦；GitHub 侧三条缓解：① 子目录树链接（proofroot 的 `project.urls` 指向 `tree/main/packages/proofroot`）；② 顶层 README 顶部双包表格（ParaLife 单 repo 多包先例）；③ GitHub topics 双标签。拆库判据依旧跟消费者走：proofroot 有了真实采用社区那天，`git subtree split` 连历史完整拆出，PyPI 名与 API 不变。

**信任核心包定名 `proofroot`**（2026-08-30 用户确认）。理由：五生态核查（PyPI / crates.io / npm / Julia General / GitHub）**全部干净**——PyPI/crates/npm 均 404、Julia General 零命中、GitHub 零同名仓库；含义不是比喻而是字面——一切随机性从 `root_seed` 派生，一切证据从规范 trace 根可比对，且暗合 Merkle proof root 的审计联想；与 `newlife` 成对：愿景名在上生长，信任名在下扎根。同批核查淘汰：`reprospec`/`seedwright`（GitHub 有语义近亲：integrity-checked evidence bundles、确定性生成平台各一）、`runproof`/`stemma`/`certus`（PyPI 已被占）。四生态扫描自此固化为所有新名字的锁定前置流程（自 `biosim` 撞名起）。注意：编码标识符 `evidencecore-rng-v1` 是冻结的字节级 ID，与包名解耦，更名不影响规范；ParaLife 内部的 EvidenceCore.jl 保持原名（oracle，见 §5.10）。

---

## 5. 关键设计决定

### 5.1 窄依赖：供应商类型不进核心，且由打包强制

Profile/机制契约不进口 `Process`、`Composite` 等供应商类型；`process-bigraph` 的 import 只出现在 `adapters/process_bigraph/` 内，并声明为 optional extra。裸安装只有参考内核可用，"core 零依赖"由安装结构保证而非口头约定。import-lint（禁止 core/应用层出现引擎模块）作为 conform 契约级测试的常驻部分和 CI 门。

### 5.2 0 号任务：lowering 完备性是一场新实验，不是迁移

压力测试代码核实的事实（2026-08-30 复核）：

- 参考内核的 `_apply_to`（`reference_kernel.py`）直接消费 Effect 对象——它不需要 lowering；
- Process-Bigraph 一侧的机制在 `propose()` 里**手写** `engine_update` 字典（`vivarium_cases.py:182` 的 `{"budget": value}`、`:678` 的 `{"genome": "B"}`），`GuardedProcess.update()`（`vivarium_profile.py:186`）原样放行——机制侧存在旁路；
- 因此"从已验证 Effect 机械地生成 runtime update"在两个实现里都从未存在过。压力测试证明的是"Effect 声明 + 手写 update 能产出一致 trace"。

所以封闭旁路（决策记录方案 1：删除自由 `engine_update`）隐含的代价是一个**完备性证明**：Effect 载荷是否携带足够信息推导出每种 runtime 的 update。这不是搬运，是把 v0.1 从"迁移"变成"新实验"。三个已识别的难点：

1. **类型语义耦合**：reconcile 对数值默认求和、`Overwrite` last-writer-wins；同一个 `StateDelta` lower 成什么载荷取决于目标 store 的注册类型——schema 知识在 adapter 层。因此 core 只定义 lowering 语义契约（中间表示 + 不变量，如"总量守恒"、"目标路径与声明权属一致"），每个 adapter 自带 lowering 实现，conform 验证两个 adapter 的 lowering 对同一 Effect 序列产出一致 trace。
2. **"每类 Effect 一个纯函数"不成立**：`Contribution` 的提交依赖 Resolver 对贡献者集合完整性的核验（跨 Effect、tick 内有状态）；`Transfer` 的原子性横跨两条路径。lowering 是有状态的批处理语义，不是逐 Effect 的映射。
3. **冻结判定的版本边界**：若 lowering 完备性倒逼 Effect 载荷扩充或新增类别，则触发 §5.6 的扩展程序，旧判定不得静默继承。

**v0.1 的正确立项方式**（符合本仓库精神）：把"五类 Effect 的现有载荷足以机械推导两个已测 runtime 的 update"当作下一个**可否证的预注册问题**——预注册其判据与否定条件，再做实现。否定结果（需要扩载荷/增类别）本身是有价值结论，走 §5.6 程序，不是项目失败。

### 5.3 契约即数据；校验器的选型

`contracts.py` 全部声明类型可序列化为 JSON。校验器选**手写最小校验器**：引入 `jsonschema`/`pydantic` 会破坏 core 零依赖；手写校验器是新增待测表面，因此它与四契约一起被 conform 契约级测试覆盖（正例 + 畸形声明负例），缺陷风险受控。若未来依赖约束放宽，可替换为 pydantic 并重跑 conform。

### 5.4 conform/ 分两层，带版本号，AST 审计是常驻 CI 门

- **`conform/contract/`（公共协议）**：语言无关——给定声明与 Effect 序列，规范 trace 逐字节比对；AST/import-lint（禁止 adapter 之外 import 引擎私有模块、禁止 `process_bigraph` 出现在 core/应用层）。任何 adapter 进库先过这一层。
- **`conform/host/`（宿主洞清单）**：每个语言/实现自行推导——Python 的可变别名、JS 的原型污染、Rust 无此问题等。这不是公共协议，替换语言时重推导。
- **既有 66 项的去向**：负例中相当一部分依赖 `Proposal.engine_update` 这个即将删除的结构，旁路封闭后它们不是"迁移"而是**重新推导**；总计数大概率改变。v0.1 验收措辞用"重推导后的契约级套件全绿 + AST 审计通过"，不用"66 项全绿"。
- **版本号**：conform 契约级套件带版本，写进运行 manifest（§5.5 第四版本）。

### 5.5 版本与证据 manifest（五个版本）

一次运行的可复现性由**五个**版本共同决定：profile 版本（semver）、机制版本（各自独立）、引擎版本（lock 钉死）、**conform 契约级套件版本（adapter 通过的是哪一版验收门）**、**proofroot 版本**（信任核心与其测试向量集的版本）。全部写入运行 manifest——manifest 的组装形状归 newlife（`manifest.py`），proofroot 只提供原语；与规范 trace、RNG 流身份一起构成证据平面的输出。

### 5.6 Effect 分类学的合法扩展程序

分类学封闭（判定条件"无第六 Effect"）与扩展程序必须一起定义：

1. 扩展需求只能来自 lowering 完备性实验或新世界问题的具体失败，不能来自抽象偏好；
2. 契约版本号递增（v1 → v2），变更以新增预注册记录（问题、判据、否定条件、切片）；
3. conform 契约级套件相应升版并重跑；
4. 冻结判定 `compatible_for_frozen_slices` 显式标注适用范围为契约 v1；新判定不回溯覆盖旧判定，旧判定保留原文。

### 5.7 可比性引擎：`core/compare.py`

§1.4 的红线主张的兑现落点，两个方向：

- **正向（已证明的雏形）**：同声明 → 同 trace。压力测试已证明每 cell 两次执行字节一致——conform 契约级测试保留此性质（重复执行一致性），compare.py 消费同一机制。
- **逆向（v0.3 建设）**：给定两份只差 N 个声明的配置，产出可归因的差异报告——声明 delta ↔ trace delta 对账，把"两个模型的差异"压缩成干净的声明式 delta。这是 AI 闭环消融实验的直接前置件。逆向方向的判据（什么样的 trace 差异算"可归因"）**经第一个世界问题的消融校准后随 v0.3 预注册**（§7）——v0.1 里凭空冻结是时序倒置，大概率冻错。

### 5.8 因果阶段声明的归属

调度顺序是科学语义，实验协议平面不得拥有它（§3.2 平面表）。因此"阶段声明 → Composite 编排"的编译逻辑**属于 adapter 层**（`adapters/process_bigraph/staging.py`），由 MechanismSpec 的调度声明驱动；压力测试里 harness 手工的多 Composite 连线在库里由 staging 承载。应用层只能声明干预时间窗，不能重排因果阶段。这块由 v0.1b 独立预注册解决（§7）——它同样是 lowering 完备性的一部分（阶段信息能否从 MechanismSpec 声明推导）。

### 5.9 规范序列化 spec：conform/contract 的 0 号资产

跨语言的逐字节 trace 比对，经典死穴是浮点文本表示——Python 与 Rust/Julia 对同一个 float 的默认序列化不保证同字节。规则直接给定：

- **结构层**采用 RFC 8785（JCS）的现成部分：对象键按码点排序、UTF-8、无多余空白；
- **浮点用位模式绕过而不是祈祷**：trace 中数值比较字段以 IEEE754 位模式（hex）承载，人可读十进制仅作注释字段，逐字节比对只认 hex——位模式定义上一致，跨语言 shortest round-trip"通常一致但无保证"；
- 附一组**跨语言测试向量**（`-0.0`、次正规数、NaN 载荷等经典坑位）作为 spec 的可执行部分；
- 落点：**spec 与 canonicalization 函数移居信任核心包 proofroot**（§5.10）——它是语言中立的信任资产，不是生物 profile 的一部分；conform 契约级测试消费其测试向量。
- **生效时序（四轮评审裁决的 canonical 尺子坑）**：压力测试的冻结 trace 是用其 `normalize.py` 旧 canonical 形式产出的；若 v0.1a 判定改用新 spec（IEEE754 hex 浮点），字节比对会**平凡失败——那是格式差异，不是 lowering 错误**。因此：**v0.1a 的判定比较沿用压力测试原 canonical 形式**（裁判必须与产出 expected 的那把尺子完全相同）；新 spec 在 v0.1a 只用于 proofroot 自身的测试向量；trace 格式切换推迟到 v0.2 跨语言比对开工之前，切换时重跑 conform 契约级套件。第一个世界问题（Parworlds 冻结研究的 Julia 参考 vs Python 实现，§7）是新 spec 的第一个真实载荷。

### 5.10 信任核心 proofroot：切线、纪律与 oracle 治理

把证据层独立成包（用户提议，评审已核实可行性）不是第二系统效应：移植的是第一代**已验证的设计**（EvidenceCore.jl，被 Parcells/Parworlds 经实战使用），不是发明新通用性。但 EvidenceCore.jl 全文核实后，有三条修正决定落地方式：

**切线表**（按"有真实消费者拉动"逐项过；EvidenceCore.jl 章程注释只收"静默合并会破坏历史可复现性的分叉点"，其余刻意 package-local——第一代已经用实战判断过统一无收益的东西不再二次统一）：

| 进 proofroot v1 | 理由 | 留在 newlife |
|---|---|---|
| D1 现行编码（仅 `evidencecore-rng-v1`） | newlife RNG 裁决直接消费 | Effect 类型化 trace schema |
| D4 bank 语义不变量（声明制流、小写归一、名字正则、只前进不重播、种子快照即 provenance） | 同上 | compare（依赖 Effect 分类学） |
| D5 证据分层词汇表（exploration/confirmatory/unknown + "字段缺失一律 unknown、绝不默认 confirmatory"的安全方向） | newlife 的 exploratory/正式运行区分是现成消费者；最值得导出的通用治理资产 | manifest 组装（五版本形状是 newlife 的；第一代已判定 manifest 统一无收益） |
| D2 RunPhase + 终态判定 | 小而通用，manifest 引用 | authority / 契约（本就不在范围） |
| 序列化 spec + canonicalization 函数 + 跨语言测试向量（§5.9） | 新需求，ParaLife 无对应物，天然语言中立 | |

**两条纪律**（"不改进"与"不继承包袱"不冲突，前者管语义，后者管范围）：

1. **移植的语义逐字节不改**：`evidencecore-rng-v1` 现行编码 + D4 不变量 + D2/D5 语义，Python 实现与 oracle 产出逐位一致（向量对照测试）。
2. **只为 ParaLife 历史服务的兼容层一律不搬**：`parcells-rng-v1`/`parreact-rng-v1`/`parworlds-rng-v1` 三种 legacy 编码、`parse_phase` 的大写 legacy 拼写——它们的存在理由（历史 run 精确复现）不可移植，留在 EvidenceCore.jl 原地。

**合同边界在派生种子层**：种子派生是 SHA-256 上的字节定义，跨语言逐位可移植；但同一 UInt64 种子出发的随机**序列**依赖生成器（Julia 内建 Xoshiro），不可跨语言移植——EvidenceCore.jl 注释自己说破了："The derived stream seeds are what matter for reproducibility"。因此 spec 的跨语言一致性向量**验到 seed 为止**；生成器是宿主选择、写入 manifest（newlife 参考内核自带纯 Python xoshiro 以保零依赖确定性）。对 v0.2 gate 的直接后果见 §7 比对方法。

**oracle 治理（单一真相源）**：ParaLife **不迁移**——其各包 Project/Manifest 是历史实验依赖身份的一部分，动它无收益。EvidenceCore.jl **原地冻结**，继续为 ParaLife 历史服务，同时作为 oracle 生成新 spec 的测试向量。正确形态是 **"spec + 一个实现（Python，有真消费者）+ 一个 oracle（Julia，已存在）"**，不从第一天维护双实现；注册公共 Julia 包等真实 Julia 消费者出现再说（消费者计数规则同款）。

---

## 6. 许可与引用

- 上游 `process-bigraph` 与 `bigraph-schema` 均为 **Apache-2.0**。本库作为依赖引用（非 fork）；若发行物中包含拷贝/衍生的上游代码，须永久保留 Apache License 原文、copyright/专利/商标声明与 NOTICE，并在修改文件上标注变更。本库自有代码由本项目全权决定 license，无 copyleft 义务。
- 命名：不使用 "process-bigraph" 或 "Vivarium"（Apache-2.0 不授予商标）。定名 `newlife`：PyPI 已核查可用（2026-08-30）；发布前补 GitHub 同名检索与 COMBINE/BioSimulators 生态重名检查，与对上游商标的谨慎同标准。
- 学术引用：Agmon & Spangler（process-bigraph，arXiv:2512.23754）、Agmon（Foundations，arXiv:2408.00942）、Vivarium 引擎（Bioinformatics 2022）、Milner（2001/2009）。完整出处见 [`../process/04-bigraph-lineage.md`](../process/04-bigraph-lineage.md)。

---

## 7. 里程碑

| 里程碑 | 内容 | 验收 |
|---|---|---|
| **v0.1a lowering 完备性**（✅ 预注册实验已判定 2026-08-30；v0.1 拆分后唯一重预注册项） | 预注册问题："删除 engine_update 后，由 lowering 从 Effect 机械生成的 update，能否在四个切片上复现冻结 trace 逐字节一致"——判据**直接复用**压力测试冻结的 expected JSON 与规范 trace，不写新 expected。架构切两半以便失败可诊断：core 定义中间表示 `(path, op, payload, provenance)`，op ∈ `{set, add, transfer_pair, structural, contribution_resolve, event}`（R2，六值）；adapter 只做 IR → runtime 形状的逐 store 类型翻译。失败时定位为"Effect → IR 缺信息（契约问题，走 §5.6）"或"IR → update 翻译错（adapter bug）"。**H0（冻结版，经修正）**：至少一个冻结 cell 的 update 不是四元基 (Effect 载荷, 注册 schema 类型, 机制身份, 观测态视图) 的纯函数——hidden instance state、wall clock、live RNG 明确在基外。**修正记录**：起草期曾立"StateDelta 载荷不区分 set/add"为具名否定点，源码核查证伪（契约 v1 的 `StateDelta.operation ∈ {add, set}` 一直存在），plan 起草时替换为上述四元基 H0，冻结于 prereg `62d6d91`。同时完成：⓪ 移植信任核心 proofroot（只搬 D1 现行编码 + D4 不变量 + D2/D5，legacy 兼容层一律不搬；EvidenceCore.jl 冻结为 oracle 生成跨语言向量，§5.10）；封闭 engine_update 旁路、serialization spec 落地（§5.9）、重推导 conform 契约级套件、AST/import-lint CI | **判定（2026-08-30）：H1 支持，`compatible_for_frozen_slices_v1_lowered`**——冻结 trace 逐字节复现 ✓；重推导契约级套件全绿（94 项）✓；import-lint 通过（R4.2 引擎标识符禁令入 CI 门）✓；旁路封闭以新增负例证明 ✓；完整预注册审计 PASS（0 warning）。证据：newlife `results/v0.1a/`（活）与 exloop `artifacts/lowering-results/`（档案） |
| **v0.1b staging 可声明化**（✅ 预注册实验已判定 2026-08-31；依赖 0.1a） | 声明形状最小化（评审裁定，2026-08-31）：staging schema 置于既有自由 `schedule` 字段（不加字段——`MechanismSpec` dataclass 形状属契约 v1）；profile 校验 DAG 无环；`staging.py` 按拓扑序生成 Composite 编排。判据 = 复现压力测试 harness 手工连线产出的冻结 trace。单 Composite 语义保持开放（风险 3）——0.1b 只证明"多 Composite 编排可从声明推导"，已足以把调度语义从 harness 代码搬进声明 | **判定（2026-08-31）：H1 支持，`staging_declarable_for_frozen_slices`**（v0.1a 判定同时保持）——冻结 trace 复现 ✓（P1–P4 程序化断言：编译器记录 == 冻结预测）；DAG 无环等 8 项具名负例通过 ✓（含编排篡改对照被字节比对咬住、手工 Composite 构造 lint 零豁免）；参考内核程序序重复感知谓词校验 ✓；完整预注册审计 PASS（0 warning）。证据：newlife `results/v0.1b/`（活）与 exloop `artifacts/staging-results/`（档案）；staging schema 置于 `schedule` 字段（评审裁定），profile 2.1.0 承载 schema v1，conform 套件 1.1.0 |
| **RNG 流（设计裁决，不预注册）** | 信任核心移植即裁决（§5.10）：只搬 `evidencecore-rng-v1` 现行编码 + D4 bank 语义不变量（声明制流、小写归一、名字正则、只前进不重播），legacy 兼容层不搬；唯一新决定是流内顺序推进 vs counter-based（后者多买并行安全，实现面稍大）；trace 记录 draw 计数两种都兼容。方案空间无真正竞争选项，预注册无不确定性的问题是浪费纪律 | 与 EvidenceCore.jl oracle 的向量对照测试逐位一致（§5.10 纪律 1） |
| **v0.2 机制箱（已关闭）** | **Gate 已通过（2026-08-31）：第一个世界问题 = Parworlds Experiment 001 Resource Foraging（`resource-foraging-v1`）**——选择理由、冻结已知答案、三层比对方法（L1 派生种子已逐位验证、L2 录制 draw 注入优先、L3 统计比较退路）、宪法→stage/机制注册表的映射与痛点对照框架，见 [`docs/worlds/001-resource-foraging.md`](../worlds/001-resource-foraging.md)。000（Memory Benchmark）落选理由同文档。这个选择一次解决四件事：① 真问题——不是为库定制的表演性问题；② 已知答案——冻结的 Julia 结果即 known answer；③ 跨语言双实现比对——Julia 参考 vs Python newlife，压力测试方法学的放大版，serialization spec 第一天就有真实载荷；④ compare 归因判据的校准来源——该世界当年做过/想做的消融。**比对方法（种子可移植、序列不可移植）**：跨语言一致性验到派生种子层为止（§5.10 合同边界）；Julia 的 Xoshiro 流与 Python 生成器不同，"已知答案"**不靠活 RNG 的字节级 trace 比对**。两个可行方法，优先前者：① 录制 Julia 冻结 run 的 draw 序列注入 newlife——这正是压力测试已验证的注入方法，冻结 run binding 保证重跑可提取；② 退到观测量层的统计比较。机制注册表条目全部由该问题导出；四个人造切片不作为生产机制迁入 | **验收（2026-08-31）**：世界问题文档化 ✓；双条件（informative/cue-neutral）全量 32×32、5000-tick、含 128-episode assay 的 L2 录制 draw 注入比对逐位精确复现（`verdict: reproduced`，全部命名流耗尽为 0）✓；注册表条目由该问题导出（6 机制）✓；示例应用零 runtime 代码（import-lint 证明）✓；**痛点对照**：P3 世界重表达/harness 行数对照如实记录（newlife 两侧行数均高于 Julia，收益在结构不在行数）。证据：newlife `results/v0.2/gate.json`（`passed: true`），详见 `docs/worlds/001-resource-foraging.md` |
| **v0.3 compare 主线（已判定）与第二世界（已判定，`ms` 最小溯祖模型）** | **compare 半判定（2026-08-31）：H1 支持，`causal_attribution_declarable_for_world1_pairs`**——question 文档起草时发现的真实缺口（informative/cue-neutral 的唯一受控差异 `condition` 完全不出现在 `MechanismSpec` 声明里，registry diff 会得到空集）经两轮红队修正后，归因算法改为"域无关字段 diff + 观测序列分歧定位 + 反事实单字段翻转重跑"，聚合终态按固定优先级判 `causal`/`incidental`/`UNATTRIBUTED_DIVERGENCE`/`MULTI_CAUSAL_OR_UNRESOLVED`。预注册（`prereg.sh audit` PASS，0 warning）冻结于 exloop `322a8dc8`。7 个标定单元（4 个 World-1 真实 + 3 个纯合成，9 次执行）全部通过，含专门回归两个终态优先级冲突的 unit 6c。证据：newlife `results/v0.3/summary.json`；实现 `packages/newlife/src/newlife/core/compare.py`（域无关，stdlib-only）+ `mechanisms/resource_foraging/calibration.py`（World-1 校准点）+ `scripts/accept_v03_compare_gate.py`。第二世界最终选型改为 Hudson `ms`（1980 年代经典溯祖模拟器，该领域公认的验证标准答案），**不是**最初设想的 SLiM/msprime 对标——question 文档调研发现那条路会把证明标准从"逐位精确"降级为"统计上差不多"（SLiM/msprime 是他人 C++ 代码，无法像 v0.2 那样精确对账），而 `ms` 只有 1851 行、能真正啃透源码，保住了最高标准。**判定（2026-09-01）：H1 支持，`ms_minimal_coalescent_reproducible`**——预注册两轮红队（修正 R2 映射检查空转、`segsites==0` 输出形态未声明、两层判据被单层结果冒领）后冻结于 exloop（`prereg.sh freeze`，全新未提交路径）。两层合取判据：(a) 独立、无依赖的 Python 移植，重放真实、当场编译运行的 `ms` 二进制自身记录的 `drand48()` draw 序列，30 个复制品（3 组种子 × 10 次）segsites 与基因型矩阵逐位精确复现，零剩余零提前耗尽；(b) 同一算法包进 `MechanismSpec`/`StructuralRewrite`/`Event`/`ReferenceKernel` 两机制注册表（`biological` 面溯祖建树逐次合并事件各发一条 `StructuralRewrite`，`evidence` 面观测者读已提交树发真实 `Event`），逐复制品复现 (a) 自身输出。两层全绿，另加 R2 种子映射正确性检查（往返重装 + 高位丢弃可观测）与 `segsites==0` 覆盖率断言。**如实记录：这是第二个连续 bypass `staging.py` 的真实世界（P1 机制可组合性不但不推进，还小幅倒退——最小模型阶段整个溯祖循环刻意收在一个机制里，未拆分，因为拆分一个"多个竞争指数等待里挑最早一个"的事件循环，早于 schedule 形状问题解决之前就是过早结构化，question 文档已如实预告）**。证据：newlife `results/second-world/summary.json`（verdict 从合取机械计算，从不手填）+ 30 份逐复制品记录 `results/second-world/replicates/`；实现 `packages/newlife/src/newlife/mechanisms/second_world/`（`ms_coalescent.py` 独立移植 + `mechanisms.py`/`world.py` 注册表）+ `conform/second_world_verdict.py`（verdict runner） | compare：判据见预注册，已核对全绿；第二世界：判据见预注册，两层 30 复制品全绿，`results/second-world/summary.json` `passed: true`；profile 核心（`MechanismSpec`/`Effect` 五类）零改动 |
| **后续独立探索** | 动力学描述语言（类型化 Effect 上的 DSL）；单一 Composite 语义测试；冷启动长尾归因 | 各自 framing + 预注册 |

v0.1 拆分的理由：五合一复合实验违反预注册纪律的适用边界——预注册擅长"一个问题、一份判据"的窄合取，部分失败时（如 lowering 成功但 staging 失败）复合预注册要么判据矩阵爆炸，要么退化成"做完了再看"。现拆为**一重两轻**：0.1a / 0.1b 各自独立可否证；RNG 降级为设计裁决；compare 逆向移出 v0.1。gate 是一道闸不是一台发动机——世界问题不靠 gate 产生，所以 §1.5 的痛点清单与 Parworlds 候选在 v0.1 期间同步准备，gate 到期时不是从零起步。

**v0.1 排程（执行顺序表，四轮评审定型；不另立工作计划文档——§7 是战略层，question → plan → prereg 三件套 + `prereg.sh audit` 是执行层管道，再造计划文档是记账压过探索）**：

| 步骤 | 内容 | 约束 |
|---|---|---|
| **0. 仓库骨架** ✅ `fc4753e` | monorepo + uv workspace 双包、空模块结构、import-lint CI | 纯机械，无预注册约束，可立即做 |
| **1. proofroot 移植** ✅ `b092678`+`3b5607e`+`dc446f2` | 先用 EvidenceCore.jl（oracle）生成跨语言向量 → Python 实现 → 逐位对照，产出 proofroot 0.1（向量 48 项逐位一致） | 设计裁决非实验；可与步骤 2 并行 |
| **2. v0.1a 预注册** ✅ 冻结 `62d6d91`、戳记 `2cd12c0`，0-warning | 问题、判据、否定条件、冻结清单 | **冻结前不写任何 lowering 实现代码**——这是纪律的核心。预注册必须钉死：判定用的 canonical 形式（§5.9 坑）、IR 形状、H0 具名候选（set/add 候选经源码核查证伪后修正）、环境锁、anomaly protocol |
| **3. 实现 → 运行 → 审计** ✅ 判定 H1 `compatible_for_frozen_slices_v1_lowered`（2026-08-30） | lowering 双 adapter 实现、封旁路、重推导 conform、跑判定 | 复用 `prereg.sh audit`（完整审计 0-warning，exloop `8fa0707`） |

不做的事同样明确：`mechanisms/`、`examples/`、compare 逆向、Julia 注册包——全部在 gate 或 v0.3 之后。分工：预注册文档由维护方案的本会话起草（握有全部上下文），外部评审继续当审稿人——起草者与审稿者分开，与压力测试的红队结构同款。问题文档入口：v0.1a [`questions/2026-08-30-newlife-lowering-completeness.md`](../../docs/science-superpowers/questions/2026-08-30-newlife-lowering-completeness.md)（已判定）；v0.1b [`questions/2026-08-31-newlife-staging-declarability.md`](../../docs/science-superpowers/questions/2026-08-31-newlife-staging-declarability.md)（已修订过审）+ [`plans/2026-08-31-newlife-staging-declarability.md`](../../docs/science-superpowers/plans/2026-08-31-newlife-staging-declarability.md)（红队通过）+ [`preregistrations/2026-08-31-newlife-staging-declarability.md`](../../docs/science-superpowers/preregistrations/2026-08-31-newlife-staging-declarability.md)（**已冻结** `ed6c1b7`，0-warning）——staging 实现已解锁。

---

## 8. 风险与开放缺口

1. **第二系统效应（当前最大风险）**：newlife 是 ParaLife 的第二代重建。第一代是给自己用的、被真实研究磨过的；第二代最经典的死法是借"通用化"之名把第一代里从没痛过的地方重新设计一遍。防线不是纪律（纪律已经过剩），是 **§1.5 痛点清单作为设计压舱石**：每个 v0.1/v0.2 设计决策必须能指回一条真实痛点，清单之外的通用化一律缓建。复合风险：v0.1a–b 是纯建设期，全程只有人造压力拉动；AI 协作把写代码的成本降得越低，"在沙漠里越建越多"的诱惑越大——成本下降降低的是建设门槛，不是建错东西的代价。闸门的两种死法各有先例：闸门永远不开（SimLoop 教训的完整复刻，且方法学越好失败越体面）与闸门为库而开（选"刚好被四契约优雅表达"的问题，问题服务库）。缓解：第一个世界问题用 Parworlds 自己的冻结研究填空，不给"为库定制"留空间。
2. **lowering 完备性未证**（§5.2）：v0.1a 的中心预注册实验，判据复用冻结 expected；否定结果（如 set/add 区分缺失）合法，走 §5.6 程序。
3. **staging 可声明化未证**（§5.8）：v0.1b 独立预注册；压力测试由 harness 手工连线，能否完全由声明推导待证。
4. **单 Composite 语义未证**：0.1b 只证"多 Composite 编排可声明化"，单 Composite 无需编排的等价性保持开放；影响机制声明中调度语义的写法。
5. **RNG 流**：已降级为设计裁决（EvidenceCore 移植审计，§7）；保留边界"真实随机数实现未在跨语言场景下测试"。
6. **冷启动长尾未归因**：exploratory pilot 两次 N=1 超 30 秒（栈定位 `Composite.__init__ → plum` 注册解析），缓存热后 2.5 秒内。部署性能结论不可从 warm run 外推。
7. **负例的语言相关性**：既有负例在 Python 语义下推导；conform host 层按语言重推导（§5.4）。
8. **profile 审计的是过程合法性，不是生物正确性**：配置化与 AI 参与会批量生产"组装合法但科学上无意义"的模型；可比性不替代建模判断。人的科学判断从"实现模型"移到"决定哪些比较值得做"。
9. **动力学 DSL 未决**：反应网络类机制目前仍以代码进入 `mechanisms/`；DSL 化是独立的后续探索（§2 非目标）。
10. **§1 定位重述：由 proofroot 的采用情况裁决**。三轮评审点破的战略连接：proofroot 是"AI 模拟科学证据层"定位（契约层零领域语义、任何 runtime 社区可独立安装、compare 逆向无竞品、conform 即 TCK）的**最小可采纳单元**。它有没有外部采用者，会自下而上地回答定位问题——不需要先赌上 §1 的重写。若采用发生，再启动 §1/tagline/v0.3 优先级的重述（compare 升主线）；若长期无人采用，则安心收缩为 ParaLife 血统的内部设施。

---

## 9. 来源

- 探索内：[`../process/03-formal-pressure-test.md`](../process/03-formal-pressure-test.md)（正式证据）、[`../process/04-bigraph-lineage.md`](../process/04-bigraph-lineage.md)（谱系）、[`vivarium2-api-survey.md`](vivarium2-api-survey.md)（API 核查）、[`architecture-discussion-record.md`](architecture-discussion-record.md)（架构决策记录）、[`pressure-test/results/summary.json`](pressure-test/results/summary.json)（机器判定）。
- 文献：Milner, *Bigraphical Reactive Systems*, CONCUR 2001；Milner, *The Space and Motion of Communicating Agents*, CUP 2009；Krivine, Milner & Troina, *Stochastic Bigraphs*, ENTCS 218 (2008)；Agmon, *Foundations of a Compositional Systems Biology*, arXiv:2408.00942 (2024)；Agmon & Spangler, *Process Bigraphs and the Architecture of Compositional Systems Biology*, arXiv:2512.23754 (v2 2026-08)。
- 软件：[vivarium-collective/process-bigraph](https://github.com/vivarium-collective/process-bigraph)（Apache-2.0）、[vivarium-collective/bigraph-schema](https://github.com/vivarium-collective/bigraph-schema)（Apache-2.0），锁定版本 1.8.3 / 1.6.0。

---

## 10. 修订记录

**v0.2（2026-08-30）——吸收外部评审**。评审核实了压力测试代码后指出：方案把 lowering 写成了迁移，实际是一场未立项的新实验。全部主要意见已采纳：

1. （评审 A）v0.2 增加"选定第一个世界问题"显式 gate；切片不作为首批生产机制（§2 非目标第 6 条、§7）。
2. （评审 B，代码主张已复核为真）重写 §5.2：lowering 从顶层模块移入各 adapter（core 只留语义契约）；"每类 Effect 一个纯函数"改为批处理语义；v0.1 立项改为预注册的可否证实验；验收措辞改为"重推导契约级套件 + AST 审计"，不再使用"66 项全绿"。
3. （评审 B）新增 §5.6 Effect 分类学合法扩展程序；§1.3 补三个判定边界（lowering 未证、契约 v1 版本边界、RNG 未测）。
4. （评审 C）新增 §5.7 `core/compare.py` 可比性引擎，作为 §1.4 红线主张的正式落点；§2 目标 6。
5. （评审中分量项）conform 拆 contract/host 两层并带版本号（§5.4）；manifest 增至四个版本（§5.5）；因果阶段归属 adapter 的 staging.py（§5.8）；RNG 流进风险清单并在 v0.1 预注册裁决（§8.4）；AST/import-lint 成为常驻 CI 门；打包用 extras 强制零依赖（§4、§5.1）；手写校验器选型写明（§5.3）；引擎升级 = 重跑 conform（§3.3 原则 6）。
6. （评审小项）包名弃 `biosim`（与 COMBINE 的 BioSimulators 近乎撞名）改工作名 `bioprofile`，并列重名检查（§4、§6）；修正 `MechansimSpec` 拼写。

**命名修订（2026-08-30）**——包名定名 `newlife`（用户确认）：愿景名优于实现名（平台成长后 `bioprofile` 显窄）；PyPI 核查可用；GitHub/COMBINE 重名检查列为发布前待办；模块名保持描述性（§4、§6）。

**v0.3（2026-08-30）——二轮外部评审，全部采纳**。评审核实了 ParaLife 本机证据后修正了风险判断并给出挑战解法：

1. （叙事补全）新增 §1.5"从 ParaLife 到 newlife：痛点清单"——newlife 是 ParaLife 的第二代：把靠治理扛的证据纪律下沉为运行时强制，补上机制组合。痛点 P1/P2 已对 README 与 EvidenceCore.jl 核实，P3 待用户确认。该清单同时是第二系统效应的设计压舱石（风险 1 重写并升为最大风险）。
2. （挑战解法）v0.1 五合一拆为"一重两轻"：v0.1a lowering 完备性（判据复用冻结 expected；IR `(path, op, payload, provenance)` 两半切分；具名否定条件 set/add 区分）；v0.1b staging 可声明化（`stage`/`after` DAG）；RNG 降级为 EvidenceCore 移植审计（不预注册）；compare 逆向移出 v0.1（归因判据时序倒置，推迟到世界问题校准后随 v0.3 预注册）。
3. （技术雷）新增 §5.9 规范序列化 spec：RFC 8785 结构规则 + IEEE754 位模式比对 + 跨语言测试向量，conform/contract 0 号资产。
4. （风险发动机）v0.2 gate 填空：第一个世界问题 = Parworlds 冻结研究 000/001 的 newlife 重表达（真问题、已知答案、跨语言双实现、compare 校准四合一）；v0.3 compare 升为主线、第二世界候选 SLiM/msprime 对标；基因组分析靠后。
5. （定位问题未决）评审提出的"AI 模拟科学证据层"战略重述列为风险 10，留待用户决定。

**v0.4（2026-08-30）——三轮外部评审（已核 EvidenceCore.jl 全文），全部采纳**：

1. （证据层独立成包）用户提议拆出信任核心包，评审核实后确立：uv workspace 双发行版（evidencecore + newlife）；新增 §5.10 切线表——进 D1 现行编码/D4 不变量/D5 证据分层词汇表/D2 RunPhase/序列化 spec，留 trace schema/compare/manifest 组装。
2. （纪律细化）"API 以现有为准"改为两条：移植语义逐字节不改；ParaLife 历史兼容层（三种 legacy 编码、大写 parse_phase）一律不搬——第一代章程只收分叉点、其余刻意 package-local，拆分线不得比第一代章程更宽。
3. （技术雷）§5.10 合同边界定在派生种子层：种子跨语言可移植、随机序列不可移植（Xoshiro 是宿主的）；§7 v0.2 gate 补比对方法——录制 Julia 冻结 run 的 draw 序列注入优先，观测量统计比较为退路。
4. （oracle 治理）ParaLife 不迁移；EvidenceCore.jl 原地冻结作 oracle；形态为"spec + 一个实现（py）+ 一个 oracle（jl）"，不维护双实现。
5. （版本）manifest 四版本 → 五版本（+evidencecore）；§5.9 serialization spec 移居 evidencecore；§4 补 GitHub 入口三条缓解与发布形态。
6. （更名建议）evidencecore 包名发布前更名（命名街区噪音大、Rust 有近亲、与 EvidenceCore.jl 同名不同 API 有混淆），候选 seedline/reprospec 已核 PyPI 可用，锁定前四生态扫描；编码 ID 与包名解耦，更名不影响规范。
7. （矛盾修复）§5.7 逆向归因判据时序与 §7 v0.3 同步（世界问题校准后预注册）；风险 10 改写为"由信任核心采用情况裁决"。

**v0.5（2026-08-30）——命名闭合**：① 痛点 P3 用户确认，§1.5 清单三条全部闭合，升格为设计压舱石正式基线；② 信任核心包定名 `proofroot`——五生态核查（PyPI/crates.io/npm/Julia General/GitHub）全部干净，同批淘汰 reprospec/seedwright（GitHub 语义近亲）与 runproof/stemma/certus（PyPI 已占）；四生态+GitHub 扫描固化为命名锁定前置流程；③ 规范性章节（§4/§5/§7/§8）的包名同步为 proofroot；`evidencecore-rng-v1` 字节级 ID 与 EvidenceCore.jl（oracle）保持原名不动；④ 本文件历史修订条目中的 "evidencecore" 均指讨论当时的暂名，不改写。

**v0.6（2026-08-30）——四轮评审（v0.5 同步核查属实）**：

1. （新坑，必须在冻结判据时排掉）§5.9 生效时序收窄：v0.1a 判定比较**沿用压力测试原 canonical 形式**（裁判 = 产出 expected 的那把尺子）；新 spec 在 v0.1a 只管 proofroot 自身向量；trace 格式切换推迟到 v0.2 跨语言比对开工前，切换时重跑 conform。否则冻结 trace 的字节比对会平凡失败——格式差异不是 lowering 错误。
2. （不另立工作计划文档）§7 增加"v0.1 排程"执行顺序表：仓库骨架 → proofroot 移植（可与预注册并行）→ v0.1a 预注册（**冻结前不写 lowering 实现代码**）→ 实现/运行/审计；不做的事（mechanisms、examples、compare 逆向、Julia 注册包）显式列出。
3. （分工）预注册由本会话起草、外部评审当审稿人（红队同款结构）；问题文档已起草：`docs/science-superpowers/questions/2026-08-30-newlife-lowering-completeness.md`，管道为 question → plan → prereg + `prereg.sh audit`。

**v0.10（2026-08-31）——v0.3 compare 主线闭合**：① question → plan → prereg 三件套完成，全部起草于 exloop `docs/science-superpowers/`；question 文档起草期即发现真实缺口——informative/cue-neutral 的唯一受控差异 `condition` 完全不出现在 `MechanismSpec` 声明里，naive 的"注册表 diff"对这个真实世界会得到空集，但 trace 从 tick 1 就分岔，此发现直接决定了归因算法必须走"反事实单字段翻转重跑"而非静态声明比对。② plan 经两轮红队修正：第一轮抓出 n=1"消去法"不安全（真实原因若在声明外会被错误归因，且从不重跑验证）与"无 causal 字段却报不出异常"两个缺口，修正为聚合终态 `UNATTRIBUTED_DIVERGENCE`；第二轮抓出该聚合规则本身有两个终态可同时触发、且无优先级裁决，修正为"unresolved 优先于 no-causal"的显式顺序，并补两个此前从未被任何单元执行到的代码分支（per-field unresolved、length-mismatch locus）。③ 预注册冻结于 exloop `322a8dc8`（`prereg.sh audit` PASS，0 warning），冻结前发现原草稿文件已被提交、无法作为 `prereg.sh freeze` 目标（要求首次提交即冻结），改用全新路径 `-v2.md` 完成冻结。④ 实现：`core/compare.py`（域无关、stdlib-only，三个函数：`diff_declarations`/`locate_divergence`/`attribute_causality`）+ `mechanisms/resource_foraging/calibration.py`（World-1 四个真实标定点）+ `scripts/check_imports.py` 新增 R6 规则（`core/` 禁止导入 `mechanisms`/`adapters`）+ `scripts/accept_v03_compare_gate.py`（verdict runner）。判定 **H1 支持，`causal_attribution_declarable_for_world1_pairs`**：7 个标定单元（4 个 World-1 真实 + 3 个纯合成，共 9 次执行）全部通过，含专门回归聚合优先级冲突的 unit 6c；两项结构检查（registry 恒等断言、`core/compare.py` 无硬编码字段名的源码扫描）均过。证据：newlife `results/v0.3/summary.json`。⑤ 第二世界候选（SLiM/msprime 对标）按"一重两轻"拆分原则未启动，需另立 question 文档。

**v0.9（2026-08-31）——v0.2 gate 闭合**：① 双条件（informative/cue-neutral）全量 32×32、5000-tick、含 128-episode assay 的 L2 录制 draw 注入比对逐位精确复现，`verdict: reproduced`，全部命名流（含 128 episode）draw 耗尽为 0。② 实现期定位并修正两处 Julia 运行时语义缺口（原判据遗漏）：`sum(::Matrix)` 是 arm64 `@simd` 分块归约而非朴素左折；organism energy 求和依赖 Julia `Dict{Int}` 的 hash-slot 迭代顺序（含探测/tombstone/rehash 规则），两者均在 Python 侧显式复刻后消除了此前误判为"1e-9 容差可接受"的最后一位舍入差异。③ 六机制注册表（含 world-observer）由该问题导出；`examples/first-world` 零 runtime 代码，import-lint 证明。④ 痛点对照如实记录（非粉饰）：newlife 语义核心 2071 行 vs Julia 1054 行、harness 987 行 vs 819 行，两侧行数均高于 Julia——代价是逐位对齐要求显式建模 Julia 运行时免费提供的行为，以及新增 Julia 侧原本不需要的跨语言 draw 录制/注入基础设施；P3 真实收益在结构（声明式机制 vs 手写脚本）不在行数。证据：newlife `results/v0.2/`（gate.json + 双条件报告）。⑤ 下一步：v0.3 compare 主线，归因判据经本世界的消融数据校准后预注册（非凭空冻结）。

**v0.8（2026-08-31）——v0.1b 闭合**：① 排程之外的第二预注册完成：问题 → plan（红队四修：根封闭断言、重复感知 R6 谓词、P2 interval 归属、负例路径改写）→ 预注册冻结（exloop `ed6c1b7`，0-warning）→ 实现（staging schema 校验、P1–P3 推导、编译器、case 改线含负例路径、R6 参考断言）→ 判定 **H1 支持，`staging_declarable_for_frozen_slices`**（v0.1a 判定保持）：4 编排单元字节级复现、P4 程序化断言、8 具名负例全过。② 声明形状按评审裁定置于既有自由 `schedule` 字段——契约 v1 字面未动；P1 精化规则（初始根集 − stage 内部 store）冻结为 formal prediction，评审原规则（下游 wiring 根之并）被 hook 反例证伪的负结果一并入册。③ 实现日志 4 条均为 implementation clarification（混编检查落点、状态键位置化、schema 零值来源、跨 stage 状态线程），零判据变更。④ 下一步：v0.2 gate——第一个世界问题（Parworlds 冻结研究 000/001 候选重表达）。

**v0.7（2026-08-31）——v0.1a 闭合**：① 排程步骤 2–3 完成：预注册冻结（exloop `62d6d91`，审计 PASS 0 warning）→ lowering 实现（proofroot 向量迁移、core IR、双 adapter、旁路删除、10 具名负例）→ 判定 **H1 支持，`compatible_for_frozen_slices_v1_lowered`**：8/8 cell、16 正向（含重放字节一致）、18 cell 级负例、篡改 lowering 对照被字节比对咬住、引擎摘要前后一致。lowering 完备性在契约 v1 + 四冻结切片范围成立，第六 Effect 未被需要，单一写入路径以负例 + CI 门双重钉死；判定不可外推。② H0 修正入表（起草期 set/add 候选证伪 → 四元纯函数基）与 R2 六值 op 枚举同步。③ 三条实现期澄清（stage 不拷 effects、篡改对照检出面=终态半边 + anti-masking、list-direct 翻译条目）均记 implementation clarification，零判据变更，见结果包 implementation-log。④ 下一预注册：v0.1b staging 可声明化。

**v0.1（2026-08-30）——初稿**。
