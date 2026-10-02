# observable validity：判据测的是不是它以为的那个量

- **状态**：设计第三稿 · 2026-10-02 · **已实现**：接线测试 `fd52ae2`，M7 `023fe0a`，险情 B 回放 `tests/test_calibration_replay.py`；O1 暂缓（§4）
- **落点**：`judgement-design.json` 的第七问 **M7（估计器校准）**，由现有的 `judgement_design` 闸门检查；前置一条 freeze 接线测试
- **工作计划**：[`observable-validity-plan.md`](observable-validity-plan.md)
- **上游证据**：my-research 的 4 起**险情**（§1）

**第三稿改了什么**：按"代价要与证据相称"重新取舍。O3 不再是新闸门 + 新锚点，而是并进 `judgement-design.json` 当第七问；O1 暂缓，写明重启条件；删掉"锚点必填"原则和全部待定项。用户可见的变化只剩"已经在填六问的人多填一问"——`goal.md`、`prereg.md` 模板一字不动。

---

## 0. 一句话

现有闸门检验**判据的形式**——锚点齐不齐、有没有 pilot、能不能变红、覆盖没覆盖。没有一道检验**判据观测的量，是不是它以为在观测的量**。四起险情都是这个形状：判据写得合规、也能变红，但测的不是它声称的量。

四起都是**人在探索期自己抓到的**，没有一起走到 freeze。所以证据支持"这个失效机制真实存在"，不支持"freeze 已经放过了它们"——这决定了修法的分量（§2 原则 3）。

---

## 1. 证据：四起险情

| # | 险情 | 文件 | 它以为在测 | 实际在测 | 处置 |
|---|---|---|---|---|---|
| **B** | 「β/ν 高 1.6 倍」 | `explorations/2026-09-23-bioelectric-criticality-pilot/README.md` 复核 2–3 | 物理指数 β/ν | 估计器读数：已知真值上旧口径偏 **+0.0325**、全曲面偏 **−0.0100**，与要解释的效应（~0.03）同量级 | 人在复核时抓到（README 第 820 行："收敛到 0.16 这件事本身也只到 ±0.01 的精度"）。**→ M7（§3）** |
| **A** | 「稳态 Vmem」 | `explorations/2026-09-25-bioelectric-grn-landscape-planaria/P2-handoff-boundary.md` §2 | 稳态（BETSE 官方验证 Pietak & Levin 2016, PMID 27458581 用 30 min） | **35 ms 快照**；外推到 20–30 min 需 ~63–95 h | 人在 handoff 时抓到；该文件第 4 行写明"它不创建 `questions/`"。**→ 暂缓（§4）** |
| C | 归一化比值加预算 | 同 B（`spread(L)/spread(24)`） | 用更多格点收窄的估计 | 在 `1/√N` 律下分子分母同降的比值 | 机制不同（判据对预算不敏感），不在本稿（§5） |
| D | 止于摘要级的文献 | ≥6 篇；`.../2026-10-02-coupling-advice-lifesci-social` | 全文级核查 | 检索日志 + 摘要 | 机制不同（证据深度缺字段），不在本稿（§5） |

同类旁证：pfl 的"集中式上界"随种子漂——上界本身是**估计器**，不是真值。

---

## 2. 原则

**原则 1：不读日志，读产物。** 借 `coupling-problem-search` G7 的先例：G6 的 `search_log` 后门已证明"日志填了" ≠ "检索做过"（`.../2026-10-01-coupling-blocker-map/README.md:70-71`）。作者手填的"偏差 = 0.0325"也是日志——所以 M7 只收**估计器在已知真值上的原始读数**，偏差由闸门自己算。

**原则 2：judge 算术，不 judge 答案。** 照 `judgement_design` 已有的两趟：第一趟查形状，第二趟从作者自己写下的前提重算。闸门不判"0.03 算不算大"（没有比提问者更懂题的裁判），只判**作者已承诺的两个数之间的关系**。

