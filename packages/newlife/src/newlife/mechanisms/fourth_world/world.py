"""第四世界的注册表组装：自己的 Moran builder + World 2 的 observer（原样复用）。

冻结判据见 `exloop` 预注册（freeze commit `24bb02e`）。本模块承担其中两条：

- **R1 复用范围**：只注册 World 2 的 `second-world-observer`，**不**注册它的
  `second-world-coalescent`——两者都会 `own` `TREE_PATH`，registry 会抛
  `StructuralOwnershipConflictError`（plan §1.1 的 0.2，由执行确认）。
- **R14 provenance**：`reuse-trace.json` 由本模块产出、由 verdict runner *读取*，
  runner 永不撰写它。判 goal C1 的是**对象同一性**——实际被调用的 step 函数
  `is second_world.mechanisms.observer_step`。只比 `__module__` 不够：手工改写
  `__module__` 的复制品能通过，而同一性挡得住（实测三种假复用，见 plan R1）。

`TREE_PATH` 沿用 World 2 的模块常量（R2）：第四世界的状态里因此带一个名为
`second_world` 的键。这是复用的真实代价，收尾时如实记录，不描述成干净的组合。
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.core.contracts import MechanismSpec, StateClaim, StructuralRewrite
from newlife.mechanisms.fourth_world.genealogy import DrawStream, build_moran_genealogy
from newlife.mechanisms.second_world import mechanisms as w2

PROTOCOL_VERSION = "fourth-world-v1"
BUILDER_IDENTITY = "fourth-world-moran-genealogy"
OBSERVER_IDENTITY = "second-world-observer"


def build_mechanism_specs() -> list[MechanismSpec]:
    """两条注册表条目：新建的 builder，以及 World 2 的 observer spec **原样**。

    observer 的 spec 直接取自 World 2 的构造函数，不复制字段、不改写——任何编辑
    都会触发预注册的 IC-2，并使本次运行不能算作 as-declared reuse。
    """
    observer = next(
        s for s in w2.build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
    )
    builder = MechanismSpec(
        identity=BUILDER_IDENTITY,
        version=PROTOCOL_VERSION,
        plane="biological",
        biological_role="neutral Moran genealogy construction (prereg R5, R8)",
        ports=("state",),
        claims=(StateClaim(w2.TREE_PATH, "own"),),
        schedule={"stage": "coalesce"},
        rng_streams=("moran-draws",),
        allowed_effects=frozenset({"StructuralRewrite"}),
        invariants=(f"{PROTOCOL_VERSION}-moran-genealogy",),
    )
    return [builder, observer]


def genealogy_step(
    view: Mapping[tuple[str, ...], Any],
    *,
    n_sample: int,
    n_pop: int,
    draws: DrawStream,
) -> w2.MechanismStep:
    """把整棵 Moran 谱系作为一次 `StructuralRewrite` 提交。

    与 World 2 的 `coalescent_step` 同构：`view` 不被读取，树完全由 draw 流决定。
    """
    time, abv, _steps = build_moran_genealogy(n_sample, n_pop, draws)
    tree = {"time": tuple(time), "abv": tuple(abv)}
    return w2.MechanismStep((StructuralRewrite(w2.TREE_PATH, None, tree),), ())


class MoranGenealogyWorld:
    """一个 replicate：建树（自己的机制）+ 观测（World 2 的机制）。"""

    def __init__(
        self,
        n_sample: int,
        n_pop: int,
        theta: float,
        builder_draws: DrawStream,
        observer_draws: Any,
        *,
        replicate_index: int = 0,
    ) -> None:
        self.n_sample = n_sample
        self.n_pop = n_pop
        self.theta = theta
        self.builder_draws = builder_draws
        self.observer_draws = observer_draws
        self.replicate_index = replicate_index
        self.kernel = ReferenceKernel({"second_world": {"tree": None}})
        for spec in build_mechanism_specs():
            self.kernel.register_mechanism(spec)
        # R14：实际被调用的 observer step 函数，供 provenance 记录。
        # 保存的是**对象本身**，不是它的名字或模块路径。
        self.observer_fn: Callable[..., Any] = w2.observer_step

    def _run_stage(self, identity: str, step) -> w2.MechanismStep:
        result = self.kernel.guarded_read_fast(identity, step)
        self.kernel.apply_batch_fast(
            identity, list(result.effects), list(result.records)
        )
        return result

    def run(self) -> dict[str, Any]:
        self._run_stage(
            BUILDER_IDENTITY,
            lambda view: genealogy_step(
                view,
                n_sample=self.n_sample,
                n_pop=self.n_pop,
                draws=self.builder_draws,
            ),
        )
        observed = self._run_stage(
            OBSERVER_IDENTITY,
            lambda view: self.observer_fn(
                view,
                nsam=self.n_sample,
                theta=self.theta,
                draws=self.observer_draws,
                replicate_index=self.replicate_index,
            ),
        )
        payload = observed.records[0]["payload"]
        return {
            "segsites": payload["segsites"],
            "genotype_rows": list(payload["genotype_rows"]),
        }

    def reuse_trace(self) -> dict[str, Any]:
        """R14(b) 的 `reuse-trace.json` 内容：判 goal C1/C2 的证据。

        由本模块产出，verdict runner 只读不写——判定与事实分层的落点。
        """
        return {
            "schema": "newlife.fourth-world.reuse-trace.v1",
            "observer_identity": OBSERVER_IDENTITY,
            "observer_is_world2_object": self.observer_fn is w2.observer_step,
            "observer_module": self.observer_fn.__module__,
            "observer_spec_unedited": next(
                s for s in build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
            )
            == next(
                s for s in w2.build_mechanism_specs() if s.identity == OBSERVER_IDENTITY
            ),
            # C2：执行期输入路径。本世界不从任何 results/ 产物取输入。
            "execution_input_paths": [],
        }
