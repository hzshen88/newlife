# first-world: Resource Foraging（Parworlds Experiment 001）

**本目录是数据，不是代码。** 世界组装与实验协议是配置文件（`resource-foraging-v1`
冻结语义的原样拷贝）；运行入口在库内：

```bash
# 单世界（训练 + 因果 assay）
uv run --package newlife python -m newlife.mechanisms.resource_foraging \
  --config examples/first-world/informative.toml --seed 101 \
  --output runs/first-world/informative-101.json

# 配对对照（同一 seed、唯一受控差异 = 感知信号）
uv run --package newlife python -m newlife.mechanisms.resource_foraging \
  --config examples/first-world/cue_neutral.toml --seed 101 \
  --output runs/first-world/cue_neutral-101.json
```

跨语言逐值比对（L2 录制 draw 注入）使用一个新输出目录运行双条件 gate：

```bash
uv run --package newlife python scripts/run_world1_l2.py \
  --parworlds /path/to/parworlds --out /tmp/newlife-world1-l2-101
```

它会用 Julia recorder 录制 informative 与 cue-neutral，再由
`scripts/compare_world1.py` 对 tick 0/间隔/最终快照、assay 和全部命名流做
proofroot IEEE754 位模式比较。完成后用 gate 验收器生成痛点测量和最终判定：

```bash
uv run --package newlife python scripts/accept_world1_gate.py \
  --parworlds /path/to/parworlds \
  --l2-root /tmp/newlife-world1-l2-101 \
  --out /tmp/newlife-world1-l2-101/gate.json
```

仅重跑已有录制的比较可加 `--reuse-recordings`。

import-lint 强制本目录零 Python 文件——应用层没有 runtime 代码可写，
这就是"配置化"的机制化形态（proposal §2 目标 5）。
