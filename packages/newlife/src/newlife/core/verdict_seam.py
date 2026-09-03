"""判定这道接缝的 Definition：判定是三值，产物的字段名由各世界声明。

判据冻结于 exloop 的预注册（freeze commit `a517d29`）。

**这是提取，不是设计**（Rule of Three / Mike Acton：三个独立编码的案例之后才谈抽象；
本项目有八个）。八个 runner 的共性是：算一堆布尔 → 判出真假 → 写一个顶层 dict →
退出码由判定导出。**唯一真正的分歧在「判定怎么表示」**，四代四样：

| 代 | 表示 | 世界 |
|---|---|---|
| 一 | `passed: bool` + `verdict` 装**假设名** | second |
| 二 | 只有 `passed: bool` | third · fourth |
| 三 | `verdict: "H0"` 且 `passed: false` | fifth |
| 四 | 三值 `H1/H0/INVALID`，无 `passed` | sixth–ninth |

**`verdict` 这个键在第一代装假设名、第四代装三值判定——同名不同义。**
本模块的解法是把两件事分开命名：**判定是三值，假设名是标签**。

**值域不得放宽**（预注册 §2.1 / IC-2）：把它稀释成八个表示的并集，那不是接口，
是把分歧改名叫共性。各世界能变的只有**渲染**——哪个键装什么、要不要排序——
沿用第八世界 `reuse_trace` 的做法：**Definition 算判定，配置给名字**。
逐字节不变是这套渲染忠实与否的检验。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Any, Mapping

H1 = "H1"
H0 = "H0"
INVALID = "INVALID"
DOMAIN = (H1, H0, INVALID)


def decide(*, h1: bool, h0: bool, invalid: bool = False) -> str:
    """三值判定。**恰好一个成立**，否则是调用方的判定逻辑有洞。

    `invalid` 优先：结果作废时不该产生 H0/H1（预注册纪律「任何 IC 触发都不产生 H0」）。
    """
    if invalid:
        return INVALID
    if h1 == h0:
        raise ValueError(
            f"判定不互斥：h1={h1} h0={h0}——合取判据必须恰好落在一边，"
            "两边都真或都假说明还有一条没算"
        )
    return H1 if h1 else H0


def exit_code(verdict: str) -> int:
    """退出码由判定机械导出，不手填。"""
    if verdict not in DOMAIN:
        raise ValueError(f"{verdict!r} 不在值域 {DOMAIN}——值域不得放宽")
    return 0 if verdict == H1 else 1


@dataclasses.dataclass(frozen=True, slots=True)
class RenderSpec:
    """一个世界怎么把三值判定渲染进自己的产物。**纯数据。**

    - `verdict_key`：装三值的键；`None` 表示本世界不写三值（第二代只有 `passed`）
    - `passed_key`：装布尔的键；`None` 表示不写
    - `label_key` / `labels`：装假设名的键，与「三值 → 标签」的声明式映射。
      第一代的 `verdict` 键就是这个。**映射进配置，runner 里不留 if/else**
    - `sort_keys`：本世界产物的序列化约定。第一代用字典序，后面用插入序
    """

    verdict_key: str | None = "verdict"
    passed_key: str | None = None
    label_key: str | None = None
    labels: Mapping[str, str] | None = None
    sort_keys: bool = False
    ensure_ascii: bool = False


def render(verdict: str, body: Mapping[str, Any], spec: RenderSpec) -> dict[str, Any]:
    """把三值判定按本世界的声明写进产物。键的插入顺序由 `body` 决定。"""
    if verdict not in DOMAIN:
        raise ValueError(f"{verdict!r} 不在值域 {DOMAIN}")
    out = dict(body)
    if spec.verdict_key is not None:
        out[spec.verdict_key] = verdict
    if spec.passed_key is not None:
        out[spec.passed_key] = verdict == H1
    if spec.label_key is not None and spec.labels is not None:
        if verdict not in spec.labels:
            raise ValueError(
                f"标签映射没覆盖 {verdict!r}——映射必须对值域穷尽，缺一个就是留了后门"
            )
        out[spec.label_key] = spec.labels[verdict]
    return out


def emit(
    verdict: str, body: Mapping[str, Any], spec: RenderSpec,
    out: pathlib.Path | None = None,
) -> tuple[dict[str, Any], str]:
    """渲染 + 序列化 + 落盘。返回 (产物, 文本)。"""
    summary = render(verdict, body, spec)
    text = json.dumps(
        summary, indent=2, sort_keys=spec.sort_keys, ensure_ascii=spec.ensure_ascii
    ) + "\n"
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    return summary, text
