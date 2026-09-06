"""Resource Foraging world model (World 1, Parworlds Experiment 001).

Line-by-line port of the frozen `resource-foraging-v1` protocol's model layer
(`Parworlds/src/worlds/ResourceForaging/Model.jl`): the constitution's
vocabularies, configuration schema and validation, and the state layout used
by the newlife mechanism registry. Protocol semantics are copied verbatim —
any deviation is a criterion issue, not a modeling choice (see
docs/zh/worlds/001-resource-foraging.md).
"""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CUE_COUNT = 5
# Cues and actions share the frozen five-value alphabet; Julia enums are
# UInt8 with HERE/Stay = 1 … WEST/MoveWest = 5.
CUE_HERE = 1
CUE_NORTH = 2
CUE_EAST = 3
CUE_SOUTH = 4
CUE_WEST = 5
ACTION_STAY = 1

RNG_STREAM_NAMES = (
    "initialization",
    "environment",
    "sensing",
    "mutation",
    "selection",
    "assay",
)

CONDITIONS = ("informative", "cue_neutral")


@dataclass(frozen=True)
class ForagingConfig:
    protocol_version: str
    name: str
    condition: str
    width: int
    height: int
    ticks: int
    initial_population: int
    initial_cell_resource: float
    cell_capacity: float
    resource_probability: float
    resource_heterogeneity: float
    resource_quantum: float
    initial_energy: float
    harvest_limit: float
    conversion_efficiency: float
    maintenance_cost: float
    movement_cost: float
    reproduction_threshold: float
    offspring_energy: float
    reproduction_cost: float
    reproduction_attempt_cost: float
    max_age: int
    death_resource_fraction: float
    mutation_rate: float
    observer_interval: int
    assay_sample_size: int
    assay_episodes: int
    assay_ticks: int


def validate_probability(value: float, name: str) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1]")


def validate_config(config: ForagingConfig) -> ForagingConfig:
    if not config.protocol_version:
        raise ValueError("protocol_version cannot be empty")
    if config.condition not in CONDITIONS:
        raise ValueError("condition must be informative or cue_neutral")
    if config.width < 3 or config.height < 3:
        raise ValueError("width and height must be at least 3")
    if config.ticks < 1:
        raise ValueError("ticks must be positive")
    if not 1 <= config.initial_population <= config.width * config.height:
        raise ValueError("initial_population must fit in the grid")
    if config.initial_cell_resource < 0.0:
        raise ValueError("initial_cell_resource cannot be negative")
    if config.cell_capacity <= 0.0:
        raise ValueError("cell_capacity must be positive")
    if config.initial_cell_resource > config.cell_capacity:
        raise ValueError("initial resource exceeds cell capacity")
    validate_probability(config.resource_probability, "resource_probability")
    if config.resource_heterogeneity < 0.0:
        raise ValueError("resource_heterogeneity cannot be negative")
    if 0.0 > config.resource_probability - config.resource_heterogeneity:
        raise ValueError("resource probability range falls below zero")
    if config.resource_probability + config.resource_heterogeneity > 1.0:
        raise ValueError("resource probability range exceeds one")
    if config.resource_quantum <= 0.0:
        raise ValueError("resource_quantum must be positive")
    if config.initial_energy <= 0.0:
        raise ValueError("initial_energy must be positive")
    if config.harvest_limit <= 0.0:
        raise ValueError("harvest_limit must be positive")
    validate_probability(config.conversion_efficiency, "conversion_efficiency")
    if config.conversion_efficiency <= 0.0:
        raise ValueError("conversion_efficiency must be positive")
    if config.maintenance_cost < 0.0:
        raise ValueError("maintenance_cost cannot be negative")
    if config.movement_cost < 0.0:
        raise ValueError("movement_cost cannot be negative")
    if config.reproduction_threshold < config.offspring_energy + config.reproduction_cost:
        raise ValueError("reproduction threshold cannot fund offspring and cost")
    if config.offspring_energy <= 0.0:
        raise ValueError("offspring_energy must be positive")
    if config.reproduction_cost < 0.0:
        raise ValueError("reproduction_cost cannot be negative")
    if config.reproduction_attempt_cost < 0.0:
        raise ValueError("reproduction_attempt_cost cannot be negative")
    if config.max_age < 1:
        raise ValueError("max_age must be positive")
    validate_probability(config.death_resource_fraction, "death_resource_fraction")
    validate_probability(config.mutation_rate, "mutation_rate")
    if config.observer_interval < 1:
        raise ValueError("observer_interval must be positive")
    if config.assay_sample_size < 1:
        raise ValueError("assay_sample_size must be positive")
    if config.assay_episodes < 1:
        raise ValueError("assay_episodes must be positive")
    if config.assay_ticks < 1:
        raise ValueError("assay_ticks must be positive")
    return config


