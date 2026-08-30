"""Resource Foraging world runtime on the newlife reference kernel.

The driver is the analogue of Julia's `run_with_observation!`: it builds the
initial state (Dynamics.jl initialize_world, including the environment-drawn
replenishment probability field and the initialization-shuffled starting
positions), registers the mechanism registry, and executes the declared stage
order per tick through the contract layer — every state change is an
authorized Effect, every tick closes with the observer's ledger verification
(constitution §9) and world invariant checks (§12).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from newlife.adapters.reference_kernel.kernel import ReferenceKernel
from newlife.mechanisms.resource_foraging import mechanisms as mech
from newlife.mechanisms.resource_foraging.injection import DevStream
from newlife.mechanisms.resource_foraging.model import (
    RNG_STREAM_NAMES,
    cell_key,
    controller_hash,
    load_config,
    organism_path,
    validate_config,
)
from proofroot import EVIDENCECORE_RNG_V1, RngBank

LEDGER_TOLERANCE = 1.0e-8  # constitution §9: a failed ledger is an implementation error


class WorldLedgerError(RuntimeError):
    """The resource-energy ledger failed — the run is `Failed`, not biology."""


def julia_matrix_sum(values: Mapping[tuple[int, int], float], width: int, height: int) -> float:
    """Julia `sum(::Matrix)` reduces in column-major order (x fastest); the
    ledger and snapshot totals replicate that order bit-for-bit."""
    total = 0.0
    for y in range(1, height + 1):
        for x in range(1, width + 1):
            total += values[(x, y)]
    return total


def _cell_organism_energy_sum(organisms: Mapping[int, dict[str, Any]]) -> float:
    """Julia sums organism energies over Dict iteration order, which is not
    reproducible in Python; this port sums in sorted-id order. The divergence
    is confined to last-bit rounding of reported aggregates — the comparison
    protocol (world doc §4) allows 1e-9 on float observables."""
    total = 0.0
    for organism_id in sorted(organisms):
        total += organisms[organism_id]["energy"]
    return total


def build_initial_state(config, initialization_stream, environment_stream) -> dict[str, Any]:
    """Dynamics.jl initialize_world (bank construction aside)."""
    resources = {
        (x, y): config.initial_cell_resource
        for y in range(1, config.height + 1)
        for x in range(1, config.width + 1)
    }
    probabilities = {}
    for y in range(1, config.height + 1):
        for x in range(1, config.width + 1):
            offset = (2.0 * environment_stream.draw_float() - 1.0) * config.resource_heterogeneity
            probabilities[(x, y)] = config.resource_probability + offset
    occupancy = {(x, y): 0 for y in range(1, config.height + 1) for x in range(1, config.width + 1)}
    positions = [
        (x, y) for y in range(1, config.height + 1) for x in range(1, config.width + 1)
    ]
    shuffled = initialization_stream.permutation(positions)
    organisms: dict[str, Any] = {}
    lineage: list[dict[str, Any]] = []
    for organism_id in range(1, config.initial_population + 1):
        x, y = shuffled[organism_id - 1]
        record = {
            "id": organism_id,
            "parent_id": 0,
            "x": x,
            "y": y,
            "energy": config.initial_energy,
            "age": 0,
            "controller": [1, 1, 1, 1, 1],
            "birth_tick": 0,
        }
        organisms[cell_key(x, y)] = record
        occupancy[(x, y)] = organism_id
        lineage.append(
            {
                "kind": "Birth",
                "organism_id": organism_id,
                "parent_id": 0,
                "birth_tick": 0,
                "genome_hash": controller_hash(record["controller"]),
                "source": "initialization",
                "time": "0",
            }
        )
    initial_total = julia_matrix_sum(resources, config.width, config.height) + _cell_organism_energy_sum(
        {record["id"]: record for record in organisms.values()}
    )
    state = {
        "resources": {cell_key(x, y): resources[(x, y)] for y in range(1, config.height + 1) for x in range(1, config.width + 1)},
        "probabilities": {cell_key(x, y): probabilities[(x, y)] for y in range(1, config.height + 1) for x in range(1, config.width + 1)},
        "occupancy": {cell_key(x, y): occupancy[(x, y)] for y in range(1, config.height + 1) for x in range(1, config.width + 1)},
        "organisms": {
            cell_key(x, y): organisms.get(cell_key(x, y))
            for y in range(1, config.height + 1)
            for x in range(1, config.width + 1)
        },
        "tick_state": {"attempted": []},
        "ledger": {name: 0.0 for name in (
            "external_input", "overflow_loss", "harvested_resource", "conversion_loss",
            "maintenance_loss", "movement_loss", "reproduction_loss",
            "death_loss_metabolize", "death_loss_reproduce", "death_loss_age",
            "balance_error",
        )} | {"before_total": initial_total},
        "counters": {
            "tick": 0,
            "next_organism_id": config.initial_population + 1,
            "births": 0,
            "deaths": 0,
            "movement_attempts": 0,
            "successful_moves": 0,
            "decisions": 0,
            "aligned_actions": 0,
            "true_cue_counts": [0] * 5,
            "perceived_cue_counts": [0] * 5,
            "flows": {
                "external_input": 0.0,
                "overflow_loss": 0.0,
                "harvested_resource": 0.0,
                "conversion_loss": 0.0,
                "maintenance_loss": 0.0,
                "movement_loss": 0.0,
                "reproduction_loss": 0.0,
                "death_loss": 0.0,
            },
        },
    }
    return state, lineage


@dataclass
class WorldRunResult:
    config: Any
    tick: int
    population: int
    extinct: bool
    history: list[dict[str, Any]]
    lineage: list[dict[str, Any]]
    final_snapshot: dict[str, Any]


class ForagingWorld:
    """The declared-stage tick loop over the reference kernel."""

    def __init__(self, config, seed: int, *, stream_factory: Callable[[int], Any] | None = None, bank=None) -> None:
        config = validate_config(config)
        if bank is None:
            # Default host generator: DevStream seeded by each derived stream
            # seed (charter: sequences are the host's choice; cross-language
            # claims go through RecordedStream injection, never DevStream).
            bank = RngBank(
                seed, list(RNG_STREAM_NAMES), EVIDENCECORE_RNG_V1,
                stream_factory=stream_factory if stream_factory is not None else DevStream,
            )
        self.bank = bank
        self.config = config
        self.seed = seed
        initialization = bank.rng_stream("initialization")
        environment = bank.rng_stream("environment")
        state, lineage = build_initial_state(config, initialization, environment)
        self.kernel = ReferenceKernel(state)
        self.kernel.trace.extend(lineage)  # the initialization lineage (Julia pushes these in initialize_world)
        for spec in mech.build_mechanism_specs(config):
            self.kernel.register_mechanism(spec)


    # ── per-stage execution ──────────────────────────────────────────────

    def _run_stage(self, identity: str, step: Callable[[Mapping], mech.MechanismStep]) -> None:
        def produce(view: Mapping[tuple[str, ...], Any]) -> mech.MechanismStep:
            return step(view)

        result = self.kernel.guarded_read(identity, produce)
        self.kernel.apply_batch(identity, list(result.effects), list(result.records))

    def tick(self) -> None:
        config = self.config
        self._run_stage(
            "resource-environment",
            lambda view: mech.environment_step(
                view, environment_stream=self.bank.rng_stream("environment"), config=config
            ),
        )
        self._run_stage(
            "forager-movement",
            lambda view: mech.movement_step(
                view,
                sensing_stream=self.bank.rng_stream("sensing"),
                selection_stream=self.bank.rng_stream("selection"),
                config=config,
                root_seed=self.bank.root_seed,
            ),
        )
        self._run_stage(
            "forager-harvest-metabolism",
            lambda view: mech.harvest_metabolism_step(view, config=config),
        )
        self._run_stage(
            "forager-reproduction",
            lambda view: mech.reproduction_step(
                view,
                selection_stream=self.bank.rng_stream("selection"),
                mutation_stream=self.bank.rng_stream("mutation"),
                config=config,
                next_organism_id=self._next_organism_id(),
            ),
        )
        self._run_stage(
            "forager-aging",
            lambda view: mech.aging_step(view, config=config),
        )
        self._run_stage(
            "world-observer",
            lambda view: self._observe(view),
        )

    def _next_organism_id(self) -> int:
        return self.kernel.state["counters"]["next_organism_id"]

    def _observe(self, view: Mapping[tuple[str, ...], Any]) -> mech.MechanismStep:
        """The observer stage: world invariants (§12), the resource-energy
        ledger (§9), the tick increment, and interval snapshots."""
        config = self.config
        tick = view[("counters", "tick")]
        organisms = {
            (record["x"], record["y"]): record
            for cell, record in ((cell_key(x, y), view[organism_path(x, y)])
                                 for y in range(1, config.height + 1)
                                 for x in range(1, config.width + 1))
            if record is not None
        }
        resources = {
            (x, y): view[("resources", cell_key(x, y))]
            for y in range(1, config.height + 1)
            for x in range(1, config.width + 1)
        }
        occupancy = {
            (x, y): view[("occupancy", cell_key(x, y))]
            for y in range(1, config.height + 1)
            for x in range(1, config.width + 1)
        }
        _validate_world_invariants(organisms, resources, occupancy, config, tick)
        before_total = view[("ledger", "before_total")]
        after_total = julia_matrix_sum(resources, config.width, config.height) + _cell_organism_energy_sum(
            {record["id"]: record for record in organisms.values()}
        )
        death_loss = (
            view[("ledger", "death_loss_metabolize")]
            + view[("ledger", "death_loss_reproduce")]
            + view[("ledger", "death_loss_age")]
        )
        expected_after = (
            before_total
            + view[("ledger", "external_input")]
            - view[("ledger", "overflow_loss")]
            - view[("ledger", "conversion_loss")]
            - view[("ledger", "maintenance_loss")]
            - view[("ledger", "movement_loss")]
            - view[("ledger", "reproduction_loss")]
            - death_loss
        )
        balance_error = after_total - expected_after
        if abs(balance_error) > LEDGER_TOLERANCE:
            raise WorldLedgerError(f"resource-energy ledger failed at tick {tick + 1}: {balance_error}")
        effects = [
            mech._set(("ledger", "balance_error"), balance_error),
            mech._set(("ledger", "before_total"), after_total),
            mech._add(("counters", "tick"), 1),
        ]
        new_tick = tick + 1
        records: tuple[dict[str, Any], ...] = ()
        if (
            new_tick % config.observer_interval == 0
            or new_tick == config.ticks
            or not organisms
        ):
            # The snapshot is an evidence trace record (Observer 只读，账本
            # 与快照走 trace，不改训练流).
            records = (self._snapshot(view, organisms, resources, new_tick, balance_error),)
        return mech.MechanismStep(tuple(effects), records)

    def _snapshot(self, view, organisms, resources, tick: int, balance_error: float) -> dict[str, Any]:
        config = self.config
        return {
            "kind": "ForagingSnapshot",
            "tick": tick,
            "population": len(organisms),
            "total_resource": julia_matrix_sum(resources, config.width, config.height),
            "total_organism_energy": _cell_organism_energy_sum(
                {record["id"]: record for record in organisms.values()}
            ),
            "births": view[("counters", "births")],
            "deaths": view[("counters", "deaths")],
            "movement_attempts": view[("counters", "movement_attempts")],
            "successful_moves": view[("counters", "successful_moves")],
            "decisions": view[("counters", "decisions")],
            "aligned_actions": view[("counters", "aligned_actions")],
            "true_cue_counts": list(view[("counters", "true_cue_counts")]),
            "perceived_cue_counts": list(view[("counters", "perceived_cue_counts")]),
            "external_input": view[("counters", "flows", "external_input")],
            "overflow_loss": view[("counters", "flows", "overflow_loss")],
            "harvested_resource": view[("counters", "flows", "harvested_resource")],
            "conversion_loss": view[("counters", "flows", "conversion_loss")],
            "maintenance_loss": view[("counters", "flows", "maintenance_loss")],
            "movement_loss": view[("counters", "flows", "movement_loss")],
            "reproduction_loss": view[("counters", "flows", "reproduction_loss")],
            "death_loss": view[("counters", "flows", "death_loss")],
            "balance_error": balance_error,
            "source": "world-observer",
            "time": str(tick),
        }

    # ── run loop ─────────────────────────────────────────────────────────

    def run(self) -> WorldRunResult:
        config = self.config
        while self.kernel.state["counters"]["tick"] < config.ticks and self.population() > 0:
            self.tick()
        tick = self.kernel.state["counters"]["tick"]
        lineage = [record for record in self.kernel.trace if record["kind"] in {"Birth", "Death"}]
        snapshots = [record for record in self.kernel.trace if record["kind"] == "ForagingSnapshot"]
        return WorldRunResult(
            config=config,
            tick=tick,
            population=self.population(),
            extinct=self.population() == 0,
            history=snapshots,
            lineage=lineage,
            final_snapshot=snapshots[-1] if snapshots else {},
        )

    def population(self) -> int:
        return sum(
            1
            for record in self.kernel.state["organisms"].values()
            if record is not None
        )


def _validate_world_invariants(organisms, resources, occupancy, config, tick: int) -> None:
    """Dynamics.jl validate_world — constitution §12 invariants, checked every
    tick inside the observer's read view."""
    tolerance = 1.0e-9
    for value in resources.values():
        if value < -tolerance:
            raise mech.WorldProtocolError(f"negative resource at tick {tick}: {value}")
        if value > config.cell_capacity + tolerance:
            raise mech.WorldProtocolError(f"resource above capacity at tick {tick}: {value}")
    occupied = sum(1 for value in occupancy.values() if value != 0)
    if occupied != len(organisms):
        raise mech.WorldProtocolError(
            f"occupancy/population mismatch at tick {tick}: {occupied} vs {len(organisms)}"
        )
    seen_ids = set()
    for (x, y), record in organisms.items():
        if occupancy[(x, y)] != record["id"]:
            raise mech.WorldProtocolError(f"occupancy does not match organism at tick {tick}: {(x, y)}")
        if record["energy"] < -tolerance:
            raise mech.WorldProtocolError(f"negative energy at tick {tick}: organism {record['id']}")
        if record["id"] in seen_ids:
            raise mech.WorldProtocolError(f"duplicate organism id at tick {tick}: {record['id']}")
        seen_ids.add(record["id"])
        if not all(action in (1, 2, 3, 4, 5) for action in record["controller"]):
            raise mech.WorldProtocolError(f"illegal action in controller at tick {tick}: {record['id']}")
    for (x, y), organism_id in occupancy.items():
        if organism_id != 0 and (x, y) not in organisms:
            raise mech.WorldProtocolError(f"occupancy ghost at tick {tick}: {(x, y)}")


def run_world(config_path, seed: int, *, stream_factory: Callable[[int], Any] | None = None, bank=None) -> WorldRunResult:
    """The single-world entry point (scripts/run_foraging_world.jl analogue)."""
    config = load_config(config_path)
    world = ForagingWorld(config, seed, stream_factory=stream_factory, bank=bank)
    result = world.run()
    return result
