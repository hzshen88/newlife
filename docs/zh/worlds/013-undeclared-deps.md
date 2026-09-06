# 第十三个里程碑：非 Python 依赖，缺了会不会静默

- **状态**：已判定（2026-09-03）。**H0 支持**——两条依赖里有一条缺失时**静默产出 summary**。
- **证据**：`results/thirteenth/summary.json`
- **预注册**：exloop `preregistrations/2026-09-03-newlife-undeclared-deps.md`，冻结于 `6c94455`

---

## 1. 穷举结果：`pyproject.toml` 之外共两条

| 依赖 | 代码位置 | 缺失时 |
|---|---|---|
| **`cc`** | `mechanisms/second_world/ms_binary.py:19` | **`hard_fail_named`** ✓ 报 `FileNotFoundError: ... 'cc'` |
| **`git`** | `conform/verdict.py:315` · `eighth_world_verdict.py` · `verdict_rot.py` | **`silent_output`** ✗✗ |

对照组（`third`，两条都用不到）两次都判 `unaffected`——**分类本身有效**，
不会把「用不到」误记成「装作没事」。

## 2. H0 的那一处，design 事前点名过

design §2.3 写在跑之前：

> `git` 缺失 → **三处的处理不一样，这是 H0 的主要嫌疑**：`verdict.py` 用
> `check_output` 会抛；而 `eighth_world_verdict.py` 里我自己写过
> `try/except Exception: pass` → 吞掉异常返回 `None`。**若它因此静默产出 summary，就是 H0。**

**实测证实。** 而且危害比「产出了 summary」这句话更具体：

它产出的是 **`verdict: INVALID`，理由写成「基线不可得」**——读的人会以为是基线的问题，
**而真实原因是 `git` 不在**。**不是没报警，是报错了案由。**

## 3. 为什么这条比 `cc` 那条更值得记

`cc` 缺失时进程直接炸，谁都不会误解。`git` 缺失时**流程照常走完、产出一份格式完好的
判定文件**——它进得了 `results/`、进得了 git 历史、下次被人当成事实读。

**本项目一路上第四次栽在同一形状**（前三次：`mutation_scan` 的空集恒真、
`gate_coverage_check` 的 `if m else 0`、`verdict_rot` 的跨仓库 commit 解析失败当成没变动）。
**而这一次在环境层，`silent_degradation_scan` 完全够不着。**

## 4. 边界

- **穷举只覆盖已知会被执行的路径**（goal §5 事前声明）。声明的是「已知需要什么」，
  **不是「只需要这些」**——这句必须留着，不许收尾时悄悄变强。
- 屏蔽只改子进程的 `PATH`，**不删系统文件**；每次屏蔽后先确认 `shutil.which` 找不到，
  确认不了即 IC-1（本次未触发）。
- **本里程碑不修**（goal §4）：不引入 Nix、不做容器、不写安装逻辑。
  修 `eighth` 那处吞异常是下一步的事。
