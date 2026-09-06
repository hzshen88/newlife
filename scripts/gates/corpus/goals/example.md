# Goal — 示例：漂移的步长是不是恒定的

- **状态**：frozen —— 冻结 commit 与内容哈希见本行末的 `@frozen` 锚。<!--@frozen: commit=EXAMPLE, sha256=301d493380688e4433e1ba298550a3ca4d8bf9bd07a952b48d6da07b768237a0-->

<!--@evidence: literature_searched=yes, sources=1, verdict=已知-->
<!--@counterparty: 会有人押 H0：步长恒定是 `drift` 的定义直接给出的，测它等于什么都没测。这条指名的是「判据与实现同源」这一条前提-->
<!--@decides: design-->
<!--@attack_layer: conclusion-->
<!--@who_changes_behavior: 抄这份样板的人——决定他自己的第一个 goal 要写成什么样-->
<!--@size_estimate: impl_lines=90, criteria=3, failure_modes=1-->

---

## 1. 这份语料是干什么的

**它是门的自检语料，同时是给用户抄的最小样板。** 它**不是**一个真问题——
按 `newlife-goal` 的分诊，它的答案由**设计**决定（`drift` 每步 +2 是写死的），
所以它是「工具」档，**不许声称任何关于世界的结论**。

**它没有用 `@goal_gate: not_applicable` 自我豁免**——语料 goal 必须是门**真的会检查**
的那种，否则拿它做的负控打不中任何东西（起草时正是这么栽的一次）。

**放它在这里的唯一理由**：门需要一份含全部锚形的文档才能自检，
而用户也需要一份能照抄的最小样板。**一份东西，两个用途。**

## 2. 达成判据

- C1 轨迹长度等于步数加一 <!--@criterion: C1-->
- C2 末态等于起点加两倍步数 <!--@criterion: C2-->
- C3 相邻步长只有一个取值 <!--@criterion: C3-->

## 3. 结局词表（封闭）

<!--@vocabulary: C1=constant|varying-->

**封闭意味着不许扩。** 为了让某个结果通过而加一个取值，正是判据被事后放宽的形状。
