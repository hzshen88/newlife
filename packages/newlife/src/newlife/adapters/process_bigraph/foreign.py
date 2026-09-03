"""把一个**第三方 process-bigraph `Process`** 接进 newlife 的契约。

第三方的 `Process` 没有 Effect 的概念：它的 `update()` **直接返回引擎 update**。
newlife 的契约要求每一次写入都来自已注册机制声明过的 `Effect`，由
`BiologicalProfile.stage` 校验。这两件事之间需要一层翻译。

**接法**：`GuardedProcess.update` 本身就是 `propose → stage → lower` 三步，
校验在 `stage`。所以这里只实现 `propose`——第三方的输出**只能**经 `stage` 进入
store，适配器不自己放行、不直接返回引擎 update（预注册 `8d65582` §3 F2）。

**第三方的源码不被改动**：这里是**实例化并调用**它，不是子类化并覆写 `update`（F1）。
端口（`inputs()`/`outputs()`）也**向它要**，不由我们重述。

---

**这一层的脆点，写在最显眼处。** `PortBinding` 那张表**只能由我们代写**，
而其中两处信息第三方根本不提供：

- **这个端口对应哪条状态路径** —— `outputs()` 只说类型（`'float'`），不说位置
- **写入是 `add` 还是 `set`** —— `Grow` 返回的是增量，但签名说不出来；填错
  `set` 会把质量覆写成增量，**而结果照样跑得出来**

FMI 用「接口描述由模型作者随实现一起交付」解决这件事。这里没有那个东西。
所以本层给出的是「契约对**被代写的声明**有强制力」，**不是**「第三方可以安全地接」。
"""

from __future__ import annotations

import copy
import dataclasses
import importlib
from typing import Any, Mapping, Sequence

from process_bigraph import Composite, Process, allocate_core

from newlife.adapters.process_bigraph.wrapper import GuardedProcess, Proposal
from newlife.core.contracts import OPERATIONS, StateDelta
from newlife.core.errors import SpecValidationError


@dataclasses.dataclass(frozen=True, slots=True)
class PortBinding:
    """第三方的一个输出端口 → newlife 的一条状态路径与写入算符。

    **这是我们替第三方说的话。** 它是断言，不是从第三方读出来的事实。
    """

    port: str
    path: tuple[str, ...]
    operation: str

    def __post_init__(self) -> None:
        if self.operation not in OPERATIONS:
            raise SpecValidationError(
                f"未知的写入算符 {self.operation!r}；词表是封闭的：{sorted(OPERATIONS)}"
            )


def admit(
    foreign_cls: type[Process],
    bindings: Sequence[PortBinding],
    lowering: Mapping[str, tuple[str, str]],
) -> type[GuardedProcess]:
    """生成一个把 `foreign_cls` 接进契约的 `GuardedProcess` 子类。"""
    bound = tuple(bindings)
    by_port = {b.port: b for b in bound}
    if len(by_port) != len(bound):
        raise SpecValidationError("同一个端口被声明了两次")

    class _Admitted(GuardedProcess):
        # 第三方的 config 键并进来，这样 pb 能按 node config 把它们传下去
        config_schema = {
            "mechanism_id": "string",
            **dict(getattr(foreign_cls, "config_schema", {})),
        }
        lowering_table = dict(lowering)

        def __init__(self, config=None, core=None) -> None:
            super().__init__(config, core)
            foreign_keys = getattr(foreign_cls, "config_schema", {})
            self._foreign = foreign_cls(
                {k: self.config[k] for k in foreign_keys if k in self.config}, core
            )

        # 端口向第三方要，不由我们重述
        def inputs(self) -> Any:
            return self._foreign.inputs()

        def outputs(self) -> Any:
            return self._foreign.outputs()

        def propose(self, state: dict[str, Any], interval: float) -> Proposal:
            raw = self._foreign.update(state, interval)
            if not isinstance(raw, Mapping):
                raise SpecValidationError(
                    f"{foreign_cls.__name__}.update 返回了 {type(raw).__name__}，"
                    "本适配器只接受端口键的映射"
                )
            effects = []
            for port, value in raw.items():
                binding = by_port.get(port)
                if binding is None:
                    # 第三方写了一个我们没为它声明的端口——**硬失败**，
                    # 不静默丢弃：丢弃等于让它的写入消失而无人知晓。
                    raise SpecValidationError(
                        f"{foreign_cls.__name__} 写了未声明的端口 {port!r}；"
                        f"已声明的是 {sorted(by_port)}"
                    )
                effects.append(StateDelta(binding.path, binding.operation, value))
            return Proposal(effects=tuple(effects))

    _Admitted.__name__ = f"Admitted_{foreign_cls.__name__}"
    _Admitted.__doc__ = (
        f"{foreign_cls.__module__}.{foreign_cls.__name__} 经 newlife 契约接入。"
    )
    return _Admitted


def resolve_foreign(dotted: str) -> type[Process]:
    """按点分路径取第三方类。**字符串是数据**——声明侧因此不必 import vendor。"""
    module_path, attr = dotted.split(":")
    return getattr(importlib.import_module(module_path), attr)


def build_composite(
    foreign_dotted: str,
    *,
    identity: str,
    bindings: Sequence[PortBinding],
    lowering: Mapping[str, tuple[str, str]],
    config: Mapping[str, Any],
    state_roots: Mapping[str, Any],
    in_wiring: Mapping[str, list[str]],
    out_wiring: Mapping[str, list[str]],
    contract: bool,
    register_types: Any = None,
) -> Composite:
    """搭一个跑第三方 process 的 composite。

    `contract=False` 时**用裸的第三方类**、不经契约——元负控要的正是这条路径。

    **读写分开两张接线表**：第十六个里程碑发现单表不够——`MonodKinetics` 的
    `substrates` 端口**读 `local`、写 `exchange`**，而第十五个里程碑接的 `Grow`
    读写同路径，单表看着够用。**一个 provider 时看着对，两个时就塌**（第九世界的教训）。
    """
    foreign_cls = resolve_foreign(foreign_dotted)
    cls = admit(foreign_cls, bindings, lowering) if contract else foreign_cls
    core = allocate_core()
    if register_types is not None:
        # 第三方交付的类型词表（对照本体文献：词表即独立组件间的接口契约）。
        # **这一半不是我们代写的**——第十五个里程碑接的 Grow 连这个都没有。
        register_types(core)
    core.register_link(identity, cls)
    node_config = dict(config)
    if contract:
        node_config["mechanism_id"] = identity
    state: dict[str, Any] = {
        # 顶层值不一定是映射——MonodKinetics 的 mass 是标量（第十六个里程碑撞到）
        **copy.deepcopy(dict(state_roots)),
        "node": {
            "_type": "process",
            "address": f"local:{identity}",
            "config": node_config,
            "inputs": {k: list(v) for k, v in in_wiring.items()},
            "outputs": {k: list(v) for k, v in out_wiring.items()},
            "interval": 1.0,
        },
    }
    return Composite({"state": state}, core=core)


def third_party_types(dotted: str):
    """取第三方交付的类型注册入口。**点分路径是数据**——判定侧因此不 import vendor。

    对照本体文献：**词表是独立组件之间的接口契约**，而这个入口由第三方提供
    （`spatio_flux:register_types`）。第十五个里程碑接的 `Grow` 连这一半都没有。
    """
    module_path, attr = dotted.split(":")
    return getattr(importlib.import_module(module_path), attr)
