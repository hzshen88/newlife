# Goal — repro class gate false negatives

<!--@evidence: literature_searched=yes, sources=3, verdict=unknown-->
<!--@counterparty: 押「抓得住」的是刚写完那份文档的我自己——三件套（dirty 检查、remote 可达、内容摘要+数据校验和）看起来把该堵的都堵了。押「抓不住」的是熟悉 git 边缘情况的人，而且检索给了直接先例：shallow clone 里 git rev-list --merges 会假阴性，明明有 merge commit 却返回空。同一族的 git branch -r --contains 凭什么不会-->
<!--@attack_layer: conclusion-->
<!--@decides: run-->
<!--@who_changes_behavior: 任何要把本地代码库接进 newlife 并在注册里声称 portable 的人。最近的一个是 hzshen 本人：mapsim 今天是 local（无 remote、111MB 数据在 gitignore 里），要变 portable 就要靠这三条判据背书，而背书错了没人会发现-->
<!--@size_estimate: impl_lines=420, criteria=4, failure_modes=1-->

| Anchor | What it must say | Why it is gated |
|---|---|---|
| `@evidence` | `literature_searched=yes, sources=N, verdict=…` | A search that failed and was silently skipped looks exactly like one that found nothing |
| `@counterparty` | Who would bet the other way, and on what grounds | If nobody would, the result is already inside your expectations |
| `@attack_layer` | `conclusion` \| `premise` \| `definition` | Under attack at the premise a simulation settles nothing |
| `@decides` | `design` \| `run` | Confuse them and a tooling result gets reported as a conclusion about the world |
| `@who_changes_behavior` | A specific person **and** a specific decision | The "unimportant but decidable" bucket passes every later gate |
| `@size_estimate` | `impl_lines=N, criteria=N, failure_modes=1` | No estimate made in advance means nothing to calibrate against |

## 1. What this buys

做完之后，从做不到变成做得到的是：**知道 `writing-a-world.md` 那三条判据在什么情况下会
放行一个实际重跑不出来的注册**——并且这个「什么情况」是列出来的具体清单，不是一句
「可能有边缘情况」。

那份文档（2026-09-07 提交 `7e3f75e`）末尾自己写着：这些等级是约定不是 gate，
「whether such a gate can actually catch the mutation it is meant to catch is itself a
question worth registering rather than assuming」。**这个里程碑就是去回答它。**

**起草期间已经确认的部分**（属于 seen）：三条判据在各自最直白的失效场景下有效——
无 remote 的仓库和未 push 的 commit，`git branch -r --contains` 都返回空；可编辑安装
靠 `dist-info/direct_url.json` 的 `dir_info.editable` 能识别。**没跑过的是边缘情况**。

## 2. Success criteria

判据是合取，且**不依赖 H1**——不管最后找不找得到假阴性，只要这三件事做到了就算达成。
H0（存在假阴性）成立时下面三条仍应满足。

- **C1**：变异清单在冻结前列定，每一种都**先证明它确实破坏可复现性**——即在该变异下
  重跑得到的东西与原始不同（或根本跑不起来）。**证明由代码给出，不由散文断言。**
  证明不了的变异不得进入清单：用一个不破坏任何东西的变异去判「判据抓住了」，
  是本项目栽过两次的形状。
- **C2**：每一种变异的判定结果取自封闭词表 `caught` / `false_negative` / `not_a_mutation`，
  由代码算出，逐条落进产物。
- **C3**：假阴性（若有）能指出**是哪一条判据漏的**，而不只是「整体漏了」——修补需要
  知道补哪一条。

## 3. Explicitly not doing

- **不实现那个 gate**。本次只回答「这三条判据够不够」；够不够的答案出来之前建 gate，
  就是为一个还没测量过的需求建设施。
- **不碰 `archived` 那一级**。DOI / 归档解析涉及外部服务，不在本次范围。
- **不判「私有 remote」**。文档里已写明：可达的 remote 未必是公开的，而这一点**没有任何
  机械测试能判**——已知答案的东西不该进清单。
- **不拿 mapsim 做被试品**。它是动机来源；构造变异需要一个可以随意破坏的仓库，
  用真项目会把破坏和真实状态混在一起。

## 4. Risks declared in advance

