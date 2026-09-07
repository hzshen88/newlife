# repro class gate false negatives

**Frozen at commit:** _pending_

## 1. Hypothesis

- **H1**：`docs/writing-a-world.md` 定下的三条机械判据（工作区 clean · commit 在 remote 上
  可达 · 内容摘要与数据校验和一致）**没有假阴性**——冻结的边缘变异清单里每一种，
  在自证确实破坏可复现性之后，都被至少一条判据拒绝。
- **H0**：至少一种边缘变异**自证破坏了可复现性，却通过了全部三条判据**。
  **H0 必须指明是哪一种变异、以及漏掉它的是哪一条判据**——修补需要知道补哪一条，
  「整体漏了」不是可用的结论。

## 2. Judgement units (mechanical conjunction, computed by the runner — **never filled in by hand**)

| Unit | What | Passes when | Piloted? |
|---|---|---|---|
| **S0** | Self-reproduction | two independent runs produce byte-identical artifacts | mechanical |
| **S1** | Environment unchanged | the packages installed at run time are exactly those `env.lock` recorded at the freeze | mechanical |
| **S2** | 每个变异确实破坏可复现性 | 清单里每一种变异，按记录信息重建后跑出的结果与实际不同，或重建失败；由代码算出 | **seen** |
| **S3** | every criterion proves it can fail | each predicate returns false on a synthetic counterexample, computed at runtime | mechanical |
| **S4** | 已知变异被抓住 | `dirty_worktree` / `no_remote` / `unpushed_commit` 三种，每种至少一条判据变红 | **seen** |
| **S5** | **边缘变异被抓住** | 下列每一种，**先自证破坏可复现性**，再由至少一条判据拒绝：shallow clone · submodule 未初始化 · `.gitattributes` 的 filter/smudge 使 checkout 内容不等于仓库内容 · LFS 指针未拉取 | **blind** |

**verdict = S0 ∧ S1 ∧ S2 ∧ S3 ∧ S4 ∧ S5.** Any one false → H0; **S0 false → INVALID**

<!--@reproduction_class: deterministic — 所有 git 操作用固定的 author/committer 时间，模型是纯函数；产物不记 commit hash 与临时路径，因为二者每次运行都不同-->

**S5 为什么不是上一个里程碑那种恒真格**：它测的是**经验事实**（shallow clone 下
`git branch -r --contains` 到底返回什么），不是逻辑推论；它不由 S4 蕴含，因为两者作用在
不相交的变异集合上。检索给出的直接先例是：shallow clone 里 `git rev-list --merges`
会假阴性，而没人测过同一族的 `branch -r --contains`。

## 3. Frozen implementation constraints

- **F1**: **Every criterion must be able to go red.** Prove it in the runner at runtime
  with synthetic inputs, not in prose.
- **F2**: `passed` is computed from the conjunction, never assigned.
- **F3**: the artifact records the newlife source digest, the `env.lock` hash, the
  platform, the Python version, **and the `git --version` string**——边缘行为随 git 版本变，
  结论绑定在这个版本上，不是永久事实。
- **F4**: **this question's verdict must not run any other question's runner.**
- **F5**: **每个边缘变异必须自证破坏可复现性**，判定方式与 S2 逐字相同（重建后结果不同
  或重建失败）。**自证不通过的变异记 `not_a_mutation`，不得计入 S5 的分子或分母**——
  用一个不破坏任何东西的变异去判「判据抓住了」，是本项目栽过两次的形状。
- **F6**: 「破坏可复现性」的判定**不得引用三条判据中的任何一条**。引用了就成了用判据
  定义破坏、再看判据抓不抓得住的循环——上一个里程碑的 S5 正是这么变恒真的。
- **F7**: 判定词表封闭为 `caught` / `false_negative` / `not_a_mutation`，不许扩。

## 4. Invalidation conditions (**written separately from the criteria**)

- **IC-1**: a building block fails to produce a result → environment problem, invalid.
- **IC-2**: S1 false (the environment changed) → not a judgement; rebuild and rerun.
- **IC-3**: 判定前 `docs/writing-a-world.md` 里那三条判据的表述被改动 → 作废。
  本轮测的是文档写下的那三条；文档变了，测的就是别的东西。
- **IC-4**（卫生检查，**刻意放在这里而不是合取式里**）：若对照组不可复现——即不施加任何
  变异时重建也跑不出同样结果——则实验台没有判定力，作废。

## 5. Declared in advance: the boundary of the conclusion

即使六格全绿，本次**不建立**下列各项：

1. **不建立「这套判据是安全的」**。清单不可能穷尽：找到 N 个假阴性不等于只有 N 个，
   **找不到也不等于没有**。收尾时「我们测了这几种」与「这套判据没有假阴性」必须是两句话，
   前者不得冒充后者。这是第十七个里程碑「穷举有保质期」的同一形状。
2. **不建立「私有 remote 会被抓住」**。可达的 remote 未必是公开的，而这一点**没有任何
   机械测试能判**；它被刻意排除在清单外，因为答案已知。
3. **不建立 `archived` 那一级的任何结论**。DOI / 归档解析涉及外部服务，不在本次范围。
4. **结论绑定在产物记录的 git 版本上**，不是关于 git 的永久事实。

## Frozen data checksums

- questions/2026-09-07-repro-class-gate-false-negatives/env.lock e4690977847b741fb4824221ba24d88fb877615e
