#!/usr/bin/env python3
"""goal 冻结前的门 —— **实现已搬进 newlife 包，本文件只是入口。**

搬家原因（2026-09-05）：这道门检查的六个锚正是 `decidable-question` skill 产出的，
而 skill 随 wheel 发布、门不发布——**用户拿到了会写锚的 skill，却拿不到验锚的门**，
四份真实 `prereg.md` 里锚数是 0。现在 `newlife init` 生成 `goal.md`，
`newlife freeze` 在冻结前挡一道，`newlife check` 一并报告。

本文件保留是因为 exloop 那条文档流水线用它（`run_gates.py` / `gate_selftest.py`
按脚本路径调用）。**它不是第二份实现**：逻辑只有一处，在
`newlife.gates.goal_ready`。两份副本必然漂移——本仓库已经为这个形状付过账
（skill 让用户跑一条库里还不存在的命令，而没有任何机械防线会发现）。
"""

from __future__ import annotations

import sys

from newlife.gates.goal_ready import main

if __name__ == "__main__":
    sys.exit(main())
