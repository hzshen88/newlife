"""Generic world assembly, stage orchestration, and observation extraction.

World declarations remain pure data. Mechanism functions are named by
``module:function`` strings, while the harness resolves and executes them.
World-specific artifact field names stay in the declaration.
"""

from __future__ import annotations

import dataclasses
import importlib
from typing import Any, Callable, Mapping, Sequence

from newlife.core.runtime import RuntimeFactory, WorldRuntime


@dataclasses.dataclass(frozen=True, slots=True)
class StageSpec:
    """Declare a stage's mechanism, step, static parameters, and named streams."""

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
    """Pure-data loop condition over an observable, operator, and value."""

    observable: str
    op: str
    value: Any


@dataclasses.dataclass(frozen=True, slots=True)
class LoopSpec:
    """Declare which stages run per tick and the conjunctive stop condition.

    ``observables`` binds condition names to host attributes or methods.
    ``per_iteration_params`` binds stage parameters to host values recomputed
    once per iteration.
    """

    stages: tuple[str, ...]
    while_all: tuple[Clause, ...]
    observables: Mapping[str, str] = dataclasses.field(default_factory=dict)
    per_iteration_params: Mapping[str, Mapping[str, str]] = dataclasses.field(
        default_factory=dict
    )


@dataclasses.dataclass(frozen=True, slots=True)
class ObservationSpec:
    """Declare the stage record and payload fields returned as observations."""

    stage: str
    record: int
    fields: tuple[str, ...]
    list_fields: tuple[str, ...] = ()           # 需转成 list 的字段


@dataclasses.dataclass(frozen=True, slots=True)
class ReuseTraceSpec:
    """Declare the shape and field names of mechanism-reuse evidence."""

    schema: str
    subject_stage: str
    declared_source: str                        # 点分模块路径
    field_names: Mapping[str, str]
    execution_input_paths: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class WorldSpec:
    """A world's complete pure-data declaration."""

    protocol_version: str
    state_roots: Mapping[str, Any]
    specs_from: str                             # "module:function" → MechanismSpec 列表
    stages: tuple[StageSpec, ...]
    observation: ObservationSpec | None = None
    reuse_trace: ReuseTraceSpec | None = None
    loop: LoopSpec | None = None


def _resolve(dotted: str) -> Callable[..., Any]:
    """Resolve a ``module:function`` string to the function object itself."""
    module_name, _, attr = dotted.partition(":")
    if not attr:
        raise ValueError(f"expected 'module:function', got {dotted!r}")
    return getattr(importlib.import_module(module_name), attr)


class GenericWorld:
    """Run one replicate from a ``WorldSpec`` declaration."""

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
        """Read a declared host attribute, calling it once if it is callable."""
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
        """Drive the tick loop while the host supplies observables and parameters."""
        loop = self.spec.loop
        if loop is None:
            raise ValueError("this world does not declare a loop")
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
        """Compute reuse facts and render their declared field names."""
        rt = self.spec.reuse_trace
        if rt is None:
            raise ValueError("this world does not declare reuse_trace")
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
    """Check that a declaration module contains no executable configuration constructs."""
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
