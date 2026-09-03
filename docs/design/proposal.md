- **注**：本文件自 v0.6 起是活版本，随本仓库演化。冻结母本（v0.6，2026-08-30）在 exloop 探索档案：`exloop/explorations/2026-08-29-biological-sim-architecture/artifacts/biosim-library-proposal.md`。

# BiologicalProfile 库建设方案

- **日期**：2026-09-01　**状态**：v0.10（v0.1a/v0.1b 均已判定：H1 支持，`compatible_for_frozen_slices_v1_lowered` 与 `staging_declarable_for_frozen_slices`；**v0.2 gate 已关闭**：World 1 = Resource Foraging 双条件 L2 逐位精确复现，`results/v0.2/gate.json` `passed: true`；**v0.3 compare 主线已判定**：H1 支持，`causal_attribution_declarable_for_world1_pairs`，预注册冻结于 exloop `322a8dc8`，实现见 `packages/newlife/src/newlife/core/compare.py`；**第二世界（`ms` 最小溯祖模型）已判定**：H1 支持，`ms_minimal_coalescent_reproducible`，预注册冻结于 exloop `c450072`，实现见 `packages/newlife/src/newlife/mechanisms/second_world/`；**第四世界（Moran 谱系 vs Kingman 溯祖）已判定**：H1 支持，预注册冻结于 exloop `24bb02e`，且 goal 的痛点 P1 首次判为 `achieved`——**移离零，不是解决**，见 [`docs/worlds/004-moran-genealogy.md`](../worlds/004-moran-genealogy.md)；**第五世界（gate 自身的检查覆盖率）已判定**：**H0 支持**——47 个 check 里 3 个 `hollow`，八个里程碑以来第一个非 H1 结果，见 [`docs/worlds/005-gate-check-coverage.md`](../worlds/005-gate-check-coverage.md)；**第十五个里程碑（接第三方 process）已判定**：**H1**——`process_bigraph.processes.growth_division.Grow` **源码零改动**被接进一个 newlife 世界，轨迹与**裸 pb**逐字节相同，两条负控（声明错路径 / 未声明 Effect）都被拒且状态不变，**元负控成立**（绕开契约就不被拒）。**但「接上 pb 就接上了它的生态」今天不成立**：`biosimulator-processes` 0.3.19 与 `vivarium-interface` 0.0.5 **都装不起来**（都 import 一个任何可用 pb 版本里都不存在的 `ProcessTypes`，且都没声明版本下界）。**成色须降级**：端口→(路径,算符) 那张表只能由我们代写，对照 FMI（接口描述由模型作者随实现交付）——H1 证明的是「契约对**被代写的声明**有强制力」，见 [`docs/worlds/015-foreign-process.md`](../worlds/015-foreign-process.md)；**第十四个里程碑（跨运行时 verification）已判定**：**H1**——World 4 的同一份声明在 `ReferenceKernel` 与 `process-bigraph` 上各跑 2101 次，**2101/2101 逐字节相同**，负控（改坏 pb 的 store 写入）变红，6.8s；**process-bigraph 从零使用变成真跑通一个世界**。**但 goal 只买到一半**：pb **不满足** B 接缝的 Definition——`core/runtime.py` 的四个操作是从 RK 读出来的逐阶段 **pull** 形状，而 pb 是先拿整张图再自己调度的 **push** 运行时，**B 今天仍只有一个 provider**；此事「事前未预见」。顺带闭合了「契约层焊死在一个运行时上」，并查出**第七世界的判定记录自第八个里程碑起是烂的**（重跑得 INVALID 而非记录的 H0），见 [`docs/worlds/014-cross-runtime-verification.md`](../worlds/014-cross-runtime-verification.md)；**第十三个里程碑（非 Python 依赖）已判定**：**H0**——`git` 缺失时静默产出一份格式完好的判定，理由写成「基线不可得」而真实原因是 git 不在，**第四次栽在同一形状且环境层扫描器够不着**，见 [`docs/worlds/013-undeclared-deps.md`](../worlds/013-undeclared-deps.md)；**第十二个里程碑（归档重放）已判定**：H1，5/5，但测出未声明的 C 工具链依赖，且**无独立预注册**；**第十一个里程碑（旧判定复现率）已判定**：H1 支持——除已知的 seventh 外**七个全部逐字节复现**；口径须连报：文献 3.4% 的基准率来自跨年依赖漂移，本项目是同环境几天之内，**跨年漂移从未被测过**，见 [`docs/worlds/011-verdict-rot.md`](../worlds/011-verdict-rot.md)；**第十个里程碑（判定接缝）已判定**：**INVALID**（IC-4）——三代判定表示已装进同一个三值 Definition 且值域未放宽，但 `seventh` 的冻结产物因第八世界改动而不可复现；**顺带发现第七世界的判定已失效**，见 [`docs/worlds/010-verdict-seam.md`](../worlds/010-verdict-seam.md)；**第九世界（tick 循环终止条件）已判定**：**H0-a 支持**——终止条件能用冻结算符集表达（C2 通过、未触发 inner-platform），但 `run` 是混合部件且 harness 与 World 1 装配所有权冲突；**卡住的是部件边界与装配所有权，不是表达能力**，见 [`docs/worlds/009-harness-tick-loop.md`](../worlds/009-harness-tick-loop.md)；**第八世界（harness 吃下 World 4）已判定**：H1 支持——**P3 首次成立**（受限：World 4 无 tick 循环，`simulator` 块最难的一半未检验）；`world.py` 148 → 68 行，配置纯数据、verdict 逐位不变，见 [`docs/worlds/008-harness-absorbs-world4.md`](../worlds/008-harness-absorbs-world4.md)；**第七世界（harness 可生成性）已判定**：**H0 支持**——42 个部件里 4 个落不进 DEVS 三分+rng，聚成「数值复现」与「运行时契约强制」两种能力，后者正是 P2；通用 harness 的规格是五块不是三块，见 [`docs/worlds/007-harness-generability.md`](../worlds/007-harness-generability.md)；**第六世界（staging 绕过可归约性）已判定**：H1 支持——四个调度循环全部 unrolling 可表达，「五次同因」裁定为不成立（三种 bound 类型），`staging.py` 无需为「重复到吸收」扩展，见 [`docs/worlds/006-staging-bypass-reducibility.md`](../worlds/006-staging-bypass-reducibility.md)；**第三世界（Moran 选择可判定性）已判定**：H1 支持，预注册冻结于 exloop `aa052dd`，证据分层裁定落地——claim (i) 为与 L1/L2/L3 正交的 analytic/specification-conformance，见 [`docs/worlds/003-moran-selection.md`](../worlds/003-moran-selection.md)）
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
| **v0.3 compare 主线（已判定）与第二世界（已判定，`ms` 最小溯祖模型）** | **compare 半判定（2026-08-31）：H1 支持，`causal_attribution_declarable_for_world1_pairs`**——question 文档起草时发现的真实缺口（informative/cue-neutral 的唯一受控差异 `condition` 完全不出现在 `MechanismSpec` 声明里，registry diff 会得到空集）经两轮红队修正后，归因算法改为"域无关字段 diff + 观测序列分歧定位 + 反事实单字段翻转重跑"，聚合终态按固定优先级判 `causal`/`incidental`/`UNATTRIBUTED_DIVERGENCE`/`MULTI_CAUSAL_OR_UNRESOLVED`。预注册（`prereg.sh audit` PASS，0 warning）冻结于 exloop `322a8dc8`。7 个标定单元（4 个 World-1 真实 + 3 个纯合成，9 次执行）全部通过，含专门回归两个终态优先级冲突的 unit 6c。证据：newlife `results/v0.3/summary.json`；实现 `packages/newlife/src/newlife/core/compare.py`（域无关，stdlib-only）+ `mechanisms/resource_foraging/calibration.py`（World-1 校准点）+ `scripts/accept_v03_compare_gate.py`。第二世界最终选型改为 Hudson `ms`（1980 年代经典溯祖模拟器，该领域公认的验证标准答案），**不是**最初设想的 SLiM/msprime 对标——question 文档调研发现那条路会把证明标准从"逐位精确"降级为"统计上差不多"（SLiM/msprime 是他人 C++ 代码，无法像 v0.2 那样精确对账），而 `ms` 只有 1851 行、能真正啃透源码，保住了最高标准。**判定（2026-09-01）：H1 支持，`ms_minimal_coalescent_reproducible`**——预注册两轮红队（修正 R2 映射检查空转、`segsites==0` 输出形态未声明、两层判据被单层结果冒领）后冻结于 exloop（`prereg.sh freeze`，全新未提交路径）。两层合取判据：(a) 独立、无依赖的 Python 移植，重放真实、当场编译运行的 `ms` 二进制自身记录的 `drand48()` draw 序列，30 个复制品（3 组种子 × 10 次）segsites 与基因型矩阵逐位精确复现，零剩余零提前耗尽；(b) 同一算法包进 `MechanismSpec`/`StructuralRewrite`/`Event`/`ReferenceKernel` 两机制注册表（`biological` 面溯祖建树逐次合并事件各发一条 `StructuralRewrite`，`evidence` 面观测者读已提交树发真实 `Event`），逐复制品复现 (a) 自身输出。两层全绿，另加 R2 种子映射正确性检查（往返重装 + 高位丢弃可观测）与 `segsites==0` 覆盖率断言。**如实记录：这是第二个连续 bypass `staging.py` 的真实世界（P1 机制可组合性不但不推进，还小幅倒退——最小模型阶段整个溯祖循环刻意收在一个机制里，未拆分，因为拆分一个"多个竞争指数等待里挑最早一个"的事件循环，早于 schedule 形状问题解决之前就是过早结构化，question 文档已如实预告）**。世界文档见 [`docs/worlds/002-ms-coalescent.md`](../worlds/002-ms-coalescent.md)（收尾时漏写，2026-09-01 补记）。证据：newlife `results/second-world/summary.json`（verdict 从合取机械计算，从不手填）+ 30 份逐复制品记录 `results/second-world/replicates/`；实现 `packages/newlife/src/newlife/mechanisms/second_world/`（`ms_coalescent.py` 独立移植 + `mechanisms.py`/`world.py` 注册表）+ `conform/second_world_verdict.py`（verdict runner） | compare：判据见预注册，已核对全绿；第二世界：判据见预注册，两层 30 复制品全绿，`results/second-world/summary.json` `passed: true`；profile 核心（`MechanismSpec`/`Effect` 五类）零改动 |
| **第五世界（已判定）：gate 自身的检查覆盖率** | **判定（2026-09-03）：H0 支持——八个里程碑以来第一个非 H1 结果**。测的是这套审核机制自己的盲区：exloop 四个验证脚本共 47 个 check，逐条归入 `auto`(24) / `hand`(15) / `anchored`(5) / `hollow`(3) / `IC-1`(0)。**三个 `hollow`**：`IC-1-tractable-at-frozen-N` 的判定条件是**字面量 `True`**（任何变异都不可能让它红）；`check-2` 是记账式计数，covers 内的变异改的是值而它数的是个数；`check-5` 是内联字面量算术，不经任何生产函数。**二阶发现**：`covers` 会误归因——它的语义是「自上次 report 起新观测到的调用」，**不等于**「算出这条 check 所断言的那个值的东西」，后两个 `hollow` 由此产生而非真空洞，必须与数字一起报。**实测自动覆盖**：两个 plan 侧脚本 **0/11 与 0/7**；在 `094c6c8` 之前 **18/47 的 check 处于「显示已覆盖、实际从未被测」**（`mutation_scan` 因标签正则写死前缀而在空集上恒真）。**goal 判定 `achieved` 而 verdict 为 H0**——判据是「量出覆盖率并把盲区写下来」，不依赖 H1，§1.5 的两层解耦第一次被真实结果检验；C4（新盲区变 fixture）未做，如实记录。世界文档见 [`docs/worlds/005-gate-check-coverage.md`](../worlds/005-gate-check-coverage.md)。证据：`results/fifth-world/summary.json`（verdict 从合取机械计算，`passed: false`）；runner `conform/fifth_world_verdict.py` | 分类表 47/47 全覆盖、每行有证据、无未讨清 IC-1；`hollow` 计数为 3 故 H0；goal 判定与 verdict 物理分开 |
| **第四世界（已判定）：Moran 谱系 vs Kingman 溯祖，兼 P1 首个实例** | **判定（2026-09-02）：H1 支持**。第一个**没有任何外部程序作为对标**的世界——对标项目自己推导并由脚本验证的数学。两层判据由数学逼出：claim (i) 拓扑，shipped builder 自己步规则诱导的 ranked labelled history 精确分布对 Kingman 闭式 `2^(n−1)/(n!(n−1)!)`，`n ∈ {3..7}` **0 mismatch**（56,700 条 history 在预算内）；claim (ii) 观测量，2101 个 replicate 的 `S̄ = 4.5307` 落在冻结验收域 `[4.4286, 4.7047]`，靶是**解析常数** `θ·H_(n−1) = 137/30`。**claim (ii) 的靶不是另一个模型的分布**——红队第五轮发现两模型 `E[S]` 在每个有限 N 上恒等，原判据"两模型分布一致"跑完必然通过却什么都没证明，是**不可证伪**的；改为对照解析靶后失败才会指向实现。载荷推导也被红队双向证伪过一次（"比值与 n 无关"既非必要也非充分，两个精确反例作为永久 check 保留），结论对而理由重写为「一步至多一次二元合并 + 条件 pair 均匀」。**P1 首次推进**：注册表原样复用 World 2 的 `second-world-observer`（对象同一性判据，挡住了手工改写 `__module__` 的复制品），复用范围由 registry 裁定（两者共同 `own TREE_PATH` 抛 `StructuralOwnershipConflictError`），无冻结产物跨世界。**如实记录**：消费方迁就了生产方的命名空间（`TREE_PATH` 是 World 2 的模块常量，第四世界状态里带 `second_world` 键，plan R2 权衡后接受），**这个组合不是干净的**；`staging.py` 第四次被绕过（goal §5.1 事前预声明，四连信号入 §8 风险清单）。世界文档见 [`docs/worlds/004-moran-genealogy.md`](../worlds/004-moran-genealogy.md)。证据：`results/fourth-world/summary.json`（verdict 从合取机械计算）；实现 `mechanisms/fourth_world/` + `conform/fourth_world_verdict.py` | 判据见预注册（冻结 `24bb02e`，`prereg.sh audit` PASS）；claim (i) 五个 n 全零 mismatch，claim (ii) 在验收域内，`passed: true`；goal 的 P1 判定与 verdict 物理分开，`summary.json` 经检查不含任何 goal 词汇 |
| **第六世界（已判定）：staging 五次绕过的可归约性——回溯审计，非新世界** | **判定（2026-09-03）：H1 支持**。四个**调度相关**循环全部可由 loop unrolling 表达：World 1 `assay.py:140` `static`、World 2 `ms_coalescent.py:111` `config`、World 3 `moran.py:95` `capped`、World 4 `genealogy.py:80` `config`。**文献先行改变了这个里程碑**：「DAG 不能原生表达重复到收敛」是教科书级已知（L-DAG 2019 / J.Cloud Computing 2021 / ACM CSUR 2022），标准解法为 loop unrolling 与 recursive DAG，所以原本「证明 DAG 表达不了」的 H1 是重新发现教科书，作废；问题磨成「已知解法覆不覆盖本项目的实例」。**三条子裁定（与 verdict 分开）**：S1 次数是 **4 不是 5**（第五世界是方法学度量，无世界循环）；S2 World 1 **确为手写循环**（`mechanisms/resource_foraging/` 无任何文件引用 `staging`，`001` 那句描述的是设计意图不是实际接线，与 `002` 矛盾处由代码裁定）；S3 **「五次同因」不成立**——四个循环出现**三种** bound 类型。**真正的发现：记载指错了循环**——机械普查 64 个循环，10 个真正无界，但**无一调度相关**（全在 `ms_coalescent.py` 的拒绝采样与逆变换采样内部，属机制步内部，staging 从不需要表达）。**对 P3 的意义：`staging.py` 不需要为「重复到吸收」扩展**，并取消 §8 那条未经核对的四连/五连风险记录。世界文档见 [`docs/worlds/006-staging-bypass-reducibility.md`](../worlds/006-staging-bypass-reducibility.md)。证据：`results/sixth-world/summary.json` | 判据见预注册（冻结 `671d6f4`，`prereg.sh audit` PASS）；三条负控全部按预期翻转（指向真正无界的 `while True` → H0、行号漂移 → IC-3、文件不存在 → INVALID）；分类在 verdict runner 里独立实现 |
| **第十二个里程碑（已判定）：只装声明依赖能否重放——不是世界** | **判定（2026-09-03）：H1**，5/5 逐字节复现（要求 ≥3），全新 venv 只装 `pyproject.toml` 声明的依赖（`newlife` + `proofroot`），同一解释器 3.12.8。文献公认答案是容器化（含 OS 的镜像），对手方据此押 H0——**H1 成立是因为依赖面薄得反常**。**但测出一条未声明依赖**：`second` 编译并运行 `ms` 的 C 源码依赖系统 C 工具链，不在 `pyproject.toml` 里，这次通过只因同机编译器在位。**口径连报**：「纯净」只到 Python 包这一层，同机同 OS，**不说明跨机器跨年可复现**。**⚠️ 流程违规如实记：冻结 goal 后直接跑了实验，没有单独冻结预注册**（判据确实事前冻在 goal §3，但 IC 与停止规则缺失）；**不事后补**，故 `prereg.sh audit` 对该里程碑不可用，结论强度低于其余。世界文档见 [`docs/worlds/012-archival-replay.md`](../worlds/012-archival-replay.md) | goal 冻结 `42ada0e`；无预注册 |
| **第十五个里程碑（已判定）：一个第三方 process 接得进来而契约还咬得住吗——不是世界** | **判定（2026-09-03）：H1**。接的是 `process_bigraph.processes.growth_division.Grow`，**源码零改动、不子类化覆写 `update`**。V1 它仍定义在 vendor 包内 · V2 经 newlife 接入的轨迹与**裸 pb**（不 import 任何 newlife）逐字节相同——**包装是忠实的** · V3 正控增长正确 · V4 代写声明错路径 → `CommitAuthorityError` 且状态不变 · V5 未声明 `StateDelta` → 同上 · **元负控**：同一份错误声明绕开契约则**不被拒**，证明拒绝确实是契约干的。**先说负面结果**：已发布的 Vivarium-2 生态入口包 `biosimulator-processes` 0.3.19 与 `vivarium-interface` 0.0.5 **都装不起来**——都 import `ProcessTypes`，而它在任何能与 `bigraph_schema` 1.6.0 配对的 pb 版本里都不存在（实测 1.8.3/1.8.2/1.8.0/1.7.1/1.5.0/1.4.18），且**两者都没声明 pb 版本下界**，安装静默成功、import 才炸。**所以改用 pb 自带的领域 process。****成色降级（预注册 §5 事前声明）**：端口→(路径,算符) 那张表只能由我们代写，第三方两处信息都不提供；对照 FMI——那里接口描述由模型作者随实现一起交付。**H1 证明的是「契约对被代写的声明有强制力」，不是「第三方生态可以安全地接」。****判定录完之后补了一道守卫**：把代写算符从 `add` 填成 `set`，修复前**产出完全相同的轨迹、无人报警**；丢失在 store handler（`_sum_float_add` 假定 ADD 却不校验，而同仓库 `_budget_proposal_projection` 等两处本来就有这个校验）。已补齐 5 个 handler，四份已判定产物修复后逐字节不变。**顺序刻意：先录判定，再修。**今天的边界：填一条**无人认领**的路径，契约不会说话。规模 449 行 vs 事前 345（**+30%**，从上次 +39% 收窄）。世界文档见 [`docs/worlds/015-foreign-process.md`](../worlds/015-foreign-process.md)。证据：`results/fifteenth/summary.json` | 判据见预注册（冻结 `8d65582`，audit PASS）；goal 判 `achieved` 但明写成色降级 |
| **第十四个里程碑（已判定）：同一个世界跑在两个运行时上，结果一样吗——不是世界** | **判定（2026-09-03）：H1**。U0 安全绳 PASS（harness 改收 runtime 工厂后 RK 产物逐字节不变）· U1 pb 跑完 2101/2101 · U2 **2101/2101 逐字节相同** · 负控变红 · 6.8s。**process-bigraph 从零使用变成真跑通一个世界**，752 行适配终于有了第一个用户。两个负控各有信息：改坏 pb 写树 → `segsites` 9→0（证明 pb 的写入在关键路径上）；**颠倒声明里的阶段顺序，pb 照样跑对（按接线依赖定序），RK 直接抛 `TypeError`（按列表顺序）——pb 在这一点上严格更强**，这是唯一一条「留着 pb」的正面证据。**最重要的产出不是 H1，是事前未预见的那条**：`core/runtime.py`（B 的 Definition）的四个操作是从 `ReferenceKernel` 读出来的**逐阶段 pull**，而 pb 是**先拿整张图再自己调度的 push**——`adapters/process_bigraph/world_runtime.py` **不是 `WorldRuntime` 的实现**，是 `WorldSpec` 的第二个消费者。**B 接缝今天仍只有一个 provider 满足它的 Definition**，现在的形状已知是错的（把 RK 的 pull 当成了通用形状），下次该规定的是**图与依赖**。顺带：架构图标红的第①条闭合；依赖声明自第八个里程碑起陈旧（已补）；**第七世界判定记录自第八个里程碑起是烂的**（4 个 phantom 部件全是被删的 `MoranGenealogyWorld.*`，重跑得 INVALID 而非记录的 H0）——`verdict_rot.impacted_by` 回溯适用正确抓住了它，当时没人跑；`test_reuse.py` 5 个测试同源一直红。**未覆盖那份已判定产物**，单独立项。规模 460 行 vs 事前 330（**+39%**，超出近五次的 ±25%）。世界文档见 [`docs/worlds/014-cross-runtime-verification.md`](../worlds/014-cross-runtime-verification.md)。证据：`results/fourteenth/summary.json` | 判据见预注册（冻结 `1b9257a`，audit PASS）；goal 判 `achieved`，verdict 判 H1，但 goal §6 明写「只买到一半」 |
| **第十三个里程碑（已判定）：非 Python 依赖缺了会不会静默——不是世界** | **判定（2026-09-03）：H0 支持**。`pyproject.toml` 之外穷举出**两条**：`cc`（`ms_binary.py:19`）缺失时 **`hard_fail_named`** ✓ 报 `FileNotFoundError: 'cc'`；**`git`（`verdict.py:315` 等三处）缺失时 `silent_output`** ✗✗——`eighth_world_verdict.py` 里的 `try/except Exception: pass` 吞掉异常，**产出一份格式完好的 `verdict: INVALID`，理由写成「基线不可得」，而真实原因是 git 不在**。**不是没报警，是报错了案由。** design §2.3 在跑之前就点名了这一处嫌疑，实测证实。对照组（`third`）两次判 `unaffected`，证明分类不会把「用不到」误记成「装作没事」。**本项目第四次栽在同一形状**（前三次：mutation_scan 空集恒真、gate_coverage_check 的 `if m else 0`、verdict_rot 跨仓库解析失败当成没变动），**而这次在环境层，`silent_degradation_scan` 完全够不着**。穷举边界如实写明：只覆盖已知会被执行的路径，声明的是「已知需要什么」不是「只需要这些」。世界文档见 [`docs/worlds/013-undeclared-deps.md`](../worlds/013-undeclared-deps.md)。证据：`results/thirteenth/summary.json` | 判据见预注册（冻结 `6c94455`，audit PASS）；goal 判 `achieved` 而 verdict 判 H0——**G4 成立：H0 之下 goal 仍达成** |
| **第十一个里程碑（已判定）：八个旧判定还有几个是坏的——不是世界** | **判定（2026-09-03）：H1 支持**。除已知的 `seventh` 外，**七个全部逐字节复现**（复现 7 · 坏 0 · 跑不了 0）。**这个数要连口径一起报**：文献的复现衰减基准率很难看（27,271 个生物医学 notebook，依赖装得上的 10,388 个里只有 879 个产出相同结果，约 3.4%；IR 研究发现四年后多数已无法运行），**但那是依赖漂移、跨年发生；本项目是同一台机器、同一环境、几天之内，唯一那次失效也是我们自己的第八个里程碑造成的**。所以 7/7 说明「环境不变时冻结判据 + 确定性种子撑得住」，**没有说明能扛住跨年漂移——那从未被测过**。**起草期做对的一个区分**：归档复现（`git checkout` 冻结 commit + 冻结种子，**能**保障）与当下有效性（今天的代码是否仍满足当时判据，**不能也不该**保障）是两个问题，本里程碑测第二个。**四态而非二态**：`reproduced` / `value_changed`（答案变了，**系统演化是正常科学结果不是故障**）/ `unevaluable`（**问题没了**，判据引用的对象已删）/ `unrunnable`（不计入 H0）；两者混淆列为 IC-2。**顺带测到的归档缺口**：8 份产物里 6 份记了自己的冻结 commit，`second` 与 `fifth` 没记，归档复现对这两个不是一条命令。世界文档见 [`docs/worlds/011-verdict-rot.md`](../worlds/011-verdict-rot.md)。证据：`results/eleventh/summary.json` | 判据见预注册（冻结 `3a2ca54`）；负控三态全部实测翻转（改一字节 → `value_changed`/H0、加一行 raise → `unrunnable`/INVALID、`seventh` 实时演示 `unevaluable`），恢复后回 H1 |
| **第十个里程碑（已判定）：判定这道接缝，从八个已有实现里提取——不是世界** | **判定（2026-09-03）：INVALID**，触发一条预注册没预见到的 IC。C1（三个 runner 都经由同一Definition）与 C2（值域仍是三值、未放宽，机械查 `DOMAIN`）**全过**；C3 逐字节不变 **2/3**。**三代表示确实装进了同一个 Definition**，靠把被同一键名混住的两件事分开命名：**判定是三值，假设名是标签**，标签由声明式映射给出（`{H1: "ms_minimal_coalescent_reproducible", H0: "verdict_withheld"}`），映射须对值域穷尽——`second` 的 runner 里因此不留 `if/else`。**IC-4 的裁定**：`seventh` 对不上冻结基线的原因**不在接缝**——第八世界删去 `fourth_world/world.py` 的 4 个部件，第七世界的分类表仍声明它们 → `phantom:4` → verdict 由 H0 变 INVALID；**把改动收起来跑原版，原版给出同样的 INVALID**，且原版 vs 接 Definition 后逐字节相同。按字面 C3 不成立即 H0，但 **H0 的含义是「Definition 装不下」而这里装得下**，照字面判会把「第七世界产物过期」误记成「接缝装不下第四代表示」——**预注册没覆盖的情形不许硬塞进 H0/H1**。**最值钱的产出：第七世界的判定已不可复现，而此前没有任何东西会发现它——因为没有任何东西在重跑旧世界的 verdict。这正是「判定该有接缝」的最强论据。** 世界文档见 [`docs/worlds/010-verdict-seam.md`](../worlds/010-verdict-seam.md)。证据：`results/tenth/summary.json` | 判据见预注册（冻结 `a517d29`）；负控：把标签映射改成常量 → `second` 产物立刻不同，恢复后逐字节相同，证明 Definition 真参与产出 |
| **第九世界（已判定）：真 tick 循环的终止条件能否纯数据表达——补第八世界未检验的那一半** | **判定（2026-09-03）：H0-a 支持**。C1 失败、C2 通过、C3 未评估。**正面结果（C2）：终止条件确实能用冻结算符集表达**——`tick lt config.ticks` ∧ `population gt 0`，两个子句、只有合取、算符在冻结的六个比较关系内、observable 是已声明观测量名（非任意状态路径），配置经 AST 检查为纯数据。**没有为让它通过而扩算符集**——那是预注册点名禁止的 inner-platform effect 的第一步。**失败的两个原因都是结构性的**：① **`run` 是混合部件**——21 行里只有中间的 `while` 属 `simulator`，前后是 `frame`（tick-0 快照 + `WorldRunResult` 聚合）；只吃循环则 `run` 不消失，连带搬走则超范围，**两条路都是 H0-a**。**这反过来打了第七世界一记：它把 `run` 整体判为 `simulator`，归类粒度是「函数」而真实类型边界在函数内部。** ② **装配所有权冲突**——通用 harness 假设自己拥有引擎装配，World 1 已经拥有；接线只能写成 `GenericWorld.__new__` 再手填字段，**那个写法本身就是证据：harness 是并排贴上去借一个循环，不是吃掉**。**结论：卡住的不是表达能力，是部件边界与装配所有权**——下一步不该扩配置语言。**C3 未评估**（重跑 v0.2 gate 需外部 L2 录制根目录，本次不可得；合取在 C1 已断，不改变 verdict——但未评估就是未评估）。**goal 判定 `not_achieved`，并自我批评：达成判据与 H1 逐条重合，违反 G4，冻结时没看出来；不许事后改窄判据让自己通过。** 世界文档见 [`docs/worlds/009-harness-tick-loop.md`](../worlds/009-harness-tick-loop.md)。证据：`results/ninth-world/summary.json` | 判据见预注册（冻结 `10e26c7`）；中途叫停一次 debug 螺旋——继续调是在为不可能改变结论的度量烧预算 |
| **第八世界（已判定）：通用 harness 把 World 4 吃到零——建造，P3 首次成立** | **判定（2026-09-03）：H1 支持**。三条判据全过：第七世界判为 `simulator`/`frame` 的 4 个部件在 World 4 侧**全部消失**（AST 枚举，挪到别处也算没消失）；配置是**纯数据**（无 lambda / 函数定义 / eval 类构造，AST 检查）；verdict **逐字节不变**（`7e5bbc47…` 前后相同）。账面：`world.py` **148 → 68 行**（只剩 `model`），新增纯数据配置 `spec.py` 62 行 + 通用件 `core/harness.py` 170 行——**通用件是一次性成本，配置是每世界的常量成本**。**逃生口没有出现**：预注册冻结了「若终止条件或观测提取只能用 lambda 表达即判 H0」（框架文献恰恰不处理「模型装不进抽象时怎么办」），原 `run()` 的两个 lambda 闭包被拆成阶段顺序 / 静态参数 / 命名流绑定三样纯数据。**P1 未被破坏**（`observer_is_world2_object` 仍为真，由逐位不变一并保证）。**边界（事前声明，非事后免责）**：World 4 的 `run` **没有循环**，`simulator` 块最难的一半（真 tick 循环）**本次完全未检验**，「P3 成立」的正确读法是「吃得下无循环的两阶段世界」；数值复现与运行时契约强制两块用不到、也未检验。**一次实现 bug 按 IC-1 处理**：verdict runner 首版从预注册 freeze commit 取基线，而那个 commit 在 exloop、文件在 newlife，跨仓库解析不了，修完重跑不计 H0。世界文档见 [`docs/worlds/008-harness-absorbs-world4.md`](../worlds/008-harness-absorbs-world4.md)。证据：`results/eighth-world/summary.json` | 判据见预注册（冻结 `6f2bc25`，`prereg.sh audit` PASS）；三条负控全部按预期翻转（配置塞 lambda → C2 FAIL、放回一个部件 → C1 FAIL、`mean_segsites` 改 1e-12 → C3 FAIL）；**NC-3 第一版是无效变异**（按显示值 `4.5307` 替换，而 JSON 是全精度），与「`return P*2` 作用在列表上」同类，已重做 |
| **第七世界（已判定）：六个世界的 harness 有多少能生成——回溯审计，冲 P3** | **判定（2026-09-03）：H0 支持**——42 个顶层部件（872 行）里 **4 个落不进冻结词表**。词表取自先验知识而非自拟：Zeigler 的 DEVS 三分（model/simulator/experimental frame）+ 本项目补的 `rng`；**预注册明写「落不进不许扩词表，直接判 H0」**——扩词表就能永远 H1。分布：`simulator` 21 · `frame` 12 · `rng` 3 · `model` 2 · **`unclassified` 4**。**落不进的 4 个聚成两种能力**：**数值复现**（3 个，复现 Julia 的 SIMD 浮点求和顺序——任何以「逐位复现另一实现」为判据的世界都会长出这类代码）与**运行时契约强制**（1 个，`_validate_world_invariants`；**这正是痛点 P2，而 DEVS 三分不含它，因为 DEVS 不关心谁有权写什么**——这不是 DEVS 的疏漏，是本项目相对经典模拟架构多出的一层）。**产出即通用 harness 的规格：五块不是三块**，其中最大的 `simulator`（21/42）正是 `staging.py` 本该覆盖的地方——三个世界各自手写了一遍 `_run_stage`；`frame` 12 个部件**目前完全没有对应物**。**World 3 裁定（与 verdict 分开）**：它根本没有 harness——不装配引擎、不注册机制、verdict runner 直接调机制函数；**是 P3 唯一「成立」的实例，但代价是完全绕开 registry 与引擎，不计入 P3 进度**。世界文档见 [`docs/worlds/007-harness-generability.md`](../worlds/007-harness-generability.md)。证据：`results/seventh-world/summary.json` | 判据见预注册（冻结 `c10dcb3`，`prereg.sh audit` PASS）；四条负控全部按预期翻转，含「偷偷用词表外取值 → INVALID」；verdict runner 独立重做枚举，不读 design 阶段台账 |
| **第三世界（已判定）：Moran 选择可判定性，兼证据分层裁定** | **判定（2026-09-02）：H1 支持**。冻结网格 N=6、i₀=1、r ∈ {1/2,1,3/2}、with-replacement、birth-first，4050 个 replicate。claim (i)：**每一步**由独立 oracle 从 `(pre, draw1, draw2)` 重放，逐值零容差，全部通过；claim (ii)：三个 cell 的不动次数 23/232/494 全部落在精确二项验收域 [11,33]/[193,258]/[451,536]；零删失。**oracle 与机制是同规格的两个独立实现，机制不得 import oracle（AST import 图检查强制）**——共用一份阈值代码会让 claim (i) 退化成「实现 vs 它自己」。**方法学产出**：claim (i) 裁定为与 L1/L2/L3 **正交**的 analytic/specification-conformance，不是第四级；claim (ii) 是普通 L3，只是靶恰好精确。**plan 经三轮红队**（question 已六轮，plan 的 Task 0 此前从未做过）：第 1 轮发现靶 `P_i_grid` 从未被任何 check 钉住（偏 1% 全绿且打印的表不变）；第 2 轮发现「定义」不等于「验证」——把 draw 顺序*声明*一下不能封住角色互换，实测 245,760 个三元组里 109,624 个受影响而角色标签记录让它们**全部逃逸**；第 3 轮钉死 step 口径（含空步 227 vs 只数有效步 89，差 2.55 倍）。**如实记录**：IC-3 的逐位对账在冻结网格上**无法区分**「字面浮点序列」与「先化简再除」两种阈值算法（差异只在 r=5/3，网格外），已写成断言固定；`staging.py` 第五次被绕过。世界文档见 [`docs/worlds/003-moran-selection.md`](../worlds/003-moran-selection.md)。证据：`results/third-world/summary.json` | 判据见预注册（冻结 `aa052dd`，`prereg.sh audit` PASS）；claim (i) 0 失败步、claim (ii) 三 cell 全在域内、零删失，`passed: true`；痛点判定 `not_applicable`（goal 事前声明属方法学收益类） |
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
3. **staging 可声明化未证**（§5.8）：v0.1b 独立预注册；压力测试由 harness 手工连线，能否完全由声明推导待证。**（2026-09-03 更新）** 原「连续 N 次绕过、同因、DAG 表达不了重复到吸收」的风险记录**已被第六世界证伪并取消**：次数是 4 不是 5、四个调度循环出现三种 bound 类型故非同因、且全部可由 loop unrolling 表达。真正无界的循环都在机制步内部，与 staging 无关。**下次再绕过 staging，不得再用「DAG 表达不了」当理由。**
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
