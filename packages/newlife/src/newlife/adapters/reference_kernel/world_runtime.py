"""把 `ReferenceKernel` 接到 B 接缝上。**十几行，故意的。**

RK 有两条路径：`guarded_read` / `apply_batch` 是深拷贝 + 归一的参考路径，
`*_fast` 是给大世界用的惰性视图路径。这个 `fast` 之分是 **RK 的内部事情**，
不该出现在接缝的名字上（见 `core/runtime.py` 的说明）。

所以接缝方法名取干净的那组，实现绑到 `_fast` 那组——**绑 `_fast` 不是取巧，
是因为 harness 改动前走的就是它**。走别的路径，U0（安全绳）就不再是干净的对照。
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.core.contracts import Effect, MechanismSpec


class ReferenceKernelRuntime:
    """`WorldRuntime` 的 reference 实现。"""

    def __init__(self, state_roots: Mapping[str, Any]) -> None:
        self.kernel = ReferenceKernel(dict(state_roots))

    def register_mechanism(self, spec: MechanismSpec) -> None:
        self.kernel.register_mechanism(spec)

    def guarded_read(
        self, source_id: str, callback: Callable[[Mapping[tuple[str, ...], Any]], Any]
    ) -> Any:
        return self.kernel.guarded_read_fast(source_id, callback)

    def apply_batch(
        self,
        source_id: str,
        effects: Iterable[Effect],
        trace_records: Iterable[Mapping[str, Any]] = (),
    ) -> None:
        self.kernel.apply_batch_fast(source_id, list(effects), list(trace_records))
