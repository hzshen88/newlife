# World 5：gate 自身的检查覆盖率

- **状态**：已判定（2026-09-03）。**H0 支持——八个里程碑以来第一个。**
- **证据**：`results/fifth-world/summary.json`（`verdict: "H0"`，schema `newlife.fifth-world.gate.v1`）
- **verdict runner**：`packages/newlife/src/newlife/conform/fifth_world_verdict.py`
- **分类原始数据**：exloop `docs/science-superpowers/plans/verification/w5-classification-final.json`
- **goal**：exloop `goals/2026-09-02-newlife-gate-check-mutation-coverage.md`（`@frozen` 锚机械保证）

---

## 1. 结果

47 个 check 全部定级，**3 个 `hollow`**：

| 分类 | 数量 | 含义 |
|---|---|---|
| `auto` | 24 | 既有自动变异空间抓得住 |
| `hand` | 15 | 自动空间碰不到，但按断言反推的变异能让它红 |
| `anchored` | 5 | check 自己从不红，但 fact 被文档锚住、对账器红 |
| **`hollow`** | **3** | 在被声明的变异空间内构造不出使断言为假的变异 |
| `IC-1` | 0 | 无未讨清的界定失败 |

**三个 hollow：**

1. **`moran_plan_grid.py: IC-1-tractable-at-frozen-N`** —— 判定条件是**字面量 `True`**，
   facts 是两个冻结常量。**任何变异都不可能让它变红。** 这不是覆盖率不足，是这条
   check 从未检验任何东西。
2. **`moran_fixation_check.py: check-2`** —— 记账式计数断言（`total == expected_count == 95`），
   其 covers 内的变异改的是**值**，而它数的是**个数**。
3. **`moran_fixation_check.py: check-5`** —— 判据是内联字面量算术（`M=4, p=3/10`），
   不经任何生产函数，covers 内的变异对它无影响。

后两条的性质与第一条不同：它们**有内容**（check-2 用两条独立推导互相对账再钉字面量，
check-5 用直接枚举当 oracle），只是**它们检验的对象不是 `covers` 指向的那些函数**。
这暴露出一个二阶事实——见 §3。

## 2. 方法

- **位置由 `covers` 定，方向由断言反推。** `covers` 是运行时观测的，所以它精确说出这条
  check 实际行使了什么；空 covers 沿「被复用值 → 产出它的 check」逐层回溯（最深回溯 4 层，
  `moran_genealogy_plan.py: check-6`）。
- **崩溃不算抓住。** 全程记录 `Traceback` 计数。判据是「目标 check 有没有打 FAIL」，
  而不是「exit code 非零」。
- **`anchored` 与 check 自身变红分开记。** 例：`acceptance_region` 整体右移 1，
  check 自己**不红**（它断言的是「验收域落在 P_i_grid ± δ 内」这个包含关系，右移 1 仍在带内），
  但 facts 变了、被锚住，对账器红。

## 3. 二阶发现：`covers` 会误归因

`covers` 的语义是「自上次 report 起新观测到的调用」，它**不等于**「算出这条 check
所断言的那个值的东西」。当一条 check 的判据是内联计算（check-2、check-5）或纯记账时，
`covers` 会指向一批与它无关的函数，于是「在 covers 内变异」这条位置规则**测不到它**。

**后果**：本次的 `hollow` 计数里，有 2/3 是这个误归因造成的，而不是 check 真的空洞。
分类判据本身是诚实的（它只承诺「在被声明的空间内」），但读者会误读。这一条必须
和数字一起报，否则「3 个 hollow」会被当成「3 条 check 没用」。

## 4. 自动变异空间的实测覆盖

| 脚本 | check | `auto` 覆盖 |
|---|---|---|
| `moran_genealogy_check.py` | 15 | **15/15** |
| `moran_fixation_check.py` | 14 | 9/14 |
| `moran_plan_grid.py` | 11 | **0/11** |
| `moran_genealogy_plan.py` | 7 | **0/7** |

**两个 plan 侧脚本的自动覆盖率是零。** 它们直到本里程碑的准备阶段（`094c6c8`）才
第一次可被扫描——在此之前 `mutation_scan` 因标签正则写死前缀而在空集上恒真，
长期显示「没有变异逃逸」。**18/47 的 check 处于「显示已覆盖、实际从未被测」的状态。**

崩溃率也高：`moran_plan_grid.py` 的 32 个自动变异体里 **22 个崩溃**。原因是算子
（`expr*2` / `expr+1` / 常数）作用在返回 list / dict / tuple 的函数上，要么抛异常，
要么是对实际取用的值的空操作（`return P * 2` 把列表长度翻倍，而调用方取 `P[I0]`）。

## 5. 如实记录：本轮的一次判断失误

曾据 `grid_native_P` 的 `*2` 变异不改变任何 fact，判 `grid-computed` 可能空洞。
复测推翻：那是算子对列表返回的空操作（§4），换成逐元素偏 1% 后该 check 立刻变红。

**留档的理由**：这正是本里程碑要测的那类错误的活样本——「形状像检查、内容不检验」
可以发生在检查一方，也可以发生在**变异**一方。用一个测不出问题的变异去判「空洞」，
与用一个恒真的断言去当检查，是同一个错误的两面。
