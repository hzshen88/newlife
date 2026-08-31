"""World-1 calibration harness for `core.compare` (v0.3, R5 units 1-4).

Frozen by exloop's preregistration
`docs/science-superpowers/preregistrations/2026-08-31-newlife-compare-attribution-declarability-v2.md`.
This module builds the four World-1-derived calibration pairs, wires them
to `core.compare`'s generic diff/locate/attribute functions via an injected
runner callback, and carries the known-true oracle each pair is checked
against. `core/compare.py` never imports this module or `ForagingWorld`
directly (R6) — the dependency runs the other way, matching an adapter
consuming a domain-free core.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from newlife.mechanisms.resource_foraging.assay import assay_config
from newlife.mechanisms.resource_foraging.mechanisms import build_mechanism_specs
from newlife.mechanisms.resource_foraging.model import ForagingConfig, load_config
from newlife.mechanisms.resource_foraging.world import ForagingWorld

_ASSAY_CONTROLLER = [1, 2, 3, 4, 5]  # never all-STAY (R5 unit 2)


@dataclasses.dataclass(frozen=True)
class CalibrationUnit:
    """One calibration pair plus the known-true answer it is checked against."""

    name: str
    registry_a: tuple[Any, ...]
    registry_b: tuple[Any, ...]
    config_a: ForagingConfig
    config_b: ForagingConfig
    history_a: Sequence[Mapping[str, Any]]
    history_b: Sequence[Mapping[str, Any]]
    runner: Callable[[ForagingConfig], Sequence[Mapping[str, Any]]]
    expected_registry_equal: bool
    expected_differing_fields: tuple[str, ...]
    expected_locus_tick: int | None  # None means "no divergence expected"
    expected_per_field: Mapping[str, str]
    expected_aggregate: str


def _train_runner(seed: int) -> Callable[[ForagingConfig], Sequence[Mapping[str, Any]]]:
    return lambda config: ForagingWorld(config, seed).run().history


def _assay_episode_runner(
    seed: int, controller: list[int]
) -> Callable[[ForagingConfig], Sequence[Mapping[str, Any]]]:
    def runner(config: ForagingConfig) -> Sequence[Mapping[str, Any]]:
        world = ForagingWorld(config, seed)
        for record in world.kernel.state["organisms"].values():
            if record is not None:
                record["controller"] = list(controller)
        return world.run().history

    return runner


def build_unit1(
    informative_path: Path | str, cue_neutral_path: Path | str
) -> CalibrationUnit:
    """Informative vs. cue-neutral, short window (R5 unit 1)."""
    config_a = dataclasses.replace(
        load_config(informative_path), ticks=50, observer_interval=1
    )
    config_b = dataclasses.replace(
        load_config(cue_neutral_path), ticks=50, observer_interval=1
    )
    runner = _train_runner(seed=101)
    history_a = runner(config_a)
    history_b = runner(config_b)
    return CalibrationUnit(
        name="unit1-informative-vs-cue-neutral",
        registry_a=tuple(build_mechanism_specs(config_a)),
        registry_b=tuple(build_mechanism_specs(config_b)),
        config_a=config_a,
        config_b=config_b,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=("condition", "name"),
        expected_locus_tick=1,
        expected_per_field={"condition": "causal", "name": "incidental"},
        expected_aggregate="normal",
    )


def build_unit2(informative_path: Path | str, seed: int) -> CalibrationUnit:
    """Assay true-cue vs. cue-ablation, one seed of the required pair (R5 unit 2)."""
    base = load_config(informative_path)
    config_a = dataclasses.replace(
        assay_config(base, "informative"), observer_interval=1
    )
    config_b = dataclasses.replace(
        assay_config(base, "cue_neutral"), observer_interval=1
    )
    runner = _assay_episode_runner(seed, _ASSAY_CONTROLLER)
    history_a = runner(config_a)
    history_b = runner(config_b)
    return CalibrationUnit(
        name=f"unit2-assay-seed{seed}",
        registry_a=tuple(build_mechanism_specs(config_a)),
        registry_b=tuple(build_mechanism_specs(config_b)),
        config_a=config_a,
        config_b=config_b,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=("condition",),
        expected_locus_tick=1,
        expected_per_field={"condition": "causal"},
        expected_aggregate="normal",
    )


def build_unit3(informative_path: Path | str) -> CalibrationUnit:
    """Irrelevant-difference control: only `name` changed (R5 unit 3)."""
    config_a = dataclasses.replace(
        load_config(informative_path), ticks=50, observer_interval=1
    )
    config_b = dataclasses.replace(config_a, name="anything-else")
    runner = _train_runner(seed=101)
    history_a = runner(config_a)
    history_b = runner(config_b)
    return CalibrationUnit(
        name="unit3-irrelevant-difference-control",
        registry_a=tuple(build_mechanism_specs(config_a)),
        registry_b=tuple(build_mechanism_specs(config_b)),
        config_a=config_a,
        config_b=config_b,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=("name",),
        expected_locus_tick=None,
        expected_per_field={"name": "incidental"},
        expected_aggregate="normal",
    )


def build_unit4(informative_path: Path | str) -> CalibrationUnit:
    """Zero-delta replay control: two genuinely independent runs (R5 unit 4,
    fixed in red-team round 2 — never a self-comparison)."""
    config = dataclasses.replace(
        load_config(informative_path), ticks=50, observer_interval=1
    )
    runner = _train_runner(seed=101)
    history_a = runner(config)
    history_b = runner(config)  # a second, independent ForagingWorld invocation
    return CalibrationUnit(
        name="unit4-zero-delta-replay-control",
        registry_a=tuple(build_mechanism_specs(config)),
        registry_b=tuple(build_mechanism_specs(config)),
        config_a=config,
        config_b=config,
        history_a=history_a,
        history_b=history_b,
        runner=runner,
        expected_registry_equal=True,
        expected_differing_fields=(),
        expected_locus_tick=None,
        expected_per_field={},
        expected_aggregate="normal",
    )
