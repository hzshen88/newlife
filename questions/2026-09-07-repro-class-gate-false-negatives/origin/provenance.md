# 这个问题从哪来的

不是从 exloop 探索来的。它是上一个里程碑（`2026-09-07-sender-side-operator-derivable`）
收尾后写文档时，自己在文档末尾留下的问题：

> **Status**: the levels above are a convention, not yet a gate. … Whether such a gate can
> actually catch the mutation it is meant to catch — a local library edited without the
> verdict moving — is itself a question worth registering rather than assuming.

那份文档（`docs/writing-a-world.md`，提交 `7e3f75e`）定了三条机械判据，用来支撑
`local` / `portable` / `archived` 三级声明。本里程碑问的是：**这三条够不够。**

## 起草期已经看过的（一律算 seen）

三条判据在各自最直白的失效场景下实测有效：

| 判据 | 实测 |
|---|---|
| `git status --porcelain` 为空 | 用于 dirty 检测 |
| `git branch -r --contains <commit>` 非空 | 无 remote 的仓库返回空；有 remote 但未 push 的 commit 也返回空；已 push 的返回 `origin/main` |
| `dist-info/direct_url.json` 的 `dir_info.editable` | 在本仓 venv 里识别出 newlife 与 proofroot 两个可编辑安装 |

**没跑过的是边缘情况**——那才是这一轮的 blind。

## 检索（三个来源，结论 unknown）

| 来源 | 结果 |
|---|---|
| 项目内部 | 三条判据是 2026-09-07 新写的，除上表外没有任何使用记录 |
| git 边缘情况 | **shallow clone 里 `git rev-list --merges` 会假阴性**——明明有 merge commit 却返回空；submodule 与 `depth=1` 冲突，而 CI runner 默认就是 depth=1。**同一族命令在同一种仓库形态下失效，是直接先例** |
| artifact evaluation（ctuning 的 checklist 等） | 存在成熟的可复现性清单，但它们是**给人评审用的**，不是机械 gate；没有回答「某组特定机械判据的假阴性在哪」 |

按 `newlife-goal` 的检索三分类，这是第二种（已知但只是上一层）：git 这些边缘情况本身
是已知的，**这套特定判据在它们面前的表现是未知的**。

## 变异清单的初步草案（冻结前定稿）

已知应被抓（pilot 会跑，属 seen）：工作区 dirty · 无 remote · commit 未 push ·
源码改动而版本号不变 · 数据文件改动。

未跑过（blind 候选）：**shallow clone** · **submodule 未初始化** ·
**`.gitattributes` 的 filter/smudge 使 checkout 内容不等于仓库内容** · **LFS 指针未拉取**。
每一种都要先证明它确实破坏可复现性——证明不了的不得进清单，否则就是拿一个不破坏
任何东西的变异去判「判据抓住了」。
