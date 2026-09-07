# Goal — sender side operator derivable

<!--@evidence: literature_searched=yes, sources=3, verdict=unknown-->
<!--@counterparty: FMI 标准的设计前提本身就押反面——它规定接口说明由模型作者随实现一起交付，即业界认为发送端语义必须声明、不可从行为推断。技术理由也实在：store type 的 apply 是纯函数，问几次都一样；process 的 update 带内部状态，探测调用本身会改变它，而且求解器类 process 未必接受零时长这种退化输入-->
<!--@attack_layer: conclusion-->
<!--@decides: run-->
<!--@who_changes_behavior: 任何用 admit 接第三方 process 进 newlife 的人。最近的一个是 hzshen 本人：下一步把 mapsim 接进来时必须手填 PortBinding 的 operation，而 mapsim 的 step 原地改 owner 数组、返回绝对归属，照抄 writing-a-world.md 里那个返回增量的示例就会静默错配-->
<!--@size_estimate: impl_lines=380, criteria=4, failure_modes=1-->

| Anchor | What it must say | Why it is gated |
|---|---|---|
| `@evidence` | `literature_searched=yes, sources=N, verdict=known\|partly known\|unknown` | A search that failed and was silently skipped looks exactly like one that found nothing |
| `@counterparty` | Who would bet the other way, and on what grounds | If nobody would, the result is already inside your expectations |
| `@attack_layer` | `conclusion` \| `premise` \| `definition` | Under attack at the premise a simulation settles nothing |
| `@decides` | `design` \| `run` | Confuse them and a tooling result gets reported as a conclusion about the world |
| `@who_changes_behavior` | A specific person **and** a specific decision | The "unimportant but decidable" bucket passes every later gate |
| `@size_estimate` | `impl_lines=N, criteria=N, failure_modes=1` | No estimate made in advance means nothing to calibrate against |

## 1. What this buys

做完之后，从做不到变成做得到的是：**接第三方代码进来时，`PortBinding.operation` 这一格
能被机器核对，而不是只能靠人写对。**

今天这一格是人写的断言——`foreign.py` 的 docstring 自己写着「This is us speaking on the
third party's behalf. It is an assertion, not a fact read off the third party.」写反了
不抛异常、数量级和单位都对、`pilot` 还会把它记成 covered，于是整套预注册体系会为一个
语义错误的判据盖章。第十八个里程碑已经把**接收端**（store type 的 add/set）从人写变成
了行为探针推出的事实，3/3；**发送端**至今没有对应的东西。

**起草期间实测得到的一处重要更正（2026-09-07，pilot 前的廉价证伪）**：
`foreign_growth/declaration.py` 写着「本文件填错了，没有任何东西会发现」，实测显示
**这句话已经过时，但坑仍然存在，只是形状变了**。三种声明各跑 5 步：

| 声明 | 报警 | 质量轨迹 |
|---|---|---|
| 正确 `add` + `sum-float-add` | 无 | 1.0 → 1.61（指数增长，`Grow` 应有行为） |
| 只填反 binding 为 `set` | **SpecValidationError** | 拒绝执行 |
| **binding 与 lowering 一起填反**（`set` + `sum-float-set`） | **无** | 1.0 → 1e-05（**指数衰减**） |

`lowering.py` 的 `_expect()` 让每个 store handler 校验自己假定的算符——这是第十五个
里程碑收尾时补的守卫。**但它守的是「声明内部自洽」，不是「声明与 process 实际行为
一致」**：两处一起填反就内部自洽了，于是畅通无阻、方向反转、零警告，而那串数字
正数单调量级正常，看不出任何破绽。**这正是本里程碑要填的那一格。**

**起草期间已经被廉价证伪的部分**：最初的设想是「零时长探针一问就知道——返 0 是增量、
返当前值是绝对值」。检查现有代码后这条不成立，至少三处：`probe_operation` 探的对象是
纯函数 `apply(schema, 1.0, 0.5)`，而 process 的 `update` 带内部状态（`writing-a-world.md`
的示例里 `self.rr` 会被写）；求解器类 process 未必接受零时长；而且第十八个的配套纪律
要求探针先自证能分辨，在发送端这需要先有已知增量语义与已知绝对值语义的对照物。
**所以「一问就知道」这句在动手前就已经不成立，剩下的是「换别的问法行不行」。**

## 2. Success criteria

判据是合取，且**不依赖 H1**——它们说的是「这个问题有没有被回答」，不是「答案有没有
如我所愿」。H0（推不出来）成立时，下面三条仍应全部满足。

- **C1**：对三个真实第三方 process（`Grow`、`MonodKinetics`、`DynamicFBA`，均已在第
  15/16/17 个里程碑接入且源码未改），各自产出一个由代码算出的判定，取值来自封闭词表
  `derivable` / `not_derivable` / `probe_inapplicable`，**不得手填**。
- **C2**：探针自证有判定力——在一个已知增量语义与一个已知绝对值语义的对照物上分别给出
  正确答案。**做不到这条，整套推导没有判定力，goal 未达成**（这一条与结果方向无关：
  它只问探针会不会分辨，不问真实 process 分辨出的是哪一种）。
- **C3**：与手写 `PortBinding.operation` 对不上的项被**机械分类**，能区分出「探针不适用」
  「手写声明本来就错、探针是对的」「真的分不出」三者。分类由代码算，不由散文判断。

## 3. Explicitly not doing

- **不碰接收端**。store type 的 add/set 第十八个里程碑已解决，本次不重做、不改 `derive.py`
  里的 `probe_operation`。
- **不把探针接进 gate**。本次只回答「能不能问出来」；把它变成 freeze 前的强制检查是
  另一个里程碑的事（先有结论，再决定要不要建设施）。
- **不给 mapsim 写 wrapper**。mapsim 是这一格的动机来源，不是本次的被试品——它还没接进来，
  拿它当样本等于同时引入一个新 wrapper 的不确定性。
- **不改 `PortBinding` 的数据结构**，不动 `admit()` 的签名。
- **不修 `writing-a-world.md` 的那段警告**。结论出来之前改文档是本末倒置。

## 4. Risks declared in advance

- **三个样本全部可推，也不能声称「任意第三方 process 可推」**。三个都来自 process-bigraph
  生态，共享同一套 `Process` 基类与调用约定；换个生态（tellurium、COPASI、mapsim 这种
  自研模拟器）是否成立，本次不回答。
- **可推 ≠ 契约能拦住错误声明**。本次只判「信息能否被问出来」，不判「问出来之后能不能
  自动否决一个填错的 binding」。收尾时这两句必须分开写。
- **探测调用可能污染 process 内部状态**，使被探对象的后续运行不再可复现。实现时必须每次
  探测都用全新实例，并在判据里留一格证明隔离有效——否则这个里程碑会亲手制造第十一个
  里程碑专门去测的那种判定腐烂。
- **失败可能来自探法选得差，而不是信息本质上不可得**。`decides=run` 要求排除前者：
  所以 C3 必须能把 `probe_inapplicable` 单独分出来，而不是一律记成 `not_derivable`。

## 5. Closeout judgement

(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)
