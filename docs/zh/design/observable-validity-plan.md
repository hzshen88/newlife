# 工作计划：observable validity

- **状态**：计划 · 2026-10-02 · 阶段 0 进行中
- **设计**：[`gate-observable-validity.md`](gate-observable-validity.md)（第三稿）
- **顺序**：阶段 0 → 阶段 1 → 阶段 2。每个阶段单独提交，中断后从最后一个绿的验收点续接

---

## 阶段 0 — freeze / run 接线测试

**为什么**：`test_gates.py` 保证每个门的 selftest 会被跑，但没有测试断言 freeze / run 真的调用了它（设计稿 §2 原则 4）。

**现状（2026-10-02 核对）**：

| 门模块 | 调用方 | 位置 |
|---|---|---|
| `goal_ready` | freeze | `scaffold/__init__.py:299` |
| `pilot_coverage` | freeze | `scaffold/__init__.py:313` |
| `judgement_design` | freeze（仅 `seeded/stochastic`，经 `reproduction_class_gate`） | `scaffold/__init__.py:244` |
| `vacuous_criterion_scan`、`silent_degradation_scan` | freeze | `scaffold/__init__.py:337` |
| `unit_alignment` | run | `cli.py:422` |
| `reproduction_class` | 无——问题 `2026-09-06-reproduction-class-declarability` 的研究用分类器 | 豁免 |

**步骤**：

1. 新建 `packages/newlife/tests/test_gate_wiring.py`：按目录枚举 `newlife.gates`（照 `test_gates.py::_gates()`）；一张接线表、一张带理由的豁免表；每个模块必须恰好在其一。
2. 行为式验证：把各门的 `main` 换成"记录调用并返回 0"，对声明 `stochastic` 的夹具跑 `scaffold.freeze`、对夹具跑 `newlife run`，断言接线表里的门全部被调用。
3. 变异验证（手动，结果记进提交说明）：注释掉 freeze 里的 `pilot_coverage.main(...)` ⇒ 红；在 `newlife/gates/` 放一个空模块 ⇒ 红。

**验收**：

```bash
uv run pytest packages/newlife/tests/test_gate_wiring.py -q
```

```bash
uv run pytest packages/newlife/tests -q
```

**提交**：`test(gates): assert every shipped gate is wired into freeze or run`

---

## 阶段 1 — M7 估计器校准

1. `newlife/stochastic/schema.py`：`REQUIRED_QUANTITY` 加 `calibration`；形状检查（二选一、`family` / `not_applicable` 非空）；文档串示例加 M7。
2. `newlife/gates/judgement_design.py`：`consistency_problems` 加 §3.3 的三步；`_selftest` 加设计稿 §3.6 的 6 条变异。
3. 现有夹具补 `calibration`：`judgement_design._complete()`、`tests/test_reproduction_class_gate.py` 等用到完整设计文件的地方。
4. 用户文档：`skills/newlife-prereg/references/design.md` 六问表加 M7；`SKILL.md` 与 `scaffold/__init__.py:327` 的 "six questions" 改为 "seven"。
5. `CHANGELOG.md`：迁移说明。

**验收**：

```bash
uv run python -m newlife.gates.judgement_design --selftest
```

```bash
uv run pytest packages/newlife/tests -q
```

```bash
uv run ruff check packages/newlife
```

**提交**：`feat(judgement-design): M7 — compare estimator bias on known truth with the committed effect`

---

## 阶段 2 — 回放与收尾

1. 用险情 B 的真实数字做一个回放夹具（已知真值上旧口径偏 +0.0325，效应 ~0.03），确认 M7 在真实形状上变红。
2. 设计稿状态改为"已实现"，注明实现提交；`docs/README.md` 索引不需要改（它只列 `zh/` 目录）。
3. 发版按 `docs/releasing.md`。

---

## 备忘（不排期）

- **O1 重启条件**：再出现一起"声明的设置 ≠ 实际生效的设置"的险情。
- O2 / O4：见设计稿 §5。