- **清单不可能穷尽**。找到 N 个假阴性不等于只有 N 个；**找不到也不等于没有**。收尾时
  「我们测了这几种」和「这套判据是安全的」必须是两句话，前者不得冒充后者。
  这是第十七个里程碑「穷举有保质期」的同一形状。
- **构造出的变异可能不真实**：一个实验室里造得出、真实使用中不会发生的场景，抓不住
  也不说明什么。每个变异要附一句它在什么真实流程里会出现（例如 CI runner 默认 depth=1）。
- **判据的实现与文档可能不一致**：本次测的是文档写下的那三条判据；如果实现时写歪了，
  测的就是别的东西。判据实现必须逐字对应文档的表述，并在产物里引用。
- **git 行为随版本变化**。结论绑定在产物记录的 git 版本上，不是永久事实。

## 5. Closeout judgement

**判定：`achieved`**

prereg verdict 是 **H0**（`results/reproduction.json`）；goal 判 `achieved`。两者物理分开，
而且事前就把达成判据写成独立于 H1——**问题被回答了**，答案恰好是「有假阴性」。

### 对照第 2 节逐条

| 事前判据 | 实际 | 结论 |
|---|---|---|
| **C1** 每种变异先自证破坏可复现性，证明由代码给出 | 七种变异全部跑了自证（重建后结果不同或重建失败）。三种边缘变异自证不通过，被记 `not_a_mutation` 并排除在分子分母外 | **满足** |
| **C2** 判定取自封闭词表，由代码算出 | `caught` / `false_negative` / `not_a_mutation` / `construction_failed`，逐条落进产物 | **满足** |
| **C3** 假阴性能指出漏的是哪条判据 | `submodule_uninitialised` 的 `caught_by` 为空数组——三条判据**全部**漏掉，而不是笼统「整体漏了」 | **满足** |

### 结论：找到一个假阴性

**`submodule_uninitialised`**：依赖放在 submodule 里的仓库，工作区 clean、commit 在 remote
上可达、内容摘要与数据校验和全部一致——**三条判据一条都不红**；而重建者按注册记下的信息
clone 下来，`lib/` 是空的，跑不起来（`rebuild_failed=True`）。

三条各自独立地漏掉它：`git status --porcelain` 对未初始化的 submodule 返回空；
`git ls-files` 里 submodule 是 gitlink 条目而非文件，内容不进摘要；commit 确实在 remote 上，
可达性判据本来就该通过。**而注册里没有任何地方能写下「这个仓库有 submodule，
重建要 --recursive」**——重建流程不得依赖注册之外的知识，这是实现里冻住的建模前提。

### 如实记录（不润色）

1. **另外三种 `not_a_mutation` 有两种不同含义，不能混为一谈。**
   `shallow_clone` 是**真的无害**——shallow clone 里代码是全的，checkout 记录的 commit
   能成功，这个重建流程不受影响。而 `gitattributes_filter` 与 `lfs_pointer_not_fetched`
   **更可能是在本地 `file://` remote 上没构造成功**（LFS 需要真正的 LFS endpoint）。
   **「测过了没事」与「没测成」是两句话**，前者不得冒充后者。
2. **清单不穷尽。** 找到一个假阴性不等于只有一个；三个没测出破坏也不等于没有。
   这是第十七个里程碑「穷举有保质期」的同一形状，事前已在第 4 节声明。
3. **结论绑定在 git 2.50.1 上**，产物记录了版本字符串。边缘行为随版本变。
4. **pilot 抓出实验台自己的两个建模缺陷**，都不跑发现不了：重建函数绕过 remote 配置
   （于是「删掉 remote」这个变异根本没生效）；变异清单混进了两种「破坏」
   （`source_edited`/`data_edited` 破坏的是「注册与实际不符」而非「能不能重建」，
   若把定义扩过去就成了用判据定义破坏的恒真圈——**上一个里程碑 S5 正是这么塌的**）。
   两者都在 pilot 阶段修掉，并把教训冻成了 F6。
5. **规模估计对照**：事前估 `impl_lines=420`，实际 488 行（含骨架约 373 行的基线，
   净增约 115 行的判据实现 + 变异构造）。**按总行数看高估 15%，按净增看严重低估**
   ——事前把「骨架」和「新增」混在一个数里估，是这次估计口径的缺陷，下次分开报。

### 对应的 prereg verdict（只作交叉引用）

`questions/2026-09-07-repro-class-gate-false-negatives/results/reproduction.json` → `H0`
