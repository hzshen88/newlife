"""通用 harness：把「怎么跑一个世界」从各世界的 `world.py` 里收上来。

规格来自第七世界的判定（预注册 `c10dcb3`）：harness 要提供五块，本模块实现 World 4
用得到的三块——**引擎装配** / **阶段执行与编排** / **观测提取**。另两块
（数值复现、运行时契约强制）World 4 用不到，本模块不含，**用不到不等于它们不存在**。

**世界侧只留声明与机制代码。** 声明是纯数据：不含 lambda、不含可调用对象、
不含 `eval`/`exec`/`getattr` 构造——预注册 §3.2 冻结了这条，由 AST 检查。
机制函数由**点分路径字符串**指名（`"module:function"`）：字符串是数据，被指名的函数
是 `model`，本就该是代码（`proposal.md` §1.4 第三层）。

**为什么 `reuse_trace` 的字段名进配置**：`results/*/summary.json` 原样嵌入这份 trace，
字段名是该世界对外的声明契约。harness 算事实，配置给名字——把名字硬编进 harness
才是把一个世界的特殊性焊死在通用件里。
"""

from __future__ import annotations

import dataclasses
import importlib
from typing import Any, Callable, Mapping, Sequence

from newlife.core.runtime import RuntimeFactory, WorldRuntime


@dataclasses.dataclass(frozen=True, slots=True)
class StageSpec:
    """一个阶段：跑哪个机制、用哪个 step、静态参数与命名流各是什么。"""

    identity: str
    step: str                                   # "module:function"
    params: Mapping[str, Any] = dataclasses.field(default_factory=dict)
    streams: Mapping[str, str] = dataclasses.field(default_factory=dict)


