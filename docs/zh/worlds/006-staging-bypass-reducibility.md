# World 6：staging 五次绕过——标准解法覆盖得了吗

- **状态**：已判定（2026-09-03）。**H1 支持**。
- **证据**：`results/sixth-world/summary.json`（`verdict: "H1"`，schema `newlife.sixth-world.verdict.v1`）
- **verdict runner**：`packages/newlife/src/newlife/conform/sixth_world_verdict.py`
- **预注册**：exloop `preregistrations/2026-09-03-newlife-staging-bypass-reducibility.md`，
  冻结于 `671d6f4`，`prereg.sh audit` PASS
- **这是一次回溯审计，不是新的世界**——不产生新的科学问题，判的是已有四个世界的控制流。

---

## 1. 结论

**四个调度相关循环全部可由 loop unrolling 表达。**

| 世界 | 循环 | bound | 可展 |
|---|---|---|---|
| World 1 | `assay.py:140` `for _ in range(config.assay_episodes)` | `static` | ✓ |
| World 2 | `ms_coalescent.py:111` `while len(active) > 1` | `config` | ✓ |
| World 3 | `moran.py:95` `while 0 < i < n_pop and steps < step_cap` | `capped` | ✓ |
| World 4 | `genealogy.py:80` `while alive > 1` | `config` | ✓ |

## 2. 三条子裁定（与 H0/H1 分开，不参与合取）

**S1 — 次数是 4，不是 5。** 第五世界是方法学度量，没有世界循环。记录里的「第五次被绕过」
把它算了进去。

**S2 — World 1 确实是手写循环。** `001-resource-foraging.md` 说「v0.1b（staging）提供
tick 顺序 = 声明 DAG」，`002-ms-coalescent.md` 说「与 World 1 的 tick 循环同样是手写
Python 循环」。**代码裁定后者对**：`mechanisms/resource_foraging/` 下没有任何文件引用
`staging`。`001` 那句描述的是 staging 的设计意图，不是 World 1 的实际接线。

**S3 — 「五次同因」不成立。** 四个循环出现**三种** bound 类型（`static` / `config` /
`capped`）。它们终止的理由各不相同：一个是配置给定的固定轮数、两个是集合单调缩小到 1、
一个是随机游走撞上限。**说它们同因，是把四件不同的事按同一句话记了四次。**

## 3. 真正的发现：记载指错了循环

记录称限制是「`{stage, after}` 的 DAG 不能表达重复到吸收」。机械普查四个世界共 **64** 个
循环，其中 **10 个真正无界**——但**没有一个是调度相关的**。它们全部在
`ms_coalescent.py` 内部：拒绝采样重试（`:113` `while rdum == 0.0`、`:124` `while j == i`）
与泊松逆变换采样（`:173` `while True`）。这些发生在**单个机制步内部**，不是 stage，
`staging.py` 从来不需要表达它们。

**换句话说：被指认为「表达不了」的那些循环全都可展；真正表达不了的那些，与 staging 无关。**

## 4. 这对 P3 意味着什么

**`staging.py` 不需要为「重复到吸收」扩展。** 四个世界的调度循环都有静态上界，
loop unrolling 直接适用。绕过 staging 的真实原因不在表达能力上——按 World 2 自己的记载，
那次是「过早结构化」，一个工程时序判断，不是能力缺口。

**本里程碑不提扩展方案**（goal §4 明确不做）。它买到的是：**取消一条不成立的风险记录**，
以及知道下次再绕过时不能再拿「DAG 表达不了」当理由。

## 5. 边界与未做

- **「调度相关」那一刀是本设计唯一的判断性步骤**，其余机械。它的定义（每一轮对应一次
  机制步的重新调度）冻结在预注册 §3.1；四条判定的理由逐条写在 design §2.3。
- **recursive DAG 支线未展开**——四个循环全部 `unrolling` 可表达，那一支不影响结论
  （预注册 §3 事前声明）。
- **不评价 `{stage, after}` 当初的设计对不对**——终局前不审判那一类。

## 6. 负控

verdict runner 做了三条，全部按预期翻转：把目标指向 `ms_coalescent.py:173` 那个真正无界的
`while True` → **H0**；行号挪开一行 → **IC-3 / INVALID**；文件不存在 → **INVALID**。
分类在 verdict runner 里是**独立实现**，与 exloop 的 `loop_census.py` 同规格、不同代码路径。
