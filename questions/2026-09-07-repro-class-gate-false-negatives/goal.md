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

(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)