**原则 3：代价与证据相称。** 本仓加闸门向来以真实注册的失败为据（`pilot_coverage`：前四个真实注册里两个 INVALID）。这次是两起探索期险情、零起 freeze 漏网，所以：
- **不给每个问题加必填锚点**。M7 只落在本来就要写 `judgement-design.json` 的问题上（`seeded` / `stochastic`，由 rule seven 决定）——适用性由现有机制裁定，不需要新的"填写或豁免"仪式；
- **一起险情不立一道门**。O1 只有险情 A 一例、一个模拟器，暂缓（§4）。

**原则 4：门要被调用，不只要能变红。** `test_gates.py` 按目录发现每个门的 `--selftest`，保证"能抓住"；但**没有测试断言 freeze / run 真的调用了它**——从 `scaffold.freeze` 删掉一行门调用，现有测试大概率全绿。这是里程碑 019（单门自检全绿、聚合入口八门全打不开）在 freeze 层的同形缺口。它与本稿的内容无关、现在就存在，作为前置先补。

---

## 3. M7 — 估计器校准

### 3.1 为什么是 `judgement-design.json`，不是新闸门

- 险情 B（蒙特卡洛临界指数）与 pfl 旁证都属于 `seeded` / `stochastic` 问题，**本来就要写这个文件**；
- 每个量已经有 **M1 `effect.value`**——偏差要与之相比的那个数现成，不用再找来源；
- 这个 `effect` 同时决定功效分析：**同一个数服务两处**。作者不能对功效分析报一个小效应、对校准报一个大效应；要让偏差显得小而调大它，就等于公开声明"本题只检测大效应"，N 随之变小、写在同一个文件里。这**不会让闸门变红**（改大 `effect` 再一致地改小 `result.n`，第二趟照样绿），但把"为过闸而改"变成一处可见、可审的改动——这是现有结构能给的防自证，不用新机制；
- 不新增锚点、不新增闸门模块、不新增豁免词。

### 3.2 字段

每个 `quantities[]` 新增必填字段 `calibration`，二选一：

```json
"calibration": {
  "truth": 0.125,
  "family": "exact 2D Ising exponent — an analytic result, not this fitter's output",
  "samples": "beta_over_nu@truth",
  "bias_accepted": null
}
```

```json
"calibration": {"not_applicable": "the quantity is read directly, no estimator between the run and the number"}
```

- `truth`：已知真值。必须来自**与本次估计器不同的函数族 / 解析解**，否则是用自己的口径校自己；`family` 把这一点写在案，闸门只查它非空，不判对错（与 M1 的 `rationale` 同一待遇）。
- `samples`：`pilot` 文件（现有顶层字段，`{quantity: {point: [values]}}`）里的一个键，存放估计器在已知真值合成数据上的**原始读数**，每个 seed 一个值。
- `bias_accepted`：偏差 ≥ 效应时的在案理由；正常为 `null`。豁免写在同一个文件里，不新增锚点词汇。
- `not_applicable`：量是直接读出的、中间没有估计器。理由必须非空。

### 3.3 闸门做什么（在 `judgement_design` 现有两趟里各加一步）

- **第一趟（形状，`schema.shape_problems`）**：`calibration` 在；二选一的形状对；`family`、`not_applicable` 非空。
- **第二趟（一致性，`consistency_problems`）**：
  1. 从 `pilot` 文件取 `samples` 指向的读数；不存在 ⇒ 红（与"pilot 样本不存在"同一种红）；
  2. 用该量**自己声明的 M2 位置统计量**（`location.statistic`）算读数的位置 `estimate`——同一把尺子量效应、也量偏差；
  3. `bias = |estimate − truth|`；`bias ≥ effect.value` 且 `bias_accepted` 为空 ⇒ 红。

### 3.4 什么会 / 什么不会阻止冻结

- **阻止**：字段缺失；`not_applicable` 无理由；`family` 为空；读数不存在；偏差 ≥ 效应而未在案。
- **不阻止**：偏差不为零（估计器有偏是常态，要的是**知道**）；`effect` 选得是否合理、`truth` 是否真的独立（没有裁判）。

### 3.5 覆盖的缺口，如实记下

