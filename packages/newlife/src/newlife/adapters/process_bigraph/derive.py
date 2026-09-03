"""从**第三方交付的东西**推导权限声明。

十五、十六、十七接了三个第三方 `Process`，三次成色都被降级，理由是同一句：
第三方交付了类型词表、模型与参数、连接线，**但没有一个说过「哪条路径归我、
我只发这类 Effect」**。那一半三次都由我们手写——**必须人写，接第三方就无法规模化**。

本模块问的是：那四项能不能机械推出来。

| 手写的 | 推导自 |
|---|---|
| `read` 声明 | 第三方接线生成器的**输入**侧路径 |
| `own` 声明 | 同上，**输出**侧 |
| `allowed_effects` | 结构性：这条接入路径上第三方的输出只可能是 `StateDelta` |
| `add` / `set` | **对第三方在自己输出端口上声明的类型做行为探针** |

**行为探针不是「只有类型」。** 类型-效应系统的文献说细粒度权限从接口**类型**推不出来
——对。但注册类型是一个**可执行**对象，问它「1.0 收到 0.5 会变成什么」问的是语义。
`PositiveFloat` 答 1.5（求和），`SetFloat` 答 0.5（覆写）——**探针能分辨**，
这是本模块成立的前提，由判定单元 Y2 每次跑前验一遍。

**本模块不 import 任何 `mechanisms/foreign_*/declaration.py`**（预注册 `f948447` §3 F1），
由判定单元 Y1 读源码机械检查。也不读第三方的**源码**去猜语义（F2）。
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence

from newlife.core.contracts import StateClaim
from newlife.core.errors import SpecValidationError

PROBE_STATE = 1.0
PROBE_UPDATE = 0.5


def unwrap(value: Any) -> Any:
    """`{"_type": "wires", "_default": {...}}` → `{...}`。

    第三方的生成器有的直接给字典，有的裹一层带默认值的 schema 壳
    （`get_kinetic_particle_composition` 是后者）。
    """
    if isinstance(value, Mapping) and "_default" in value and "_type" in value:
        return value["_default"]
    return value


def process_nodes(tree: Any, address_suffix: str) -> Iterator[Mapping[str, Any]]:
    """在第三方生成器的返回结构里找出地址以 `address_suffix` 结尾的 process/step 节点。

    **一个遍历器吃掉三种形状**：顶层节点（dfba）、嵌套在 `_value` 下（monod）、
    藏在一个 composite 里（grow）。比给每个生成器各写一个提取器好——
    第四个第三方来的时候不用再加一段。
    """
    if isinstance(tree, Mapping):
        node = unwrap(tree)
        if isinstance(node, Mapping) and node.get("_type") in {"process", "step"}:
            address = unwrap(node.get("address"))
            if isinstance(address, str) and address.endswith(address_suffix):
                yield node
        for value in (node.values() if isinstance(node, Mapping) else ()):
            yield from process_nodes(value, address_suffix)
    elif isinstance(tree, (list, tuple)):
        for item in tree:
            yield from process_nodes(item, address_suffix)


def config_of(node: Mapping[str, Any]) -> dict[str, Any]:
    """取节点自带的 config。**三个第三方生成器又是三种形状**：直接给字典、
    包一层带默认值的壳、或者壳里再裹一个元组。第一个映射就是它。"""
    value = unwrap(node.get("config", {}))
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (list, tuple)):
        for item in value:
            item = unwrap(item)
            if isinstance(item, Mapping):
                return dict(item)
    return {}


def wiring_of(node: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """取一个 process 节点的读写接线，壳已剥。"""
    return dict(unwrap(node.get("inputs", {}))), dict(unwrap(node.get("outputs", {})))


def common_prefix(paths: Sequence[tuple[str, ...]]) -> tuple[str, ...]:
    """一组路径的最长公共前缀。"""
    if not paths:
        return ()
    prefix = paths[0]
    for path in paths[1:]:
        cut = 0
        while cut < min(len(prefix), len(path)) and prefix[cut] == path[cut]:
            cut += 1
        prefix = prefix[:cut]
    return prefix


def paths_in(wiring: Mapping[str, Any]) -> set[tuple[str, ...]]:
    """一张接线表里，**每个端口能被声明到的那条路径**。

    值可以是一条路径，也可以是 `{key: 路径}`（按 key 逐个接线）。后者会**塌到
    这些路径的最长公共前缀**上——理由不在任何手写声明里，在 `admit()` 的代码里：

    > **`admit()` 对每个端口只发一条 `StateDelta`，而一条 `StateDelta` 只有一个路径。**

    所以一个按 key 接线的端口，其写入**无法**声明到每个 key 各自的路径上。
    推导若给出更细的路径，产出的是一份 `admit()` 消费不了的声明——
    **推导必须尊重接入路径自身的粒度上限**，否则它推的是另一个机制的声明。

    第十八个里程碑判 H0 时，这一条正是它指向的两处修法之一（分类为 `finer`：
    「信息在，是手写当初被端口粒度限制了」——**更准确的说法是：被接法限制了**）。
    解除这个上限要让 `admit()` 按 key 逐条发 `StateDelta`，而按 key 接线目前
    **只有一个 provider**（`DynamicFBA`）。**少于三个 provider 不许定型**——
    第九、十六、十七个里程碑各栽过一次，这次不再栽。
    """
    found: set[tuple[str, ...]] = set()
    for value in wiring.values():
        value = unwrap(value)
        if isinstance(value, Mapping):
            found.add(common_prefix([tuple(p) for p in value.values()]))
        else:
            found.add(tuple(value))
    return found


def derive_claims(
    in_wiring: Mapping[str, Any], out_wiring: Mapping[str, Any]
) -> tuple[StateClaim, ...]:
    """输入侧路径 → `read`；输出侧路径 → `own`。**两侧都有则只记 `own`**——
    `own` 蕴含读，重复声明会让「声明了几条」这个数字失去意义。"""
    owned = paths_in(out_wiring)
    read_only = paths_in(in_wiring) - owned
    return tuple(
        sorted(
            [StateClaim(p, "own") for p in owned]
            + [StateClaim(p, "read") for p in read_only],
            key=lambda c: (c.path, c.permission),
        )
    )


def element_type(type_expr: Any) -> str:
    """`"map[count]"` → `"count"`；`"float"` → `"float"`。容器只剥一层。"""
    text = str(unwrap(type_expr))
    if "[" in text and text.endswith("]"):
        return text[text.index("[") + 1 : -1].strip()
    return text.strip()


def probe_operation(core: Any, type_expr: Any) -> str:
    """**行为探针**：问这个 store 类型「1.0 收到 0.5 会变成什么」。

    求和 → 写入是增量（`add`）；覆写 → 是绝对值（`set`）。
    分辨不出即硬失败——**不许猜一个对自己有利的默认值**。
    """
    from bigraph_schema.methods import apply  # noqa: PLC0415

    name = element_type(type_expr)
    registry = core.registry.registry if hasattr(core.registry, "registry") else core.registry
    schema_cls = registry.get(name)
    if schema_cls is None:
        raise SpecValidationError(f"探针取不到类型 {name!r}：它没有注册在 core 里")
    result, _ = apply(schema_cls(), PROBE_STATE, PROBE_UPDATE, [])
    if result == PROBE_STATE + PROBE_UPDATE:
        return "add"
    if result == PROBE_UPDATE:
        return "set"
    raise SpecValidationError(
        f"类型 {name!r} 的 apply 语义既不是求和也不是覆写（{PROBE_STATE} ⊕ "
        f"{PROBE_UPDATE} = {result}）——推不出算符，不猜"
    )


def derive_operations(core: Any, outputs: Mapping[str, Any]) -> dict[str, str]:
    """每个输出端口一个算符，来自第三方**在那个端口上声明的类型**。"""
    return {port: probe_operation(core, expr) for port, expr in outputs.items()}


ALLOWED_EFFECTS = frozenset({"StateDelta"})
"""这条接入路径上，第三方的输出只可能降级成 `StateDelta`——结构性事实，不是选择。

