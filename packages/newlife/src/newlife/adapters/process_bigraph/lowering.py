"""Process-Bigraph adapter lowering: LoweredOp → engine update (R5 class ii).

The IR → runtime-update translation is adapter knowledge (proposal §5.2):
what a `set` means depends on the target store's registered type semantics.
This module is the complete, unit-testable dispatch — mechanism authors never
write engine updates (R4); they declare which (port, store type) each Effect
kind targets via the class-level ``lowering_table``, and the handlers below
do the rest as pure functions of (LoweredOp, observed state view, interval).

Handlers are keyed by store type; each returns the engine-update fragment for
its port. ``interval`` is ambient runtime context (the value the engine
legally passes into ``update``) and is used only where the frozen store type
embeds tick time (contribution envelopes).
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from newlife.core.errors import SpecValidationError
from newlife.core.lowering_contract import (
    OP_ADD,
    OP_CONTRIBUTION_RESOLVE,
    OP_EVENT,
    OP_SET,
    OP_STRUCTURAL,
    LoweredOp,
)

StoreHandler = Callable[[LoweredOp, str, dict[str, Any], float], dict[str, Any]]


def _expect(op: LoweredOp, wanted: str, store: str) -> None:
    """store handler 假定了某个算符，就必须校验它。

    第十五个里程碑（`results/fifteenth/`）发现的缺口：`sum-float-add` 假定进来的是
    ADD，却从不检查——于是把声明表里的 `operation` 填成 `set` **产出完全相同的轨迹，
    没有任何东西报警**。而接第三方 process 时，那张表正是由我们**代写**的，
    是最容易填错、也最没人复核的一处。

    `_budget_proposal_projection` 与 `_resolved_position_envelope` 本来就这么做，
    只是 StateDelta 那几个 handler 漏了。这里补齐。
    """
    if op.op != wanted:
        raise SpecValidationError(
            f"store 类型 {store!r} 假定算符 {wanted!r}，实际收到 {op.op!r}——"
            "声明表与 store 语义对不上，不许静默按假定处理"
        )


def _integer_count(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    _expect(op, OP_ADD, 'integer-count')
    # add on an integer store: the engine reconciles per-timestep updates by
    # summation, so the update carries the delta itself.
    return {port: op.payload}


def _sum_float_add(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    _expect(op, OP_ADD, 'sum-float-add')
    # add on a sum-reconciling float store: the engine adds the update to the
    # current value, so a delta passes through unchanged.
    # `_integer_count` 的语义相同但名字说的是整数 store；接第三方 process 时
    # 声明表**就是**这次里程碑要检验的东西，名字不许将就。
    return {port: op.payload}


def _sum_map_add(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # add on a per-key sum-reconciling map store: the delta mapping passes through.
    # 第十六个里程碑加：第三方的 substrates 端口一次写多个底物的增量。
    _expect(op, OP_ADD, "sum-map-add")
    if not isinstance(op.payload, Mapping):
        raise SpecValidationError(
            f"store 类型 'sum-map-add' 要求映射负载，收到 {type(op.payload).__name__}"
        )
    return {port: dict(op.payload)}


def _map_direct(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    _expect(op, OP_SET, 'map-direct')
    # set on a map store whose fields are committed wholesale (budget store).
    return {port: op.payload}


def _sum_float_set(op: LoweredOp, port: str, view, _interval) -> dict[str, Any]:
    _expect(op, OP_SET, 'sum-float-set')
    # set on a sum-reconciling float store: the engine adds the update to the
    # current value, so the set is translated to after − observed_before.
    # State-view arithmetic — class (ii) adapter translation, sanctioned by
    # the frozen prediction for MutationRateIntervention, never an H0 shape.
    return {port: op.payload - view[port]}


def _list_direct(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    _expect(op, OP_SET, 'list-direct')
    # set on a list store: the update is the whole new list (overwrite).
    return {port: op.payload}


def _string_leaf_structural(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # structural rewrite of a leaf string store collapses to its after value.
    return {port: op.payload["after"]}


def _map_divide_structural(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # structural rewrite of a map store with a single-key before-state is the
    # engine's division sentinel: the before key is the mother, the after
    # mapping is the daughters.
    before = op.payload["before"]
    if not isinstance(before, dict) or len(before) != 1:
        raise SpecValidationError(
            "map-divide structural rewrite requires a single-mother before state"
        )
    mother = next(iter(before))
    return {port: {"_divide": {"mother": mother, "daughters": op.payload["after"]}}}


def _budget_proposal_projection(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # Contribution envelope projected onto the proposal store's registered
    # type {A, B, available}: weights become the per-organism allocation and
    # available_instructions the budget size. Pure restructuring of the
    # effect payload — class (ii) store-type knowledge.
    if op.op != OP_CONTRIBUTION_RESOLVE:
        raise SpecValidationError("budget-proposal projection consumes Contribution ops")
    value = op.payload["value"]
    weights = value["weights"]
    return {
        port: {
            "A": weights["A"],
            "B": weights["B"],
            "available": value["available_instructions"],
        }
    }


def _resolved_position_envelope(op: LoweredOp, port: str, _view, interval) -> dict[str, Any]:
    # Contribution envelope for the registered biosim_resolved_position_v1
    # store: named provenance rides with the delta (R3; the tick time comes
    # from the engine-passed interval, not from mechanism state).
    if op.op != OP_CONTRIBUTION_RESOLVE:
        raise SpecValidationError("resolved-position envelope consumes Contribution ops")
    return {
        port: {
            "source": op.payload["source_id"],
            "delta": op.payload["value"],
            "resolver_id": op.payload["resolver_id"],
            "time": str(interval),
        }
    }


def _mapping_direct_structural(op: LoweredOp, port: str, _view, _interval) -> dict[str, Any]:
    # 结构重写落在一个整体覆写的映射 store 上：after 就是新值。
    # 与 `string-leaf-structural` 同一语义，区别只在 store 的注册类型不是叶子字符串。
    # **这是接线，不是改语义**——预注册 1b9257a §3 F1 允许的唯一一类改动。
    return {port: op.payload["after"]}


def _noop(_op: LoweredOp, _port: str, _view, _interval) -> dict[str, Any]:
    # event ops carry no state semantics: the effect is validated and traced,
    # the update contributes nothing.
    return {}


STORE_HANDLERS: dict[str, StoreHandler] = {
    "integer-count": _integer_count,
    "sum-float-add": _sum_float_add,
    "map-direct": _map_direct,
    "sum-map-add": _sum_map_add,
    "list-direct": _list_direct,
    "sum-float-set": _sum_float_set,
    "string-leaf-structural": _string_leaf_structural,
    "mapping-direct-structural": _mapping_direct_structural,
    "map-divide-structural": _map_divide_structural,
    "budget-proposal-projection": _budget_proposal_projection,
    "resolved-position-envelope": _resolved_position_envelope,
    "noop": _noop,
}


def lower_update(
    mechanism_id: str,
    lowering_table: dict[str, tuple[str, str]],
    effects: tuple,
    state_view: dict[str, Any],
    interval: float,
) -> dict[str, Any]:
    """Derive the engine update from validated Effects alone (pure function
    of Effect payloads, registered store types, mechanism identity, observed
    state view — the R5 basis). One Effect → one LoweredOp → one handler."""
    from newlife.core.lowering_contract import lower_effect

    update: dict[str, Any] = {}
    for effect in effects:
        op = lower_effect(effect, provenance=mechanism_id)
        # 先按 (类别, 路径) 找，再退回只按类别。
        # **第十六个里程碑撞出来的**：只按类别做键时，一个机制每类 Effect 只能写
        # 一个端口——第三方的 MonodKinetics 写两个（biomass 与 substrates），
        # 两条 StateDelta 全落到同一个端口上，`mass` 因此收到一个 dict。
        # 单端口的 Grow 看不出这个限制。**一个 provider 时看着对，两个时就塌。**
        binding = lowering_table.get((effect.kind, op.path)) or lowering_table.get(effect.kind)
        if binding is None:
            raise SpecValidationError(
                f"{mechanism_id} has no lowering binding for Effect {effect.kind} "
                f"at {op.path!r}"
            )
        port, store_type = binding
        handler = STORE_HANDLERS.get(store_type)
        if handler is None:
            raise SpecValidationError(f"unknown store type: {store_type!r}")
        update.update(handler(op, port, state_view, interval))
    return update