- `deterministic` 问题不写 `judgement-design.json`，**M7 覆盖不到**确定性数据上的有偏估计（如对确定性模拟做有限尺寸外推拟合）。目前没有这类险情；出现一起再议。
- 读数由 runner 产出，runner 若硬编码数字，闸门看不出来；但 runner 与设计文件都在 freeze 时被钉住、可审计——比手填偏差强一档，不是滴水不漏。

### 3.6 变异用例（进 `judgement_design._selftest`）

| # | 变异 | 期望 |
|---|---|---|
| 1 | 读数位置离真值的距离 < `effect` | **green** |
| 2 | 距离 ≥ `effect`，`bias_accepted` 为空 | RED |
| 3 | 同 2，`bias_accepted` 有理由 | **green** |
| 4 | `samples` 指向 pilot 文件里不存在的键 | RED |
| 5 | 缺 `calibration` 字段 | RED |
| 6 | `not_applicable` 为空串 | RED |

### 3.7 兼容

- 已冻结的问题不再走 freeze，不受影响（本仓 `questions/` 下五个均已冻结）。**一个例外要说清**：`2026-09-06-judgement-design-method` 的 runner 在 S4 里对自己的设计文件调用 `judgement_design.check`，并要求它返回空。在新版本下重跑这个 runner，S4 会因缺 `calibration` 变红。这不算复现失败——它的 `summary.json` 记着当时的 `newlife_source_sha256`，换一版 newlife 源码重跑，本来就不是在复现那份记录；冻结的设计文件也不追溯补写。没有任何测试或脚本会重跑它（`scripts/check_record.py` 只核对记录）。
- 未冻结的 `seeded` / `stochastic` 问题升级后会因缺 `calibration` 被拦——`CHANGELOG.md` 写迁移说明：补读数，或写 `not_applicable` 与理由。

---

## 4. O1（稳态声明）——暂缓

**机制**：险情 A 是"声明的设置 vs 实际生效的设置"——注册说稳态，生效的 `t_end` 是 35 ms。这与 bigraph 契约层 §8 规则 2 同形（my-research 已在 `interface_contract.py` 机械化，不搬进 newlife）。

**为什么暂缓**：只有一例、一个模拟器。为它在每个问题的模板里加一个 `@steady_state` 锚点，做元胞自动机或统计问题的用户会看到一个与自己无关的词——代价落在所有人身上，证据只有一条。

**重启条件**：再出现一起"声明的设置 ≠ 实际生效的设置"的险情（不限稳态）。届时按第二例的形状设计——两例才看得出该抽象到"稳态"还是"生效设置"。第二稿里的具体做法（runner 产出 `effective_settings`、闸门经 ledger 的 `out` 读 pilot 产物比对、键名带单位）可作起点，见本文件的 git 历史。

---

## 5. 有意不做

1. **不做文本扫描**（找 `calibration`、`traceable` 字样）——会造出因错理由变绿的检查，即 G6 `search_log` 的老毛病。
2. **不预设科学阈值**。闸门只判"比过没有"，不判"偏差多小算小"。
3. **不引入新硬件 / 新长跑**。读数来自 pilot 本来就要跑的东西。
4. **O2（判据预算可动性，险情 C）**：要在两个预算点实际跑判据，与"读已有产物"不同形，另起设计。
5. **O4（`@evidence` 加 `depth`，险情 D）**：只是 `goal_ready` 已有锚点上的一个字段，下次动 `goal_ready` 时顺带做，不需要设计稿。

---

## 6. 落点

| 件 | 类型 | 位置 |
|---|---|---|
| 前置：freeze / run 接线测试 | **新** | `packages/newlife/tests/test_gate_wiring.py` |
| M7 形状 | 改 | `newlife/stochastic/schema.py`（`REQUIRED_QUANTITY` + 形状检查 + 文档串里的示例） |
| M7 一致性 | 改 | `newlife/gates/judgement_design.py`（`consistency_problems` + `_selftest`） |
| 用户文档 | 改 | `skills/newlife-prereg/references/design.md`（六问表加 M7 一行）；`SKILL.md` 与 `scaffold/__init__.py` 里的 "six questions" 改为 "seven" |
| 迁移说明 | 改 | `CHANGELOG.md` |
