# 第十个里程碑：判定这道接缝，从八个已有实现里提取

- **状态**：已判定（2026-09-03）。**INVALID**——触发一条预注册没预见到的 IC。
- **证据**：`results/tenth/summary.json`
- **实现**：`packages/newlife/src/newlife/core/verdict_seam.py`（Definition）
- **预注册**：exloop `preregistrations/2026-09-03-newlife-verdict-seam.md`，冻结于 `a517d29`
- **不是一个世界**，是八道接缝里 D（判定）的第一次提取。

---

## 1. 结果

| 判据 | 结果 |
|---|---|
| C1 三个 runner 都经由同一 Definition 产出判定 | **PASS** |
| C2 值域仍是三值、未放宽 | **PASS** |
| C3 三份产物逐字节不变 | **2/3** |

**verdict: INVALID。** 不是 H0——见 §3。

## 2. 三代表示都装进去了，而且没有放宽值域

关键是把两件被同一个键名混在一起的事分开命名：

- **判定是三值**（`decide()` 的值域仍是 `H1/H0/INVALID`，一步没放宽）
- **假设名是标签**，由**声明式映射**给出

| runner | 代 | 渲染声明 |
|---|---|---|
| `second` | 一：`verdict` 装假设名 + `passed` | `passed_key="passed"`，`label_key="verdict"`，映射 `{H1: "ms_minimal_coalescent_reproducible", H0: "verdict_withheld"}`，`sort_keys=True` |
| `third` | 二：只有 `passed` | `verdict_key=None, passed_key="passed"` |
| `seventh` | 四：三值 + `invalid` | `verdict_key="verdict"` |

**`second` 的 runner 里因此不留 `if/else`**——映射进配置，Definition 按三值查表。
映射必须对值域**穷尽**，缺一个即报错（缺一个就是留了后门）。

这是第八世界 `reuse_trace` 那招的复用：**Definition 算判定，配置给名字。**

## 3. IC-4：为什么不是 H0

`seventh` 对不上冻结基线，**原因不在接缝**：

> 第八世界从 `mechanisms/fourth_world/world.py` 删去 4 个部件，而第七世界的分类表仍
> 声明着它们 → `phantom: 4` → 覆盖失败 → verdict 由 `H0` 变 `INVALID`。

**把改动收起来跑原版，原版给出同样的 INVALID。** 接缝是清白的，另有实测：
`seventh` 原版 vs 接 Definition 后**逐字节相同**。

按字面，「逐字节不变」有一条不成立就是 H0。但 **H0 的含义是「Definition 装不下」，
而这里装得下**——照字面判会把「第七世界产物过期」误记成「接缝装不下第四代表示」。
**预注册没覆盖的情形不许硬塞进 H0/H1**，故记 IC-4 判 INVALID。

## 4. 真正的发现：第七世界的判定已经不可复现

这是本次最值钱的产出，而且**此前没有任何东西会发现它**——因为**没有任何东西在重跑旧世界的 verdict**。

一个里程碑判完、产物提交、然后下一个里程碑改动了它依赖的代码，**旧判定就悄悄失效了**。
这正是「判定该有一道接缝」的最强论据：接缝补上，重跑全部旧 verdict 才成为一条可执行的命令。

## 5. 负控

把 Definition 的标签映射改成常量 `"MUTANT"` → `second` 的产物立刻与冻结基线不同；
恢复后逐字节相同。**证明 Definition 真的参与了产出，不是摆设。**

## 6. 边界

- 只接了三个，其余五个未接（预注册 §5）
- 各 runner 的判定逻辑一字未改，只改「怎么被调用」
- **C2 的「未放宽」是机械查的**（`DOMAIN` 必须恰为三值），不是自陈
