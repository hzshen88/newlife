# 这个问题从哪来的

不是从 exloop 探索来的，是从一次具体的接入需求里长出来的（2026-09-07 对话）：

1. 起点是把 `mapsim`（一个自研的 2031 行地理模拟器，H3 六边形网格上跑政权演化）接进
   newlife。它不是 process-bigraph 的 `Process`，属于 `writing-a-world.md` 说的
   「wrap in about twenty lines」那一类。
2. 读那份文档时撞上其中加粗的警告：`PortBinding` 第三个字段说的是 process 返回的是
   *change* 还是 *level*，而 `outputs()` 只给类型、给不出这个；填反了 **不抛异常**，
   数字量级单位都对，**`pilot` 还会把它记成 covered**。
3. mapsim 恰好正是会踩的那一类：`step()` 原地改 `owner` 数组、返回绝对归属（level），
   而文档示例返回的是差值（delta）。照抄示例就静默错配。
4. 检索后发现第十八个里程碑已经解决了**接收端**——`derive.py:110` 的 `probe_operation`
   用 `apply(schema, 1.0, 0.5)` 探出 store type 是 add 还是 set，3/3。但那是纯函数；
   **发送端**（process 返回什么）至今是 `foreign.py:52` 自己写明的
   「an assertion, not a fact read off the third party」。

## 起草期间已经看过的东西（按 prereg 规矩，这些一律算 seen）

- `derive.py` 的 `probe_operation` 实现与它的 `PROBE_STATE=1.0 / PROBE_UPDATE=0.5` 常量
- `foreign.py` 的 `PortBinding` 定义与那句 docstring
- `docs/milestones.md` 第 15/16/17/18 行的结论
- 外部检索两轮：FMI 系（接口说明由模型作者随实现交付，未见推断工作）、
  动态不变量检测系（Daikon 一族，手法上是上一层，未见覆盖 delta/level 这一实例）

## 坑的存在性：已被事前声明，但仍需实测

起草时我以为「坑存不存在」还没验证过。**查证后更正**：第十五个里程碑的预注册
`8d65582` §5 已经事前声明了这一点，`foreign_growth/declaration.py` 的模块 docstring
写着「本文件填错了，没有任何东西会发现」，`BINDINGS` 旁边写着「填 `set` 会把质量
覆写成增量，而结果照样跑得出来」。

所以本问题的前提不是「坑可能不存在」，而是**坑已知存在、接收端已解决（第十八个，3/3）、
发送端能不能推是未知**。

但按本项目纪律，「作者判断」与「实测过」是两回事（`derive.py` 的探针自检就是为此存在）。
pilot 第一件事仍是真跑一次：把 `Grow` 的 `PortBinding("mass", MASS_PATH, "add")` 填成
`set`，确认 (a) `admit()` 不抛错——它硬失败的是 `update` 返回的**形状**，不是语义；
(b) 结果确实不同却无人报警。这两个量都会出现在判据里，所以必须先看过。
