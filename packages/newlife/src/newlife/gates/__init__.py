"""随包发布的门 —— **打在用户自己的文件上**。

这里只放**对一个问题文件夹直接适用**的那几条。其余留在 newlife 仓库的
`scripts/gates/`：`check_goal_ready` 检查的是 exloop 的 goal 锚点格式、
`verify_doc_claims` 需要一份验证脚本台账、`run_gates` 的参数是 goal/question/ledger
三件套——**它们假定了另一套文档流水线，发出去用户也用不上**。

**这不是省略，是归属。** 该发的发，不该发的说清楚为什么不发。

每个模块都保持**可单独运行**（stdlib-only、有 `__main__`、有 `--selftest`），
因为 newlife 仓库自己的 `gate_selftest.py` 靠把它们拷进临时工作区再变异来验证
「门真的会红」。
"""
