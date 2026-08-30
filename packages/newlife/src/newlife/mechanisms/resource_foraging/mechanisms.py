"""Resource Foraging mechanism registry (World 1).

The frozen constitution's tick order (EXPERIMENT.md §3.5) becomes the declared
stage order; each mechanism is a registry entry (MechanismSpec + a pure step
function over its declared read view, the named streams, and ambient run
context). State paths are cell-keyed ("x,y", 1-based Julia order) so every
effect path is pre-bindable with exact-path claims — the profile authorizes
every write at runtime (pain point P2).

Faithfulness notes (docs/worlds/001-resource-foraging.md §5):
- movement cost is charged by the harvest-metabolism stage (Julia
  harvest_and_metabolize!), which reads the attempted-movers set the movement
  stage published into declared tick state — the constitution's stage dataflow
  made explicit instead of hidden in one function's locals;
- ledger death loss is split per stage (metabolize / reproduce / age); the
  observer sums them into the constitution's single death_loss line;
- organisms carry birth_tick so the aging stage reproduces Julia's
  existing_ids semantics without extra state (newborns have birth_tick ==
  tick+1 and are not aged in their birth tick).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from newlife.core.contracts import Event, MechanismSpec, StateClaim, StateDelta
from newlife.core.errors import ContractError
from newlife.mechanisms.resource_foraging.model import (
    ACTION_STAY,
    CUE_COUNT,
    RNG_STREAM_NAMES,
    cell_key,
    controller_hash,
    grid_paths,
    organism_field_path,
    organism_from_record,
    organism_path,
    orthogonal_neighbors,
    occupancy_path,
    resource_path,
    wrap_coordinate,
)


class WorldProtocolError(ContractError):
    """A mechanism step violated the world protocol (not the contract layer)."""


@dataclass(frozen=True)
class MechanismStep:
    effects: tuple[Any, ...]
    records: tuple[dict[str, Any], ...]


def _claims(paths, permission: str) -> list[StateClaim]:
    return [StateClaim(path, permission) for path in paths]


def _flow_paths() -> list[tuple[str, ...]]:
    return [
        ("counters", "flows", name)
        for name in (
            "external_input",
            "overflow_loss",
            "harvested_resource",
            "conversion_loss",
            "maintenance_loss",
            "movement_loss",
            "reproduction_loss",
            "death_loss",
        )
    ]


def _ledger_paths() -> list[tuple[str, ...]]:
    return [
        ("ledger", name)
        for name in (
            "external_input",
            "overflow_loss",
            "harvested_resource",
            "conversion_loss",
            "maintenance_loss",
            "movement_loss",
            "reproduction_loss",
            "death_loss_metabolize",
            "death_loss_reproduce",
            "death_loss_age",
            "balance_error",
            "before_total",
        )
    ]


TICK_READ = ("counters", "tick")


def _read_tick(view: Mapping[tuple[str, ...], Any]) -> int:
    return view[TICK_READ]


def _grid(view: Mapping[tuple[str, ...], Any], subsystem: str, width: int, height: int):
    """View paths → (x, y) dict in 1-based Julia coordinates."""
    return {
        (x, y): view[(subsystem, cell_key(x, y))]
        for y in range(1, height + 1)
        for x in range(1, width + 1)
    }


def _organism_records(view, width: int, height: int) -> dict[int, dict[str, Any]]:
    records = {}
    for y in range(1, height + 1):
        for x in range(1, width + 1):
            record = view.get(organism_path(x, y))
            if record is not None:
                records[record["id"]] = organism_from_record(record)
    return records


def build_mechanism_specs(config) -> list[MechanismSpec]:
    """The six registry entries + the evidence observer, with exact-path
    claims derived from the world geometry."""
    width, height = config.width, config.height
    resources = grid_paths("resources", width, height)
    probabilities = grid_paths("probabilities", width, height)
    occupancy = grid_paths("occupancy", width, height)
    organisms = grid_paths("organisms", width, height)
    energies = [
        organism_field_path(x, y, "energy")
        for y in range(1, height + 1)
        for x in range(1, width + 1)
    ]
    ages = [
        organism_field_path(x, y, "age")
        for y in range(1, height + 1)
        for x in range(1, width + 1)
    ]
    flow_paths = _flow_paths()
    ledger_paths = _ledger_paths()

    def spec(identity, plane, role, claims, effects, stage, after=(), streams=()):
        return MechanismSpec(
            identity=identity,
            version=config.protocol_version,
            plane=plane,
            biological_role=role,
            ports=("state",),
            claims=tuple(claims),
            schedule={"stage": stage, "after": list(after)},
            rng_streams=tuple(streams),
            allowed_effects=frozenset(effects),
            invariants=("resource-foraging-v1",),
        )

    return [
        spec(
            "resource-environment",
            "biological",
            "exogenous resource replenishment",
            _claims(probabilities, "read")
            + _claims(resources, "read")
            + _claims(resources, "own")
            + _claims([TICK_READ], "read")
            + _claims([("counters", "flows", "external_input"), ("counters", "flows", "overflow_loss")], "own")
            + _claims([("ledger", "external_input"), ("ledger", "overflow_loss")], "own"),
            {"StateDelta"},
            stage="replenish",
            streams=("environment",),
        ),
        spec(
            "forager-movement",
            "biological",
            "perception, action intent, and movement conflict resolution",
            _claims(organisms, "read")
            + _claims(occupancy, "read")
            + _claims(resources, "read")
            + _claims([TICK_READ], "read")
            + _claims(organisms, "own")
            + _claims(occupancy, "own")
            + _claims(
                [
                    ("tick_state", "attempted"),
                    ("counters", "movement_attempts"),
                    ("counters", "successful_moves"),
                    ("counters", "decisions"),
                    ("counters", "aligned_actions"),
                    ("counters", "true_cue_counts"),
                    ("counters", "perceived_cue_counts"),
                ],
                "own",
            ),
            {"StateDelta", "Event"},
            stage="perceive-move",
            streams=("sensing", "selection"),
        ),
        spec(
            "forager-harvest-metabolism",
            "biological",
            "resource harvest, conversion, movement and maintenance costs, energy deaths",
            _claims([("tick_state", "attempted")], "read")
            + _claims([TICK_READ], "read")
            + _claims(resources, "read")
            + _claims(organisms, "read")
            + _claims(resources, "own")
            + _claims(energies, "own")
            + _claims(organisms, "own")
            + _claims(occupancy, "own")
            + _claims([("counters", "deaths")], "own")
            + _claims(flow_paths, "own")
            + _claims(
                [
                    ("ledger", "harvested_resource"),
                    ("ledger", "conversion_loss"),
                    ("ledger", "maintenance_loss"),
                    ("ledger", "movement_loss"),
                    ("ledger", "death_loss_metabolize"),
                ],
                "own",
            ),
            {"StateDelta", "Event"},
            stage="harvest-metabolize",
            after=("perceive-move",),
        ),
        spec(
            "forager-reproduction",
            "biological",
            "resource-driven reproduction with declared mutation",
            _claims([TICK_READ], "read")
            + _claims(resources, "read")
            + _claims(organisms, "read")
            + _claims(occupancy, "read")
            + _claims(resources, "own")
            + _claims(organisms, "own")
            + _claims(energies, "own")
            + _claims(occupancy, "own")
            + _claims([("counters", "next_organism_id"), ("counters", "births"), ("counters", "deaths")], "own")
            + _claims([("counters", "flows", "reproduction_loss"), ("counters", "flows", "death_loss")], "own")
            + _claims([("ledger", "reproduction_loss"), ("ledger", "death_loss_reproduce")], "own"),
            {"StateDelta", "Event"},
            stage="reproduce",
            after=("harvest-metabolize",),
            streams=("selection", "mutation"),
        ),
        spec(
            "forager-aging",
            "biological",
            "age increment and lifespan deaths",
            _claims([TICK_READ], "read")
            + _claims(resources, "read")
            + _claims(organisms, "read")
            + _claims(resources, "own")
            + _claims(ages, "own")
            + _claims(organisms, "own")
            + _claims(occupancy, "own")
            + _claims([("counters", "deaths")], "own")
            + _claims([("counters", "flows", "death_loss")], "own")
            + _claims([("ledger", "death_loss_age")], "own"),
            {"StateDelta", "Event"},
            stage="age",
            after=("reproduce",),
        ),
        spec(
            "world-observer",
            "evidence",
            "tick ledger verification and interval snapshots",
            _claims(resources, "read")
            + _claims(organisms, "read")
            + _claims(occupancy, "read")
            + _claims(ledger_paths, "read")
            + _claims(
                [
                    TICK_READ,
                    ("counters", "births"),
                    ("counters", "deaths"),
                    ("counters", "movement_attempts"),
                    ("counters", "successful_moves"),
                    ("counters", "decisions"),
                    ("counters", "aligned_actions"),
                    ("counters", "true_cue_counts"),
                    ("counters", "perceived_cue_counts"),
                    ("counters", "flows", "external_input"),
                    ("counters", "flows", "overflow_loss"),
                    ("counters", "flows", "harvested_resource"),
                    ("counters", "flows", "conversion_loss"),
                    ("counters", "flows", "maintenance_loss"),
                    ("counters", "flows", "movement_loss"),
                    ("counters", "flows", "reproduction_loss"),
                    ("counters", "flows", "death_loss"),
                ],
                "read",
            )
            + _claims(
                [
                    ("counters", "tick"),
                    ("counters", "births"),
                    ("counters", "deaths"),
                    ("counters", "movement_attempts"),
                    ("counters", "successful_moves"),
                    ("counters", "decisions"),
                    ("counters", "aligned_actions"),
                    ("counters", "true_cue_counts"),
                    ("counters", "perceived_cue_counts"),
                    ("counters", "flows", "external_input"),
                    ("counters", "flows", "overflow_loss"),
                    ("counters", "flows", "harvested_resource"),
                    ("counters", "flows", "conversion_loss"),
                    ("counters", "flows", "maintenance_loss"),
                    ("counters", "flows", "movement_loss"),
                    ("counters", "flows", "reproduction_loss"),
                    ("counters", "flows", "death_loss"),
                    ("ledger", "balance_error"),
                    ("ledger", "before_total"),
                ],
                "own",
            ),
            {"StateDelta", "Event"},
            stage="observe",
            after=("age",),
        ),
    ]


def _add(path, value) -> StateDelta:
    return StateDelta(path, "add", value)


def _set(path, value) -> StateDelta:
    return StateDelta(path, "set", value)


def _spend(energy: float, requested: float) -> float:
    """Dynamics.jl spend_energy!: capped at current energy."""
    spent = min(energy, requested)
    return spent


def environment_step(view, *, environment_stream, config) -> MechanismStep:
    """Dynamics.jl add_resources! — per-cell probability draw, quantum add,
    capacity-capped overflow. Tick-start totals feed the ledger."""
    tick = _read_tick(view)
    probabilities = _grid(view, "probabilities", config.width, config.height)
    resources = _grid(view, "resources", config.width, config.height)
    effects: list[StateDelta] = []
    external_input = 0.0
    overflow = 0.0
    for y in range(1, config.height + 1):
        for x in range(1, config.width + 1):
            if environment_stream.draw_float() < probabilities[(x, y)]:
                requested = config.resource_quantum
                available_capacity = config.cell_capacity - resources[(x, y)]
                added = min(requested, available_capacity)
                effects.append(_add(resource_path(x, y), added))
                external_input += requested
                overflow += requested - added
    effects += [
        _add(("counters", "flows", "external_input"), external_input),
        _add(("counters", "flows", "overflow_loss"), overflow),
        _set(("ledger", "external_input"), external_input),
        _set(("ledger", "overflow_loss"), overflow),
    ]
    return MechanismStep(tuple(effects), ())


def _true_cue(resources, record, tick, config, root_seed: int) -> int:
    """Dynamics.jl true_cue — declared tie-break, consumes no RNG stream."""
    neighbors = orthogonal_neighbors(record["x"], record["y"], config.width, config.height)
    positions = ((record["x"], record["y"]),) + neighbors
    values = [resources[position] for position in positions]
    start = (record["x"] + 2 * record["y"] + tick + root_seed % 5) % 5
    best_index = start
    best_value = values[start]
    for offset in range(1, 5):
        index = (start + offset) % CUE_COUNT
        if values[index] > best_value:
            best_index = index
            best_value = values[index]
    return best_index + 1


def movement_step(
    view, *, sensing_stream, selection_stream, config, root_seed: int
) -> MechanismStep:
    """Dynamics.jl resolve_movement! — perception (sensing stream only in the
    cue_neutral condition), intent, and uniform conflict resolution."""
    tick = _read_tick(view)
    resources = _grid(view, "resources", config.width, config.height)
    occupancy = _grid(view, "occupancy", config.width, config.height)
    records_by_id = _organism_records(view, config.width, config.height)
    effects: list[StateDelta] = []
    decisions = 0
    aligned = 0
    attempts = 0
    successful = 0
    true_cue_counts = [0] * CUE_COUNT
    perceived_cue_counts = [0] * CUE_COUNT
    attempted_ids: list[int] = []
    intents: dict[tuple[int, int], list[int]] = {}
    for organism_id in sorted(records_by_id):
        record = records_by_id[organism_id]
        actual_cue = _true_cue(resources, record, tick, config, root_seed)
        if config.condition == "informative":
            cue = actual_cue
        else:
            cue = sensing_stream.pick(tuple(range(1, CUE_COUNT + 1)))
        action = record["controller"][cue - 1]
        decisions += 1
        aligned += int(action == actual_cue)
        true_cue_counts[actual_cue - 1] += 1
        perceived_cue_counts[cue - 1] += 1
        if action == ACTION_STAY:
            continue
        attempted_ids.append(organism_id)
        attempts += 1
        if action == 2:
            target = (record["x"], wrap_coordinate(record["y"] - 1, config.height))
        elif action == 3:
            target = (wrap_coordinate(record["x"] + 1, config.width), record["y"])
        elif action == 4:
            target = (record["x"], wrap_coordinate(record["y"] + 1, config.height))
        else:
            target = (wrap_coordinate(record["x"] - 1, config.width), record["y"])
        if occupancy[target] != 0:
            continue
        intents.setdefault(target, []).append(organism_id)
    winners: list[tuple[int, tuple[int, int]]] = []
    for target in sorted(intents):
        contenders = sorted(intents[target])
        winner = contenders[0] if len(contenders) == 1 else selection_stream.pick(tuple(contenders))
        winners.append((winner, target))
        successful += 1
    # Phase 1 (clear all origins) then phase 2 (commit all destinations) —
    # Dynamics.jl:173-181; sequential per-organism writes would clobber swaps.
    for winner, _ in winners:
        record = records_by_id[winner]
        effects.append(_set(organism_path(record["x"], record["y"]), None))
        effects.append(_set(occupancy_path(record["x"], record["y"]), 0))
    for winner, target in winners:
        record = records_by_id[winner]
        moved = organism_from_record(record)
        moved["x"], moved["y"] = target
        effects.append(_set(organism_path(target[0], target[1]), moved))
        effects.append(_set(occupancy_path(target[0], target[1]), winner))
    effects += [
        _set(("tick_state", "attempted"), attempted_ids),
        _add(("counters", "movement_attempts"), attempts),
        _add(("counters", "successful_moves"), successful),
        _add(("counters", "decisions"), decisions),
        _add(("counters", "aligned_actions"), aligned),
        _set(("counters", "true_cue_counts"), true_cue_counts),
        _set(("counters", "perceived_cue_counts"), perceived_cue_counts),
    ]
    return MechanismStep(tuple(effects), ())


def harvest_metabolism_step(view, *, config) -> MechanismStep:
    """Dynamics.jl harvest_and_metabolize! + remove_energy_deaths!."""
    tick = _read_tick(view)
    resources = _grid(view, "resources", config.width, config.height)
    attempted = set(view[("tick_state", "attempted")])
    records_by_id = _organism_records(view, config.width, config.height)
    effects: list[StateDelta] = []
    records: list[dict[str, Any]] = []
    harvested_total = 0.0
    conversion_loss = 0.0
    maintenance_loss = 0.0
    movement_loss = 0.0
    local_energy: dict[int, float] = {}
    for organism_id in sorted(records_by_id):
        record = records_by_id[organism_id]
        x, y = record["x"], record["y"]
        harvested = min(config.harvest_limit, resources[(x, y)])
        harvested_total += harvested
        effects.append(_add(resource_path(x, y), -harvested))
        gained = harvested * config.conversion_efficiency
        effects.append(_add(organism_field_path(x, y, "energy"), gained))
        conversion_loss += harvested - gained
        energy = record["energy"] + gained
        if organism_id in attempted:
            spent = _spend(energy, config.movement_cost)
            energy -= spent
            movement_loss += spent
            effects.append(_add(organism_field_path(x, y, "energy"), -spent))
        spent = _spend(energy, config.maintenance_cost)
        energy -= spent
        maintenance_loss += spent
        effects.append(_add(organism_field_path(x, y, "energy"), -spent))
        local_energy[organism_id] = energy
    death_loss = 0.0
    deaths = 0
    for organism_id in sorted(records_by_id):
        record = records_by_id[organism_id]
        if local_energy[organism_id] <= 0.0:
            x, y = record["x"], record["y"]
            returned_target = local_energy[organism_id] * config.death_resource_fraction
            returned = min(returned_target, config.cell_capacity - resources[(x, y)])
            loss = local_energy[organism_id] - returned
            effects.append(_set(organism_path(x, y), None))
            effects.append(_set(occupancy_path(x, y), 0))
            effects.append(_add(resource_path(x, y), returned))
            records.append(
                {
                    "kind": "Death",
                    "organism_id": organism_id,
                    "death_tick": tick + 1,
                    "genome_hash": controller_hash(record["controller"]),
                    "source": "forager-harvest-metabolism",
                    "time": str(tick + 1),
                }
            )
            death_loss += loss
            deaths += 1
    effects += [
        _add(("counters", "flows", "harvested_resource"), harvested_total),
        _add(("counters", "flows", "conversion_loss"), conversion_loss),
        _add(("counters", "flows", "maintenance_loss"), maintenance_loss),
        _add(("counters", "flows", "movement_loss"), movement_loss),
        _add(("counters", "flows", "death_loss"), death_loss),
        _add(("counters", "deaths"), deaths),
        _set(("ledger", "harvested_resource"), harvested_total),
        _set(("ledger", "conversion_loss"), conversion_loss),
        _set(("ledger", "maintenance_loss"), maintenance_loss),
        _set(("ledger", "movement_loss"), movement_loss),
        _set(("ledger", "death_loss_metabolize"), death_loss),
    ]
    return MechanismStep(tuple(effects), tuple(records))


def reproduction_step(
    view, *, selection_stream, mutation_stream, config, next_organism_id: int
) -> MechanismStep:
    """Dynamics.jl reproduce! — selection-resolved birth conflicts, declared
    mutation draws, attempt costs, and the post-reproduction death pass."""
    tick = _read_tick(view)
    occupancy = _grid(view, "occupancy", config.width, config.height)
    records_by_id = _organism_records(view, config.width, config.height)
    effects: list[StateDelta] = []
    records: list[dict[str, Any]] = []
    attempted_parents: list[int] = []
    intents: dict[tuple[int, int], list[int]] = {}
    local_energy = {
        organism_id: record["energy"] for organism_id, record in records_by_id.items()
    }
    for organism_id in sorted(records_by_id):
        parent = records_by_id[organism_id]
        if not parent["energy"] >= config.reproduction_threshold:
            continue
        attempted_parents.append(organism_id)
        empty_neighbors = [
            position
            for position in orthogonal_neighbors(
                parent["x"], parent["y"], config.width, config.height
            )
            if occupancy[position] == 0
        ]
        if not empty_neighbors:
            continue
        target = selection_stream.pick(tuple(empty_neighbors))
        intents.setdefault(target, []).append(organism_id)
    winners: list[tuple[int, tuple[int, int]]] = []
    for target in sorted(intents):
        contenders = sorted(intents[target])
        winner = contenders[0] if len(contenders) == 1 else selection_stream.pick(tuple(contenders))
        winners.append((winner, target))
    reproduction_loss = 0.0
    winner_ids = {winner for winner, _ in winners}
    for organism_id in attempted_parents:
        if organism_id in winner_ids:
            continue
        spent = _spend(local_energy[organism_id], config.reproduction_attempt_cost)
        local_energy[organism_id] -= spent
        reproduction_loss += spent
        record = records_by_id[organism_id]
        effects.append(
            _add(organism_field_path(record["x"], record["y"], "energy"), -spent)
        )
    births = 0
    next_id = next_organism_id
    newborns: list[dict[str, Any]] = []
    for parent_id, target in winners:
        parent = records_by_id[parent_id]
        required = config.offspring_energy + config.reproduction_cost
        if not local_energy[parent_id] >= required:
            continue
        local_energy[parent_id] -= required
        reproduction_loss += config.reproduction_cost
        effects.append(
            _add(organism_field_path(parent["x"], parent["y"], "energy"), -required)
        )
        controller = list(parent["controller"])
        for index in range(CUE_COUNT):
            if mutation_stream.draw_float() < config.mutation_rate:
                controller[index] = mutation_stream.pick(tuple(range(1, CUE_COUNT + 1)))
        newborn_id = next_id
        next_id += 1
        newborn = {
            "id": newborn_id,
            "parent_id": parent_id,
            "x": target[0],
            "y": target[1],
            "energy": config.offspring_energy,
            "age": 0,
            "controller": controller,
            "birth_tick": tick + 1,
        }
        newborns.append(newborn)
        effects.append(_set(organism_path(target[0], target[1]), newborn))
        effects.append(_set(occupancy_path(target[0], target[1]), newborn_id))
        records.append(
            {
                "kind": "Birth",
                "organism_id": newborn_id,
                "parent_id": parent_id,
                "birth_tick": tick + 1,
                "genome_hash": controller_hash(controller),
                "source": "forager-reproduction",
                "time": str(tick + 1),
            }
        )
        births += 1
    # Post-reproduction death pass over the updated population (parents at
    # their locally tracked energies, newborns at offspring_energy) — the
    # Julia code inserts newborns into world.organisms first.
    death_loss = 0.0
    deaths = 0
    resources_grid = _grid(view, "resources", config.width, config.height)
    population = dict(records_by_id)
    for newborn in newborns:
        population[newborn["id"]] = newborn
    for organism_id in sorted(population):
        record = population[organism_id]
        energy = (
            local_energy[organism_id] if organism_id in records_by_id else record["energy"]
        )
        if energy > 0.0:
            continue
        x, y = record["x"], record["y"]
        returned_target = energy * config.death_resource_fraction
        returned = min(returned_target, config.cell_capacity - resources_grid[(x, y)])
        loss = energy - returned
        effects.append(_set(organism_path(x, y), None))
        effects.append(_set(occupancy_path(x, y), 0))
        effects.append(_add(resource_path(x, y), returned))
        records.append(
            {
                "kind": "Death",
                "organism_id": organism_id,
                "death_tick": tick + 1,
                "genome_hash": controller_hash(record["controller"]),
                "source": "forager-reproduction",
                "time": str(tick + 1),
            }
        )
        death_loss += loss
        deaths += 1
    effects += [
        _set(("counters", "next_organism_id"), next_id),
        _add(("counters", "births"), births),
        _add(("counters", "deaths"), deaths),
        _add(("counters", "flows", "reproduction_loss"), reproduction_loss),
        _add(("counters", "flows", "death_loss"), death_loss),
        _set(("ledger", "reproduction_loss"), reproduction_loss),
        _set(("ledger", "death_loss_reproduce"), death_loss),
    ]
    return MechanismStep(tuple(effects), tuple(records))


def aging_step(view, *, config) -> MechanismStep:
    """Dynamics.jl age_and_remove! over the tick-start population (organisms
    with birth_tick <= tick; newborns carry birth_tick == tick+1)."""
    tick = _read_tick(view)
    resources = _grid(view, "resources", config.width, config.height)
    records_by_id = _organism_records(view, config.width, config.height)
    effects: list[StateDelta] = []
    records: list[dict[str, Any]] = []
    death_loss = 0.0
    deaths = 0
    for organism_id in sorted(records_by_id):
        record = records_by_id[organism_id]
        if record["birth_tick"] > tick:
            continue
        effects.append(_add(organism_field_path(record["x"], record["y"], "age"), 1))
        if record["age"] + 1 >= config.max_age:
            x, y = record["x"], record["y"]
            returned_target = record["energy"] * config.death_resource_fraction
            returned = min(returned_target, config.cell_capacity - resources[(x, y)])
            loss = record["energy"] - returned
            effects.append(_set(organism_path(x, y), None))
            effects.append(_set(occupancy_path(x, y), 0))
            effects.append(_add(resource_path(x, y), returned))
            records.append(
                {
                    "kind": "Death",
                    "organism_id": organism_id,
                    "death_tick": tick + 1,
                    "genome_hash": controller_hash(record["controller"]),
                    "source": "forager-aging",
                    "time": str(tick + 1),
                }
            )
            death_loss += loss
            deaths += 1
    effects += [
        _add(("counters", "deaths"), deaths),
        _add(("counters", "flows", "death_loss"), death_loss),
        _set(("ledger", "death_loss_age"), death_loss),
    ]
    return MechanismStep(tuple(effects), tuple(records))
