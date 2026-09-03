# World 8：通用 harness 把 World 4 的手写代码吃到了零

- **状态**：已判定（2026-09-03）。**H1 支持**——**P3 首次成立**（受限意义，见 §4）。
- **证据**：`results/eighth-world/summary.json`（`verdict: "H1"`）
- **实现**：`packages/newlife/src/newlife/core/harness.py`（通用件）+
  `mechanisms/fourth_world/spec.py`（纯数据配置）
- **verdict runner**：`packages/newlife/src/newlife/conform/eighth_world_verdict.py`
- **预注册**：exloop `preregistrations/2026-09-03-newlife-harness-absorbs-world4.md`，
  冻结于 `6f2bc25`，`prereg.sh audit` PASS

---

## 1. 结论：三条判据全过

| | 判据 | 结果 |
|---|---|---|
| C1 | 第七世界判为 `simulator`/`frame` 的 4 个部件在 World 4 侧**全部消失** | ✓ 残留 0；保留 `build_mechanism_specs`/`genealogy_step` 两个 `model` |
| C2 | 配置是**纯数据**（无 lambda / 函数定义 / eval 类构造，AST 检查）| ✓ |
| C3 | verdict **逐字节不变** | ✓ `7e5bbc47…` == `7e5bbc47…` |

**账面**：`world.py` **148 → 68 行**（只剩科学），新增纯数据配置 `spec.py` 62 行，
通用件 `core/harness.py` 170 行——**通用件是一次性成本，配置是每个世界的常量成本**。

## 2. 逃生口没有出现

预注册 §3.2 冻结了最容易失败的那条：**若终止条件或观测提取只能用 lambda 表达，
即胶水未被吃掉，判 H0。** 框架文献恰恰不处理「模型装不进抽象时怎么办」，而逃生口
通常就长成一个 lambda。

**本次没有出现。** 原 `run()` 里两个 `lambda view: ...` 闭包，被拆成三样纯数据：
阶段顺序、静态参数、命名流绑定。机制函数由**点分路径字符串**指名——字符串是数据，
被指名的函数是 `model`，本就该是代码（`proposal.md` §1.4 第三层）。

## 3. 一个设计决定值得写明：为什么 `reuse_trace` 的字段名在配置里

`results/fourth-world/summary.json` **原样嵌入**这份 trace，字段名是本世界对外的声明
契约。**harness 算事实（对象同一性、spec 是否被改），配置给名字。** 把
`observer_is_world2_object` 这种名字硬编进通用件，才是把一个世界的特殊性焊死在通用件上。

**P1 未被破坏**（预注册 IC-2）：`observer_is_world2_object` 仍为真——由 C3 的逐位不变
一并保证，不需要单独断言。

## 4. 边界：这次证明的比听起来的窄

**World 4 的 `run` 没有循环**——它是两个顺序阶段加一次取值，`while alive > 1` 在
`genealogy.py` 内部属 `model`。所以：

> **H1 只能说「harness 吃得下无循环的两阶段世界」，不得外推。**

`simulator` 块最难的一半（World 1 的 `tick` 40 行 + `run` 21 行那种真 tick 循环）
**本次完全未被检验**。这是 design §2.1 事前声明的，不是事后补的免责。

**数值复现与运行时契约强制两块 World 4 用不到，本次未检验**——用不到不等于它们不存在。

## 5. 一次实现 bug，按 IC-1 处理

verdict runner 首版从预注册的 freeze commit 取基线 sha——**而那个 commit 在 exloop，
`summary.json` 在 newlife，跨仓库解析不了**。这是实现 bug 而非抽象装不下，按预注册
IC-1 修完重跑，不计 H0。改为从本仓最后一次触及该文件的 commit 取。

## 6. 负控

三条，全部按预期翻转：配置里塞 lambda → **C2 FAIL / H0**；把一个被吃掉的部件放回去 →
**C1 FAIL / H0**；把 `mean_segsites` 改动 `1e-12` → **C3 FAIL / H0**。

**NC-3 第一版是无效变异**——按显示值 `4.5307` 做字符串替换，而 JSON 里是全精度
`4.530699666825321`，替换是空操作。与「`return P * 2` 作用在列表上」是同一类错误：
**用一个测不出问题的变异去判「通过」**。改成真改浮点值后才拿到有效负控。
