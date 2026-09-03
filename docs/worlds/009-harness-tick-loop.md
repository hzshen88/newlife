# World 9：真 tick 循环的终止条件，能不能用纯数据表达

- **状态**：已判定（2026-09-03）。**H0-a 支持**。
- **证据**：`results/ninth-world/summary.json`（`verdict: "H0"`，`h0_shape: "H0-a"`）
- **预注册**：exloop `preregistrations/2026-09-03-newlife-harness-tick-loop.md`，
  冻结于 `10e26c7`

---

## 1. 结果

| 判据 | 结果 |
|---|---|
| C1 `ForagingWorld.run`/`.tick` 消失 | **FAIL** |
| C2 终止条件是纯数据、算符在冻结集内 | **PASS** |
| C3 `results/v0.2/gate.json` 逐位不变 | **未评估** |

## 2. 正面结果：表达能力够用，没触发 inner-platform

**终止条件确实能用冻结算符集表达**：

```
while  tick  lt  config.ticks
  and  population  gt  0
```

两个子句、**只有合取**、算符 `lt`/`gt` 都在冻结的六个比较关系内、两个 `observable`
都是**已声明的观测量名**（不是任意状态路径）。配置经 AST 检查为纯数据。

**没有为了让它通过而扩算符集**——那是预注册点名禁止的、inner-platform effect 的第一步。

## 3. 失败的两个原因，都是结构性的

### 3.1 `run` 是混合部件

21 行里只有中间的 `while` 属 `simulator`，前后是 `frame`：

| 段 | 性质 |
|---|---|
| 追加 tick-0 快照 | `frame` |
| `while ...: self.tick()` | `simulator`（本次要吃的）|
| 组装 `WorldRunResult` | `frame` |

只吃循环则 `run` 不消失；连带搬走前后两段则超出 goal §4 划定的范围。**两条路都是 H0-a。**

**这条反过来打了第七世界一记**：它把 `run` 整体判为 `simulator`——**归类粒度是「函数」，
而真实的类型边界在函数内部**。第七世界的词表封闭性结论不受影响（它判的是 H0），
但**粒度问题是新的，且它直接导致了本次的 C1 失败**。

### 3.2 装配所有权冲突

通用 harness 假设**自己拥有引擎装配**（`GenericWorld.__init__` 建 `ReferenceKernel`
并注册机制），而 World 1 **已经拥有**。接线时只能写成
`GenericWorld.__new__(GenericWorld)` 再手填字段——**那个写法本身就是证据：harness 是
并排贴上去借一个循环，不是吃掉。**

**卡住的不是表达能力，是部件边界与装配所有权。** 这个区分决定下一步不该去扩配置语言。

## 4. C3 未评估，如实记

重跑 v0.2 gate 需要外部 L2 录制根目录（`--l2-root` / `--parworlds`），本次不可得。
合取判据在 C1 已断，C3 的取值不改变 verdict——**但未评估就是未评估，不写成通过也不
写成失败。**

## 5. 中途叫停一次

接 bolt-on 时进了 debug 螺旋。**继续调是在为一个不可能改变结论的度量烧预算**
（C1 已断，合取到此为止），而且 bolt-on 本来就不是合法的「吃掉」。回退到 HEAD，
保留 `core/harness.py` 的循环支持与 `resource_foraging/spec.py` 作为 C2 的证据。

## 6. 一个 goal 写法上的自我批评

goal 的达成判据被写成了**三条合取**，与 verdict 的 H1 实际上是同一件事——**违反 G4
（goal 判据不依赖 H1）**，而我在冻结时没看出来。goal 真正想买的只有一条：
「终止条件能不能纯数据表达」，那一条**买到了**（C2 通过）。

判定仍按字面记为 `not_achieved`——**不许事后把判据改窄来让自己通过**。
教训记入 skill：**达成判据写完要跑一遍 G4——如果它与 H1 逐条重合，那就是没写对。**