OPERATORS = {
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}
"""终止条件的**封闭**算符集（预注册 `10e26c7` §2.1）。

**不得扩充。** 为了让某个世界通过而加算符，正是 inner-platform effect 的第一步：
系统越可配置，配置本身越像一门编程语言，最后需要程序员而不是用户来改。
组合只有合取——没有 `or`、没有算术、没有任意状态路径。
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Clause:
    """终止条件的一个子句：`{已声明的观测量, 算符, 常量或配置字段}`。纯数据。"""

    observable: str
    op: str
    value: Any


@dataclasses.dataclass(frozen=True, slots=True)
class LoopSpec:
    """tick 循环：每轮跑哪些阶段，什么时候停。

    `while_all` 的全部子句同时为真才继续——**只有合取**。
    `observables` 把子句里的名字绑到宿主对象的属性/方法名（字符串，不是可调用对象）。
    `per_iteration_params` 声明「每轮重算一次」的参数取自宿主的哪个方法——
    这是绑定点，不是取值语言：没有表达式，只有名字。
    """

    stages: tuple[str, ...]
    while_all: tuple[Clause, ...]
    observables: Mapping[str, str] = dataclasses.field(default_factory=dict)
    per_iteration_params: Mapping[str, Mapping[str, str]] = dataclasses.field(
        default_factory=dict
    )


@dataclasses.dataclass(frozen=True, slots=True)
class ObservationSpec:
    """从哪个阶段的第几条记录、取哪些 payload 字段。"""

    stage: str
    record: int
    fields: tuple[str, ...]
    list_fields: tuple[str, ...] = ()           # 需转成 list 的字段


@dataclasses.dataclass(frozen=True, slots=True)
class ReuseTraceSpec:
    """复用证据的形状。字段名属世界的声明契约，故在配置里。"""

    schema: str
    subject_stage: str
    declared_source: str                        # 点分模块路径
    field_names: Mapping[str, str]
    execution_input_paths: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class WorldSpec:
    """一个世界的全部声明。**纯数据。**"""

    protocol_version: str
    state_roots: Mapping[str, Any]
    specs_from: str                             # "module:function" → MechanismSpec 列表
    stages: tuple[StageSpec, ...]
    observation: ObservationSpec | None = None
    reuse_trace: ReuseTraceSpec | None = None
    loop: LoopSpec | None = None


def _resolve(dotted: str) -> Callable[..., Any]:
    """`"module:function"` → 函数对象。**取的是对象本身**，复用判据靠对象同一性。"""
    module_name, _, attr = dotted.partition(":")
    if not attr:
        raise ValueError(f"需要 'module:function' 形式，得到 {dotted!r}")
    return getattr(importlib.import_module(module_name), attr)


class GenericWorld:
    """按 `WorldSpec` 跑一个 replicate。世界侧不再需要写这些。"""

    def __init__(
        self,
        spec: WorldSpec,
        streams: Mapping[str, Any],
        runtime: Mapping[str, Any] | None = None,
        *,
        backend: RuntimeFactory,
    ) -> None:
        self.spec = spec
        self._streams = dict(streams)
        self._runtime = dict(runtime or {})
        self.kernel: WorldRuntime = backend(spec.state_roots)
        for mechanism in _resolve(spec.specs_from)():
            self.kernel.register_mechanism(mechanism)
        # 解析出来的 step **对象**，复用 provenance 与 R14 一样靠对象同一性
        # `host:` 前缀的 step 延迟到 run_loop 时绑到宿主对象；其余在此解析成对象，
        # 复用 provenance 靠的正是对象同一性。
        self._steps: dict[str, Callable[..., Any]] = {
            stage.identity: _resolve(stage.step)
            for stage in spec.stages
            if not stage.step.startswith("host:")
        }
        self._host_steps: dict[str, str] = {
            stage.identity: stage.step.split(":", 1)[1]
            for stage in spec.stages
            if stage.step.startswith("host:")
        }

    def _run_stage(self, stage: StageSpec, extra: Mapping[str, Any] | None = None,
                   host: Any = None) -> Any:
        if stage.identity in self._host_steps:
            step = getattr(host, self._host_steps[stage.identity])
        else:
            step = self._steps[stage.identity]
        kwargs = dict(stage.params)
        kwargs.update(extra or {})
        for name, stream in stage.streams.items():
            kwargs[name] = self._streams[stream]
        for name, value in self._runtime.items():
            if name in stage.params or name in stage.streams:
                kwargs[name] = value

        def bound(view: Any) -> Any:
            return step(view, **kwargs)

        result = self.kernel.guarded_read(stage.identity, bound)
        self.kernel.apply_batch(
            stage.identity, list(result.effects), list(result.records)
        )
        return result

    def _read_observable(self, host: Any, name: str) -> Any:
        """按声明的名字从宿主取观测量。属性取值，方法调用一次；**没有路径解析**。"""
        loop = self.spec.loop
        assert loop is not None
        attr = getattr(host, loop.observables[name])
        return attr() if callable(attr) else attr

    def _should_continue(self, host: Any, config: Any) -> bool:
        loop = self.spec.loop
        assert loop is not None
        for clause in loop.while_all:
            left = self._read_observable(host, clause.observable)
            right = clause.value
            if isinstance(right, str) and right.startswith("config."):
                right = getattr(config, right.split(".", 1)[1])
            if not OPERATORS[clause.op](left, right):
                return False
        return True

    def run_loop(self, host: Any, config: Any) -> int:
        """驱动 tick 循环。宿主提供观测量与每轮重算的参数，harness 管顺序与终止。"""
        loop = self.spec.loop
        if loop is None:
            raise ValueError("本世界未声明 loop")
        by_identity = {st.identity: st for st in self.spec.stages}
        iterations = 0
        while self._should_continue(host, config):
            for identity in loop.stages:
                stage = by_identity[identity]
                extra = {
                    name: (lambda v: v() if callable(v) else v)(getattr(host, meth))
                    for name, meth in loop.per_iteration_params.get(identity, {}).items()
                }
                self._run_stage(stage, extra, host)
            iterations += 1
        return iterations

    def run(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for stage in self.spec.stages:
            results[stage.identity] = self._run_stage(stage)
        obs = self.spec.observation
        payload = results[obs.stage].records[obs.record]["payload"]
        out: dict[str, Any] = {}
        for field in obs.fields:
            value = payload[field]
            out[field] = list(value) if field in obs.list_fields else value
        return out

    def reuse_trace(self) -> dict[str, Any]:
        """复用证据。harness 算事实，`ReuseTraceSpec` 给字段名。"""
        rt = self.spec.reuse_trace
        if rt is None:
            raise ValueError("本世界未声明 reuse_trace")
        step = self._steps[rt.subject_stage]
        source = importlib.import_module(rt.declared_source)
        declared = getattr(source, step.__name__, None)
        ours = next(s for s in _resolve(self.spec.specs_from)()
                    if s.identity == rt.subject_stage)
        theirs = next(s for s in source.build_mechanism_specs()
                      if s.identity == rt.subject_stage)
        facts = {
            "identity": rt.subject_stage,
            "is_declared_object": step is declared,
            "module": step.__module__,
            "spec_unedited": ours == theirs,
        }
        out: dict[str, Any] = {"schema": rt.schema}
        for key, name in rt.field_names.items():
            out[name] = facts[key]
        out["execution_input_paths"] = list(rt.execution_input_paths)
        return out


def config_is_pure_data(module_path: str) -> tuple[bool, list[str]]:
    """预注册 §3.2：配置里不得出现 lambda / 函数定义 / eval 类构造。

    由 AST 检查，不靠自觉。**若终止条件或观测提取只能用 lambda 表达，
    就是胶水没被吃掉。**
    """
    import ast, pathlib  # noqa: PLC0415

    tree = ast.parse(pathlib.Path(module_path).read_text())
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Lambda):
            bad.append(f"L{node.lineno}: lambda")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bad.append(f"L{node.lineno}: def {node.name}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in {"eval", "exec", "compile", "getattr"}:
            bad.append(f"L{node.lineno}: {node.func.id}()")
    return (not bad), bad
