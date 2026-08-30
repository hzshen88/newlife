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

跨语言逐值比对（L2 录制 draw 注入）见 `scripts/compare_world1.py` 与
`docs/worlds/001-resource-foraging.md` §4。

import-lint 强制本目录零 Python 文件——应用层没有 runtime 代码可写，
这就是"配置化"的机制化形态（proposal §2 目标 5）。
