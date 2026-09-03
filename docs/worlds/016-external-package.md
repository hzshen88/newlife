# 第十六个里程碑 —— 一个真正独立的第三方包

- **goal**：`exloop` `goals/2026-09-03-newlife-external-package.md`（冻结 `4493856`）
- **预注册**：`preregistrations/2026-09-03-newlife-external-package.md`（冻结 `588137e`）
- **判定**：**H1** —— `results/sixteenth/summary.json`（`c8e19a68…`，两次重跑稳定）
- **goal 收尾判定**：`achieved`（成色仍有保留，但**比第十五个里程碑实了一层**，见 §5）

---

## 1. 上一个里程碑的结论下早了

第十五个里程碑接的 `Grow` **住在 `process_bigraph` 包里面**——是我们没写没改的代码，
但不是「别人生态里的一个包」。当时只查了两个候选就断言「生态不通」，**搜索太窄**。

这次系统找了一轮：

| 包 | 版本 | 与 pb 1.8.3 |
|---|---|---|
| `biosimulator-processes` | 0.3.19 | ✗ `ImportError: ProcessTypes` |
| `vivarium-interface` | 0.0.5 | ✗ 同上 |
| `viva-munk` | 0.0.2 | ✗ **未声明依赖** `spatio_flux`；补装后仍要它的旧版子模块 |
| **`spatio-flux`** | **1.4.0** | **✓ 干净共存** |

`spatio-flux` 的 5 个模块、11 个 `Process`/`Step` 全部 import 成功，含 `dfba`
（动态通量平衡分析）、`diffusion_advection`、`monod_kinetics`。

> **不通的是那两个入口包，不是整个生态。** 上次的结论要收回。

三个失败包有一个共同形状值得记：**都没有把自己的依赖说清楚**——前两个没给 pb 版本
下界，第三个漏声明了整个 `spatio_flux`。安装一律静默成功，import 才炸。

## 2. 结果

接的是 `spatio_flux.processes.monod_kinetics.MonodKinetics`，**源码零改动、
不子类化覆写 `update`**。

| 单元 | 结果 |
|---|---|
| W0 安全绳（第十五个里程碑产物） | 逐字节不变 `a4f92066…` |
| W1 第三方未被改动 | 仍定义在 `spatio_flux.processes.monod_kinetics`，位于 site-packages |
| W2 忠实性：与**裸 pb**（不 import 任何 newlife） | `mass` 与 `exchange` 两条轨迹逐字节相同 |
| W3 正控 | 生物量增长且葡萄糖被消耗（`exchange` 为负） |
| W4 负控甲：代写声明填错路径 | `CommitAuthorityError`，状态不变 |
| W5 负控乙：不声明 `StateDelta` | 同上 |
| W6 **元负控**：同一份错误声明**绕开契约** | **不被拒** —— 拒绝确实是契约干的 |

## 3. 为什么这个比 `Grow` 难

| | `Grow`（第十五） | `MonodKinetics`（本次） |
|---|---|---|
| 来源 | pb 包**内部** | **独立发行的第三方包** |
| 类型 | 只有 `float` | **自带类型词表**（`register_types(core)`） |
| 输出端口 | 1 个 | **2 个，其中一个是 `map`** |
| 接线 | 读写同路径 | **读 `local`，写 `exchange`** |

## 4. 撞出来的三处，第二处是真发现

**① `state_roots` 假定顶层值是映射。** `MonodKinetics` 的 `mass` 是标量。改通用深拷贝。

**② `lowering_table` 按 Effect 类别做键 → 一个机制每类 Effect 只能写一个端口。**
`MonodKinetics` 写两个（`biomass` 与 `substrates`），于是两条 `StateDelta` 全落到
同一个端口上，`mass`（正浮点）收到了一个 dict。

> **单端口的 `Grow` 看不出这个限制。一个 provider 时看着对，两个时就塌。**
> 第九世界那条教训（「一道接缝不许在少于三个 provider 时定型」）的又一次实例，
> 这次落在降级表上。

改为**先按 `(类别, 路径)` 找、再退回只按类别**——向后兼容，
`fourteenth` / `fifteenth` 的产物逐字节不变。新增 store handler `sum-map-add`
（按键求和的 map store，增量字典透传）。

**③ 读写异路径。** `substrates` 读 `local`、写 `exchange`。`build_composite` 原来用
**同一张**接线表喂 inputs 与 outputs——`Grow` 读写同路径，单表看着够用。已拆成两张。

**import-lint 第三次咬人**：`spatio_flux` 不在 vendor 白名单。加进白名单，
**这是显式声明，不是给某个文件开豁免**——加一个第三方包必须留在那一行的 diff 里
被人看见；规则 2（只许出现在 `adapters/process_bigraph/` 内）仍然生效。

## 5. 成色：比上一个实了一层，但没有全实

第十五个里程碑的降级理由是「端口→(路径,算符) 那张表只能由我们代写」。

**本次改善的一半是真的**：`spatio-flux` **交付了类型词表**（`register_types(core)`
单一入口），对应本体文献里「本体在独立开发的组件之间充当**接口契约**」。
词表这一半不用我们说了。

**没改善的一半也是真的**：**权限声明仍由我们代写**——哪条路径归谁、允许发哪类
Effect、写入是增量还是覆写。第三方的 `outputs()` 只说类型（`float` / `map[float]`），
对权限一个字都没说。

> **词表来自第三方，权限仍由我们代写。这两件事在文献里不是同一个问题，
> 本次也不证明第二半可以自动化。**

## 6. 规模估计对照

| | 事前估计 | 实际 |
|---|---|---|
| 实现行数 | 475 | **389（−18%）** |
| 判据条数 | 1 | 1 |
| 可判定的失败方式 | 1 | 1 |

**新校准规则第一次用就过头了。** 成分列全得 **365**，实际 389——**原始估计只差 +7%**；
是「每项各加三成」把它推到 475 的。那条规则基于**一个**数据点（上次 +30%），
overcorrect 了。修正为：**成分列全后直接报，只有当某一项明显是「没做过的类型」时
才给那一项加成**。