`admit()` 把引擎 update 的**每一个端口条目**翻成一条 `StateDelta`；
第三方没有别的出口（Event / StructuralRewrite / Transfer / Contribution 都进不来）。
"""


def derive_spec(
    core: Any,
    node: Mapping[str, Any],
    outputs_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """一个第三方 process 节点 → 推导出的权限声明三件套。"""
    in_wiring, out_wiring = wiring_of(node)
    return {
        "claims": derive_claims(in_wiring, out_wiring),
        "allowed_effects": ALLOWED_EFFECTS,
        "operations": derive_operations(core, outputs_schema),
        "in_wiring": in_wiring,
        "out_wiring": out_wiring,
    }


def probe_selftest(core: Any) -> dict[str, str]:
    """探针自检：覆写型必须判成 `set`，求和型必须判成 `add`。

    **判定单元 Y2 每次跑前验一遍。** 探针分辨不出，整套推导就没有判定力——
    这是本项目栽过两次的坑（「用一个检测不出任何东西的变异去判定通过」）的预防。

    住在适配器区内，因为它要 import vendor（`bigraph_schema` / `spatio_flux`），
    而 import lint 的规则 2 只允许这一层这么做。
    """
    from bigraph_schema.methods import apply  # noqa: PLC0415
    from spatio_flux.types.positive import PositiveFloat, SetFloat  # noqa: PLC0415

    registry = core.registry.registry if hasattr(core.registry, "registry") else core.registry
    out: dict[str, str] = {}
    for cls in (PositiveFloat, SetFloat):
        name = next((k for k, v in registry.items() if v is cls), None)
        if name is not None:
            out[cls.__name__] = probe_operation(core, name)
            continue
        result, _ = apply(cls(), PROBE_STATE, PROBE_UPDATE, [])
        out[cls.__name__] = (
            "add" if result == PROBE_STATE + PROBE_UPDATE
            else "set" if result == PROBE_UPDATE else "?"
        )
    return out


def allocate_probe_core(register_types_dotted: str) -> Any:
    """装一个挂好第三方类型词表的 core。**vendor import 留在适配器区**（import lint 规则 2）。"""
    from process_bigraph import allocate_core  # noqa: PLC0415

    from newlife.adapters.process_bigraph.foreign import third_party_types  # noqa: PLC0415

    core = allocate_core()
    third_party_types(register_types_dotted)(core)
    return core


def outputs_declared_by(cls: Any, config: Mapping[str, Any], core: Any) -> tuple[dict, str]:
    """取第三方在自己输出端口上声明的类型。

    先试**完整实例化**（最忠实）；第三方的 config 里带 schema 对象时它会炸
    （`MonodKinetics` 就是），退而只调它声明的 `outputs()`——**仍是问第三方，
    不是读它的源码**（预注册 `f948447` §3 F2）。用了哪条路径由判定产物如实记录。
    """
    try:
        return dict(cls(dict(config), core).outputs()), "instantiated"
    except Exception:  # noqa: BLE001 —— 退路本身是产物里要交代的事实
        return dict(cls.outputs(cls.__new__(cls))), "declared_only"