def load_config(path: Path | str) -> ForagingConfig:
    raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    world = raw["world"]
    resource = raw["resource"]
    life = raw["life"]
    observation = raw["observation"]
    assay = raw["assay"]
    return validate_config(
        ForagingConfig(
            protocol_version=str(raw["protocol_version"]),
            name=str(raw["name"]),
            condition=str(raw["condition"]),
            width=int(world["width"]),
            height=int(world["height"]),
            ticks=int(world["ticks"]),
            initial_population=int(world["initial_population"]),
            initial_cell_resource=float(resource["initial_cell_resource"]),
            cell_capacity=float(resource["cell_capacity"]),
            resource_probability=float(resource["probability"]),
            resource_heterogeneity=float(resource["heterogeneity"]),
            resource_quantum=float(resource["quantum"]),
            initial_energy=float(life["initial_energy"]),
            harvest_limit=float(life["harvest_limit"]),
            conversion_efficiency=float(life["conversion_efficiency"]),
            maintenance_cost=float(life["maintenance_cost"]),
            movement_cost=float(life["movement_cost"]),
            reproduction_threshold=float(life["reproduction_threshold"]),
            offspring_energy=float(life["offspring_energy"]),
            reproduction_cost=float(life["reproduction_cost"]),
            reproduction_attempt_cost=float(life["reproduction_attempt_cost"]),
            max_age=int(life["max_age"]),
            death_resource_fraction=float(life["death_resource_fraction"]),
            mutation_rate=float(life["mutation_rate"]),
            observer_interval=int(observation["interval"]),
            assay_sample_size=int(assay["sample_size"]),
            assay_episodes=int(assay["episodes"]),
            assay_ticks=int(assay["ticks"]),
        )
    )


def ancestor_controller() -> list[int]:
    """The five-locus lookup ancestor: every cue maps to STAY (§4)."""
    return [ACTION_STAY] * CUE_COUNT


def controller_hash(actions: list[int] | tuple[int, ...]) -> str:
    """bytes2hex(sha256(UInt8[UInt8(action) …])) — the lineage genome hash."""
    return hashlib.sha256(bytes(actions)).hexdigest()


def wrap_coordinate(value: int, size: int) -> int:
    """Julia mod1: 1-based toroidal wrap (Dynamics.jl:1)."""
    return value % size if value % size != 0 else size


def orthogonal_neighbors(x: int, y: int, width: int, height: int) -> tuple[tuple[int, int], ...]:
    """North, East, South, West — Dynamics.jl:3-10."""
    return (
        (x, wrap_coordinate(y - 1, height)),
        (wrap_coordinate(x + 1, width), y),
        (x, wrap_coordinate(y + 1, height)),
        (wrap_coordinate(x - 1, width), y),
    )


# ── state layout (kernel state paths) ────────────────────────────────────────
# Grid cells are keyed "x,y" (1-based, Julia order): bounded exact-path
# claims for the mechanism registry. Organisms are keyed by CELL (at most one
# organism per cell, constitution §3.1) so every effect path is pre-boundable.

def cell_key(x: int, y: int) -> str:
    return f"{x},{y}"


def resource_path(x: int, y: int) -> tuple[str, ...]:
    return ("resources", cell_key(x, y))


def probability_path(x: int, y: int) -> tuple[str, ...]:
    return ("probabilities", cell_key(x, y))


def occupancy_path(x: int, y: int) -> tuple[str, ...]:
    return ("occupancy", cell_key(x, y))


def organism_path(x: int, y: int) -> tuple[str, ...]:
    return ("organisms", cell_key(x, y))


def organism_field_path(x: int, y: int, field: str) -> tuple[str, ...]:
    return ("organisms", cell_key(x, y), field)


def grid_paths(subsystem: str, width: int, height: int) -> list[tuple[str, ...]]:
    return [
        (subsystem, cell_key(x, y))
        for y in range(1, height + 1)
        for x in range(1, width + 1)
    ]


def organism_cell(record: dict[str, Any]) -> tuple[int, int]:
    return record["x"], record["y"]


def organism_from_record(record: dict[str, Any]) -> dict[str, Any]:
    """Defensive copy of a read-view organism record."""
    return {
        "id": record["id"],
        "parent_id": record["parent_id"],
        "x": record["x"],
        "y": record["y"],
        "energy": record["energy"],
        "age": record["age"],
        "controller": list(record["controller"]),
        "birth_tick": record["birth_tick"],
    }
