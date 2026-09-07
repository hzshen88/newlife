# sender side operator derivable

**Frozen at commit:** _pending_

## 1. Hypothesis

- **H1**：对第三方 process，**发送端算符**（它 `update` 返回的是增量还是绝对值）可以由
  **行为探针**从运行行为推出——推出的结果与手写 `PortBinding.operation` 逐项相同（S4），
  探针自身能分辨两种语义（S2），**且能抓住被故意填反的声明**（S5）。
- **H0**：S2、S4、S5 中任意一项为假。**H0 必须指明是哪一项**——三者失败的含义完全不同：
  S2 假 = 探针没有判定力；S4 假 = 推出的与手写的不符；S5 假 = 探针确认得了对的、抓不住错的。

## 2. Judgement units (mechanical conjunction, computed by the runner — **never filled in by hand**)

| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | Self-reproduction | two independent runs produce byte-identical artifacts | mechanical |
| **S1** | Environment unchanged | the packages installed at run time are exactly those `env.lock` recorded at the freeze | mechanical |
| **S2** | 正控：探针自证能分辨 | 已知增量语义的对照物判为 `add`，已知绝对值语义的对照物判为 `set`，且两者相对裕度均大于 `1e-6` | **seen** |
| **S3** | every criterion proves it can fail | each predicate returns false on a synthetic counterexample, computed at runtime | mechanical |
| **S4** | 三个真实第三方 process 上，推出的算符与手写声明逐项相同 | `Grow`、`MonodKinetics`、`DynamicFBA` 的每个端口，探针判定 == 该端口 `PortBinding.operation`；任何端口判 `indeterminate` 或 `AMBIGUOUS` 即为假 | **seen** |
| **S5** | 负控：填反的声明被抓住 | 对上述三个 process 的**每一个端口**，把手写算符取反后，探针判定与之不符（即探针报告不一致）；有任何一个端口"取反后仍被判为一致"即为假 | **blind** |

**verdict = S0 ∧ S1 ∧ S2 ∧ S3 ∧ S4 ∧ S5.** Any one false → H0; **S0 false → INVALID**

<!--@reproduction_class: deterministic — 探针只对每个 process 调用两次 update，不抽随机数、不跨 tick 累积状态；DynamicFBA 每次调用解一个 LP，而第十七个里程碑已实测它在同输入下逐字节可复现-->

**Fill in the "Piloted?" column for every unit** — `seen` / `blind` / `mechanical`.

**S2 与 S4 已在起草期跑过，如实标 `seen`。** 具体看到的数字记在 `goal.md` §1 与
`origin/provenance.md`：S2 的两个对照物相对裕度均为 1.0；S4 是 3/3 相同。
**S5 从未跑过**——它才是这一轮携带信息的那一格，而且它问的是探针真正有用的能力：
确认一个正确的声明没有价值，抓住一个错误的才有。

## 3. Frozen implementation constraints

- **F1**: **Every criterion must be able to go red.** Prove it in the runner at runtime
  with synthetic inputs, not in prose.
- **F2**: `passed` is computed from the conjunction, never assigned.
- **F3**: the artifact records the newlife source digest, the `env.lock` hash, the
  platform and the Python version.
- **F4**: **this question's verdict must not run any other question's runner.**
- **F5**: **探针每次探测必须使用全新实例**，不得跨探测复用 process 对象——
  `goal.md` §4 事前声明的风险之一是探测调用会污染被探对象的内部状态。
- **F6**: 探针**不得读取** `PortBinding.operation`、`LOWERING`、或任何声明侧的算符信息
  来形成自己的判定。判定只能来自 `update` 的返回值与传入状态。**违反这条，S4 变成恒真。**
- **F7**: 判定词表封闭为 `add` / `set` / `indeterminate` / `AMBIGUOUS`，
  落不进的一律记 `indeterminate` 并使该端口的 S4 为假，**不许扩词表**。

## 4. Invalidation conditions (**written separately from the criteria**)

- **IC-1**: a building block fails to produce a result → environment problem, invalid.
- **IC-2**: S1 false (the environment changed) → not a judgement; rebuild and rerun.
- **IC-3**: 判定前，探针实现或三个 `declaration.py` 中任何一个被改动 → 作废。
- **IC-4**（卫生检查，**刻意放在这里而不是合取式里**）：若隔离自检失败——即同一个
  process 连续两次全新实例探测给出不同结果——则本次运行没有判定力，作废。
  **它不进合取式**：一条会在合法数据上失败的机械检查不得否决一次科学上成功的运行
  （第十九个里程碑 tellurium v2 的教训）。

## 5. Declared in advance: the boundary of the conclusion

即使六格全绿，本次**不建立**下列各项：

1. **不建立「任意第三方 process 的发送端算符可推」**。三个样本全部来自 process-bigraph
   生态，共享同一套 `Process` 基类与 `update(state, interval)` 调用约定。换一个生态
   （tellurium、COPASI、或 mapsim 这类自研模拟器）是否成立，本次不回答。
2. **不建立「契约能自动拦住填错的声明」**。本次只判信息能否被问出来；把探针接进
   freeze 前的强制检查是另一个里程碑的事。
3. **不建立「探针无需领域知识」**——这是 pilot 实测出来的真实约束，必须写明：
   探针需要一个**能激活该 process 的输入状态**。`MonodKinetics` 第一次探测因状态端口名
   不匹配而全部返回 0，探针（在加入 `indeterminate` 之前）差点据此输出一个确定的错误判定；
   `Grow` 的 `STATE_ROOTS` 里 `mass` 是 `None` 占位，探测状态由探针合成为 `1.0` 并在产物中
   标注 `synthesized_state_ports`。**「状态从哪来」不在本次的判定范围内，它是下一个问题。**
4. **不建立「S5 通过就等于探针能抓住任意错误声明」**。S5 只取反算符这一个维度；
   路径填错、端口漏声明等其他填错方式不在本次范围（前者第十五个里程碑已证契约会拒）。

## Frozen data checksums

- questions/2026-09-07-sender-side-operator-derivable/env.lock e4690977847b741fb4824221ba24d88fb877615e
