"""B 接缝的 Definition：`GenericWorld` 对执行后端的**全部**要求。

这四个操作不是设计出来的，是**读出来的**——`core/harness.py` 在改动前只碰
`ReferenceKernel` 的四个方法（`__init__` / `register_mechanism` /
`guarded_read_fast` / `apply_batch_fast`），别的一概没碰。接缝的宽度由此确定，
不由想象确定。

**为什么现在才定型。** 接缝的规矩是「少于三个 provider 不许定型」（第九世界的教训）。
这里只有两个 provider，所以本模块**不是最终形态**：它是为了让第二个 provider 从
零使用变成活的而立的**最小可判定契约**。第三个 provider 出现前，任何加宽都要先问
「是哪个 provider 逼出来的」。

**命名去掉了 `_fast` 后缀。** RK 侧那两个方法名里的 `fast` 是相对它自己的
`guarded_read` / `apply_batch` 参考路径说的，是 RK 的内部区分，不该出现在接缝上。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Protocol, runtime_checkable

from newlife.core.contracts import Effect, MechanismSpec


@runtime_checkable
class StageResult(Protocol):
    """一个阶段跑完之后，运行时交回来的东西。"""

    effects: Iterable[Effect]
    records: Iterable[Mapping[str, Any]]


@runtime_checkable
class WorldRuntime(Protocol):
    """执行后端。构造签名是 `Runtime(state_roots: Mapping[str, Any])`。

    **构造不在 Protocol 里**——Protocol 不约束 `__init__`。harness 收的是
    `Callable[[Mapping[str, Any]], WorldRuntime]` 这个工厂类型，见 `RuntimeFactory`。
    """

    def register_mechanism(self, spec: MechanismSpec) -> None:
        """把一条机制声明登记进本运行时的注册表。"""
        ...

    def guarded_read(
        self, source_id: str, callback: Callable[[Mapping[tuple[str, ...], Any]], Any]
    ) -> Any:
        """以 `source_id` 声明的读权限构造只读视图，调 callback，返回其结果。

        视图被 callback 改写时必须抛错——这是契约强制，不是可选优化。
        """
        ...

    def apply_batch(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        """原子提交一批 Effect 与 trace 记录。任一条越权则整批不生效。"""
        ...


RuntimeFactory = Callable[[Mapping[str, Any]], WorldRuntime]
"""`state_roots -> WorldRuntime`。harness 只认这个类型，不认具体类。"""
