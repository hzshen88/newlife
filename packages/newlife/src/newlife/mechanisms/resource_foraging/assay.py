"""The frozen causal assay (EXPERIMENT.md §7 / Assays.jl) driven through the
newlife contract layer, with recorded-draw injection (L2) or dev streams.

Assay worlds are fresh worlds whose single organism carries a sampled
controller; the two branches (true_cue / cue_ablation) share the same
episode seed — the exogenous events match, the sensing sub-streams differ.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from newlife.mechanisms.resource_foraging.model import (
    ForagingConfig,
    validate_config,
)
from newlife.mechanisms.resource_foraging.world import ForagingWorld


def assay_config(config: ForagingConfig, condition: str) -> ForagingConfig:
    """Assays.jl assay_config — one organism, no reproduction, capped age."""
    return validate_config(
        ForagingConfig(
            protocol_version=config.protocol_version,
            name=f"{config.name}-assay",
            condition=condition,
            width=config.width,
            height=config.height,
            ticks=config.assay_ticks,
            initial_population=1,
            initial_cell_resource=config.initial_cell_resource,
            cell_capacity=config.cell_capacity,
            resource_probability=config.resource_probability,
            resource_heterogeneity=config.resource_heterogeneity,
            resource_quantum=config.resource_quantum,
            initial_energy=config.initial_energy,
            harvest_limit=config.harvest_limit,
            conversion_efficiency=config.conversion_efficiency,
            maintenance_cost=config.maintenance_cost,
            movement_cost=config.movement_cost,
            reproduction_threshold=1.0e300,
            offspring_energy=config.offspring_energy,
            reproduction_cost=config.reproduction_cost,
            reproduction_attempt_cost=0.0,
            max_age=max(config.max_age, config.assay_ticks + 1),
            death_resource_fraction=config.death_resource_fraction,
            mutation_rate=0.0,
            observer_interval=config.observer_interval,
            assay_sample_size=config.assay_sample_size,
            assay_episodes=config.assay_episodes,
            assay_ticks=config.assay_ticks,
        )
    )


@dataclass
class AssayEpisodeResult:
    harvested_resource: float
    survival_ticks: int
    movement_attempts: int
    aligned_actions: int
    decisions: int


@dataclass
class ForagingAssayResult:
    sampled_genomes: int
    paired_episodes: int
    mean_true_harvest: float
    mean_ablated_harvest: float
    harvest_contribution: float
    true_alignment_rate: float
    ablated_alignment_rate: float


def _episode(
    config: ForagingConfig,
    controller: list[int],
    episode_index: int,
    episode_seed: int,
    condition: str,
    *,
    recorded_banks: dict[tuple[int, str], Any] | None = None,
) -> AssayEpisodeResult:
    assay_conf = assay_config(config, condition)
    bank = None
    if recorded_banks is not None:
        bank = recorded_banks[(episode_index, condition)]
    world = ForagingWorld(assay_conf, episode_seed, bank=bank)
    # swap the single organism's controller to the sampled genome
    for cell, record in world.kernel.state["organisms"].items():
        if record is not None:
            record["controller"] = list(controller)
    result = world.run()
    final = result.final_snapshot
    return AssayEpisodeResult(
        harvested_resource=final["harvested_resource"],
        survival_ticks=result.tick,
        movement_attempts=final["movement_attempts"],
        aligned_actions=final["aligned_actions"],
        decisions=final["decisions"],
    )


def run_assay(
    world: ForagingWorld,
    *,
    recorded_banks: dict[tuple[int, str], Any] | None = None,
) -> ForagingAssayResult:
    """Assays.jl run_assay over the world's final population."""
    config = world.config
    state = world.kernel.state
    organism_records = sorted(
        (record for record in state["organisms"].values() if record is not None),
        key=lambda record: record["id"],
    )
    if not organism_records:
        return ForagingAssayResult(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assay_stream = world.bank.rng_stream("assay")
    # Assays.jl shuffles the sorted id list with the assay stream; the
    # recorder logs the resulting permutation, so both bindings consume the
    # stream through the same permutation interface.
    ids = [record["id"] for record in organism_records]
    shuffled = assay_stream.permutation(ids)
    sample_count = min(config.assay_sample_size, len(shuffled))
    sampled_ids = shuffled[:sample_count]

    records_by_id = {record["id"]: record for record in organism_records}
    true_harvest = 0.0
    ablated_harvest = 0.0
    true_aligned = 0
    ablated_aligned = 0
    true_decisions = 0
    ablated_decisions = 0
    paired_episodes = sample_count * config.assay_episodes
    episode_index = 0
    for organism_id in sampled_ids:
        controller = list(records_by_id[organism_id]["controller"])
        for _ in range(config.assay_episodes):
            episode_index += 1
            episode_seed = assay_stream.draw_u64()
            true_result = _episode(
                config, controller, episode_index, episode_seed, "informative",
                recorded_banks=recorded_banks,
            )
            ablated_result = _episode(
                config, controller, episode_index, episode_seed, "cue_neutral",
                recorded_banks=recorded_banks,
            )
            true_harvest += true_result.harvested_resource
            ablated_harvest += ablated_result.harvested_resource
            true_aligned += true_result.aligned_actions
            ablated_aligned += ablated_result.aligned_actions
            true_decisions += true_result.decisions
            ablated_decisions += ablated_result.decisions
    mean_true = true_harvest / paired_episodes
    mean_ablated = ablated_harvest / paired_episodes
    return ForagingAssayResult(
        sampled_genomes=sample_count,
        paired_episodes=paired_episodes,
        mean_true_harvest=mean_true,
        mean_ablated_harvest=mean_ablated,
        harvest_contribution=mean_true - mean_ablated,
        true_alignment_rate=0.0 if true_decisions == 0 else true_aligned / true_decisions,
        ablated_alignment_rate=0.0 if ablated_decisions == 0 else ablated_aligned / ablated_decisions,
    )


