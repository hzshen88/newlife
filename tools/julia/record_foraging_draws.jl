# record_foraging_draws.jl — L2 draw recorder for the World 1 comparison.
#
# Replays a frozen resource-foraging-v1 world (Parworlds Experiment 001) with
# per-call-site draw logging, writing one JSONL per stream plus a
# recorded_observables.json with the history snapshots, final counts, ledger
# flows, and assay result — the comparison targets for the newlife injected
# run.
#
# Recording design: the RNG is NOT wrapped (a wrapper AbstractRNG would
# dispatch to different Julia rand methods and change the consumption
# sequence). Instead the frozen Dynamics/Assays call sites are copied
# verbatim with a logging shim at each rand call — same rng, same calls, in
# the same order. Self-check: an uninstrumented control run must reproduce
# the instrumented run's final snapshot and assay result exactly.
#
# Usage (stdlib-only; run with the Parworlds project env):
#   julia --project=<Parworlds> record_foraging_draws.jl \
#     --config <informative.toml> --seed 101 --out <dir>
#
# Outputs:
#   <out>/<stream>.jsonl   one JSON object per recorded tick:
#                          {"t": tick, "d": [{"k":"f","v":hex16} |
#                                            {"k":"p","v":value} |
#                                            {"k":"u64","v":hex16} |
#                                            {"k":"perm","v":[[x,y],…]}]}
#   <out>/recorded_observables.json

using Parworlds
using Parworlds.ResourceForaging
import Parworlds.EvidenceKernel
import Parworlds.ResourceForaging: RNG_STREAM_NAMES, Stay, ForagingAction, ForagingCue,
    ACTIONS, true_cue, perceived_cue, action_target, harvest_and_metabolize!, remove_energy_deaths!,
    age_and_remove!, validate_world, total_stored_energy, snapshot, controller_hash,
    ancestor_controller, assay_config
using Random, SHA

const CUE_COUNT_LOCAL = 5

# ── minimal JSON writer (stdlib-only) ────────────────────────────────────────

json_escape(s::AbstractString) = replace(s, "\\" => "\\\\", "\"" => "\\\"")

json_value(x::Float64) = repr(x)          # shortest round-trip
json_value(x::Integer) = string(x)
json_value(x::AbstractString) = "\"$(json_escape(x))\""
json_value(x::Symbol) = "\"$(String(x))\""
json_value(x::Nothing) = "null"
json_value(v::Vector) = "[$(join(json_value.(v), ","))]"
json_value(v::Matrix) = json_value(vec(v))
json_value(v::AbstractVector) = "[$(join(json_value.(v), ","))]"
json_value(t::Tuple) = json_value(collect(t))
json_value(p::Pair) = json_value(p)
json_value(d::Dict) = "{" * join(["\"$(json_escape(String(k)))\":$(json_value(v))" for (k, v) in sort!(collect(d); by = pr -> String(pr.first))], ",") * "}"
json_value(nt::NamedTuple) = json_value(Dict(pairs(nt)))

function jsonl_append(path::AbstractString, obj::Dict)
    open(path, "a") do io
        println(io, json_value(obj))
    end
end

hex16(x::UInt64) = string(x, base = 16, pad = 16)

# ── recorder state ───────────────────────────────────────────────────────────

mutable struct Recorder
    current::String
    tick::Int
    scope::String
    entry::Vector{Any}
    files::Dict{Tuple{String,String},String}   # (scope, stream) → path
    out::String
    Recorder(out::String) = new("", -1, "main", Any[], Dict{Tuple{String,String},String}(), mkpath(out) |> _ -> out)
end

function open_stream!(rec::Recorder, stream::AbstractString, tick::Int)
    if rec.current != stream || rec.tick != tick
        flush_stream!(rec)
        rec.current = String(stream)
        rec.tick = tick
    end
end

function set_scope!(rec::Recorder, scope::AbstractString)
    rec.current != "" && flush_stream!(rec)
    rec.scope = String(scope)
    rec.current = ""
    rec.tick = -1
end

function flush_stream!(rec::Recorder)
    if !isempty(rec.entry)
        key = (rec.scope, rec.current)
        path = get!(rec.files, key, begin
            dir = joinpath(rec.out, rec.scope)
            mkpath(dir)
            joinpath(dir, "$(rec.current).jsonl")
        end)
        jsonl_append(path, Dict("t" => rec.tick, "d" => rec.entry))
        rec.entry = Any[]
    end
end

log_float!(rec::Recorder, stream::AbstractString, tick::Int, value::Float64) =
    (open_stream!(rec, stream, tick); push!(rec.entry, Dict("k" => "f", "v" => hex16(reinterpret(UInt64, value)))))
log_pick!(rec::Recorder, stream::AbstractString, tick::Int, value) =
    (open_stream!(rec, stream, tick); push!(rec.entry, Dict("k" => "p", "v" => value)))
log_u64!(rec::Recorder, stream::AbstractString, tick::Int, value::UInt64) =
    (open_stream!(rec, stream, tick); push!(rec.entry, Dict("k" => "u64", "v" => hex16(value))))
function log_perm!(rec::Recorder, stream::AbstractString, tick::Int, perm)
    # Initialization shuffles Cartesian positions; assay shuffles organism
    # IDs. Keep both as one typed permutation record, preserving the element
    # shape expected by the Python injector.
    value = [p isa Tuple ? [p[1], p[2]] : p for p in perm]
    open_stream!(rec, stream, tick)
    push!(rec.entry, Dict("k" => "perm", "v" => value))
end

# ── verbatim instrumented copies (Dynamics.jl / Assays.jl call sites) ───────

function initialize_world_recorded!(rec::Recorder, config::ForagingConfig, seed::Integer)
    validate_config(config)
    bank = EvidenceKernel.RngBank(seed, RNG_STREAM_NAMES)
    initialization_rng = EvidenceKernel.rng_stream(bank, "initialization")
    environment_rng = EvidenceKernel.rng_stream(bank, "environment")

    resources = fill(config.initial_cell_resource, config.width, config.height)
    probabilities = Matrix{Float64}(undef, config.width, config.height)
    for index in eachindex(probabilities)   # column-major: x fastest
        draw = rand(environment_rng)
        log_float!(rec, "environment", 0, draw)
        offset = (2.0 * draw - 1.0) * config.resource_heterogeneity
        probabilities[index] = config.resource_probability + offset
    end

    occupancy = zeros(Int, config.width, config.height)
    organisms = Dict{Int,Organism}()
    lineage = LineageRecord[]
    positions = collect(CartesianIndices(occupancy))
    # stdlib shuffle! unrolled (Random 1.12: FORWARD Fisher-Yates with the
    # ltm52 bounded range) — self-checked below against the real shuffle!.
    shuffled = collect(positions)
    mask = 3
    for i in 2:length(shuffled)
        j = 1 + rand(initialization_rng, Random.ltm52(i, mask))
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
        i == 1 + mask && (mask = 2 * mask + 1)
    end
    control_bank = EvidenceKernel.RngBank(seed, RNG_STREAM_NAMES)
    control_positions = collect(positions)
    shuffle!(EvidenceKernel.rng_stream(control_bank, "initialization"), control_positions)
    @assert [Tuple(p) for p in control_positions] == [Tuple(p) for p in shuffled] "unrolled shuffle diverged from stdlib shuffle!"
    log_perm!(rec, "initialization", 0, [Tuple(p) for p in shuffled])

    for id in 1:config.initial_population
        position = shuffled[id]
        organism = Organism(id, 0, position[1], position[2], config.initial_energy, 0, ancestor_controller())
        organisms[id] = organism
        occupancy[position] = id
        push!(lineage, LineageRecord(id, 0, 0, nothing, controller_hash(organism.controller)))
    end

    world = ForagingWorld(config, 0, resources, probabilities, occupancy, organisms,
        lineage, config.initial_population + 1, bank, TickLedger(), FlowTotals(),
        0, 0, 0, 0, 0, 0, zeros(Int, CUE_COUNT_LOCAL), zeros(Int, CUE_COUNT_LOCAL))
    validate_world(world)
    world
end

function add_resources_recorded!(rec::Recorder, world::ForagingWorld, tick::Int)
    rng = EvidenceKernel.rng_stream(world.rng_bank, "environment")
    input = 0.0
    overflow = 0.0
    for index in eachindex(world.resources)
        draw = rand(rng)
        log_float!(rec, "environment", tick, draw)
        if draw < world.resource_probabilities[index]
            requested = world.config.resource_quantum
            available_capacity = world.config.cell_capacity - world.resources[index]
            added = min(requested, available_capacity)
            world.resources[index] += added
            input += requested
            overflow += requested - added
        end
    end
    input, overflow
end

function resolve_movement_recorded!(rec::Recorder, world::ForagingWorld, tick::Int)
    intents = Dict{Tuple{Int,Int},Vector{Int}}()
    attempted = Int[]
    for id in sort!(collect(keys(world.organisms)))
        organism = world.organisms[id]
        actual_cue = true_cue(world, organism)
        cue = perceived_cue(world, organism, actual_cue)
        if world.config.condition != :informative
            log_pick!(rec, "sensing", tick, UInt8(cue))
        end
        action = organism.controller.actions[Int(cue)]
        world.decisions += 1
        world.aligned_actions += Int(action) == Int(actual_cue)
        world.true_cue_counts[Int(actual_cue)] += 1
        world.perceived_cue_counts[Int(cue)] += 1
        action == Stay && continue
        push!(attempted, id)
        target = action_target(world, organism, action)
        world.occupancy[target...] == 0 || continue
        push!(get!(intents, target, Int[]), id)
    end
    winners = Tuple{Int,Tuple{Int,Int}}[]
    selection_rng = EvidenceKernel.rng_stream(world.rng_bank, "selection")
    for target in sort!(collect(keys(intents)))
        contenders = sort!(intents[target])
        if length(contenders) == 1
            winner = only(contenders)
        else
            winner = rand(selection_rng, contenders)
            log_pick!(rec, "selection", tick, winner)
        end
        push!(winners, (winner, target))
    end
    for (id, _) in winners
        organism = world.organisms[id]
        world.occupancy[organism.x, organism.y] = 0
    end
    for (id, target) in winners
        organism = world.organisms[id]
        organism.x, organism.y = target
        world.occupancy[target...] = id
    end
    attempted, length(winners)
end

function mutate_recorded!(rec::Recorder, controller::Controller, rng::AbstractRNG, rate::Float64, tick::Int)
    actions = Vector{UInt8}(undef, CUE_COUNT_LOCAL)
    for index in 1:CUE_COUNT_LOCAL
        draw = rand(rng)
        log_float!(rec, "mutation", tick, draw)
        if draw < rate
            picked = rand(rng, ACTIONS)
            log_pick!(rec, "mutation", tick, UInt8(picked))
            actions[index] = UInt8(picked)
        else
            actions[index] = UInt8(controller.actions[index])
        end
    end
    Controller(ntuple(i -> ForagingAction(actions[i]), CUE_COUNT_LOCAL))
end

function reproduce_recorded!(rec::Recorder, world::ForagingWorld, tick::Int)
    intents = Dict{Tuple{Int,Int},Vector{Int}}()
    attempted_parents = Int[]
    selection_rng = EvidenceKernel.rng_stream(world.rng_bank, "selection")
    for id in sort!(collect(keys(world.organisms)))
        parent = world.organisms[id]
        parent.energy >= world.config.reproduction_threshold || continue
        push!(attempted_parents, id)
        empty_neighbors = [position for position in orthogonal_neighbors(
            parent.x, parent.y, world.config.width, world.config.height
        ) if world.occupancy[position...] == 0]
        isempty(empty_neighbors) && continue
        target = rand(selection_rng, empty_neighbors)
        log_pick!(rec, "selection", tick, [target[1], target[2]])
        push!(get!(intents, target, Int[]), id)
    end
    winners = Tuple{Int,Tuple{Int,Int}}[]
    for target in sort!(collect(keys(intents)))
        contenders = sort!(intents[target])
        if length(contenders) == 1
            winner = only(contenders)
        else
            winner = rand(selection_rng, contenders)
            log_pick!(rec, "selection", tick, winner)
        end
        push!(winners, (winner, target))
    end
    reproduction_loss = 0.0
    winner_ids = Set(first(w) for w in winners)
    for id in attempted_parents
        id in winner_ids && continue
        organism = world.organisms[id]
        spent = min(organism.energy, world.config.reproduction_attempt_cost)
        organism.energy -= spent
        reproduction_loss += spent
    end
    mutation_rng = EvidenceKernel.rng_stream(world.rng_bank, "mutation")
    newborns = Organism[]
    for (parent_id, target) in winners
        parent = world.organisms[parent_id]
        required = world.config.offspring_energy + world.config.reproduction_cost
        parent.energy >= required || continue
        parent.energy -= required
        reproduction_loss += world.config.reproduction_cost
        id = world.next_organism_id
        world.next_organism_id += 1
        controller = mutate_recorded!(rec, parent.controller, mutation_rng, world.config.mutation_rate, tick)
        push!(newborns, Organism(id, parent_id, target[1], target[2], world.config.offspring_energy, 0, controller))
    end
    for newborn in newborns
        world.organisms[newborn.id] = newborn
        world.occupancy[newborn.x, newborn.y] = newborn.id
        push!(world.lineage, LineageRecord(newborn.id, newborn.parent_id, world.tick + 1, nothing, controller_hash(newborn.controller)))
        world.births += 1
    end
    reproduction_loss
end

function step_recorded!(rec::Recorder, world::ForagingWorld)
    before = total_stored_energy(world)
    existing_ids = sort!(collect(keys(world.organisms)))
    tick = world.tick
    external_input, overflow_loss = add_resources_recorded!(rec, world, tick)
    attempted, successful_moves = resolve_movement_recorded!(rec, world, tick)
    harvested_resource, conversion_loss, maintenance_loss, movement_loss =
        harvest_and_metabolize!(world, attempted)          # no draws — frozen function reused
    death_loss = remove_energy_deaths!(world)
    reproduction_loss = reproduce_recorded!(rec, world, tick)
    death_loss += remove_energy_deaths!(world)
    death_loss += age_and_remove!(world, existing_ids)
    after = total_stored_energy(world)
    expected_after = before + external_input - overflow_loss - conversion_loss -
                     maintenance_loss - movement_loss - reproduction_loss - death_loss
    balance_error = after - expected_after
    world.last_ledger = TickLedger(external_input, overflow_loss, conversion_loss,
        maintenance_loss, movement_loss, reproduction_loss, death_loss, balance_error)
    world.flows.external_input += external_input
    world.flows.overflow_loss += overflow_loss
    world.flows.harvested_resource += harvested_resource
    world.flows.conversion_loss += conversion_loss
    world.flows.maintenance_loss += maintenance_loss
    world.flows.movement_loss += movement_loss
    world.flows.reproduction_loss += reproduction_loss
    world.flows.death_loss += death_loss
    world.movement_attempts += length(attempted)
    world.successful_moves += successful_moves
    world.tick += 1
    abs(balance_error) <= 1.0e-8 || error("recorded ledger failed at tick $(world.tick): $balance_error")
    validate_world(world) || error("recorded world invariant failed at tick $(world.tick)")
    world
end

function run_assay_recorded!(rec::Recorder, world::ForagingWorld, episode_logs::Dict{String,Any})
    isempty(world.organisms) && return ForagingAssayResult(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assay_rng = EvidenceKernel.rng_stream(world.rng_bank, "assay")
    organism_ids = sort!(collect(keys(world.organisms)))
    shuffle!(assay_rng, organism_ids)
    # shuffle! consumes Julia's internal bounded draws, which are deliberately
    # not wrapped by this recorder. Record its completed permutation as the
    # typed draw consumed by the injection interface, before the first episode
    # seed u64 draw.
    log_perm!(rec, "assay", world.tick, organism_ids)
    sample_count = min(world.config.assay_sample_size, length(organism_ids))
    sampled_ids = organism_ids[1:sample_count]
    true_harvest = 0.0; ablated_harvest = 0.0
    true_aligned = 0; ablated_aligned = 0
    true_decisions = 0; ablated_decisions = 0
    paired = sample_count * world.config.assay_episodes
    episode_index = 0
    for id in sampled_ids
        controller = world.organisms[id].controller
        for _ in 1:world.config.assay_episodes
            episode_index += 1
            # Episode execution changes the recorder scope. Return to the
            # training world's main scope before recording the next assay seed
            # so all sampling draws stay in main/assay.jsonl.
            set_scope!(rec, "main")
            seed_draw = rand(assay_rng, UInt64)
            log_u64!(rec, "assay", world.tick, seed_draw)
            for (branch, condition) in (("true", :informative), ("ablated", :cue_neutral))
                scope = "episodes/episode-$(episode_index)-$(branch)"
                set_scope!(rec, scope)
                episode_world = initialize_world_recorded!(rec, assay_config(world.config, condition), seed_draw)
                only(values(episode_world.organisms)).controller = controller
                while episode_world.tick < episode_world.config.ticks && !isempty(episode_world.organisms)
                    step_recorded!(rec, episode_world)
                end
                flush_stream!(rec)
                episode_logs[scope] = Dict(
                    "seed_hex" => hex16(seed_draw),
                    "condition" => String(condition),
                    "harvested_resource" => episode_world.flows.harvested_resource,
                    "tick" => episode_world.tick,
                    "movement_attempts" => episode_world.movement_attempts,
                    "aligned_actions" => episode_world.aligned_actions,
                    "decisions" => episode_world.decisions,
                )
                if branch == "true"
                    true_harvest += episode_world.flows.harvested_resource
                    true_aligned += episode_world.aligned_actions
                    true_decisions += episode_world.decisions
                else
                    ablated_harvest += episode_world.flows.harvested_resource
                    ablated_aligned += episode_world.aligned_actions
                    ablated_decisions += episode_world.decisions
                end
            end
        end
    end
    mean_true = true_harvest / paired
    mean_ablated = ablated_harvest / paired
    ForagingAssayResult(sample_count, paired, mean_true, mean_ablated, mean_true - mean_ablated,
        true_decisions == 0 ? 0.0 : true_aligned / true_decisions,
        ablated_decisions == 0 ? 0.0 : ablated_aligned / ablated_decisions)
end

# ── driver ───────────────────────────────────────────────────────────────────

function snapshot_dict(world::ForagingWorld)
    s = snapshot(world)
    Dict(
        "tick" => s.tick, "population" => s.population,
        "total_resource" => s.total_resource, "total_organism_energy" => s.total_organism_energy,
        "births" => s.births, "deaths" => s.deaths,
        "movement_attempts" => s.movement_attempts, "successful_moves" => s.successful_moves,
        "decisions" => s.decisions, "aligned_actions" => s.aligned_actions,
        "true_cue_counts" => collect(s.true_cue_counts), "perceived_cue_counts" => collect(s.perceived_cue_counts),
        "external_input" => s.external_input, "overflow_loss" => s.overflow_loss,
        "harvested_resource" => s.harvested_resource, "conversion_loss" => s.conversion_loss,
        "maintenance_loss" => s.maintenance_loss, "movement_loss" => s.movement_loss,
        "reproduction_loss" => s.reproduction_loss, "death_loss" => s.death_loss,
        "balance_error" => s.balance_error,
    )
end

function main()
    args = Dict{String,String}()
    i = 1
    while i <= length(ARGS) - 1
        if startswith(ARGS[i], "--")
            args[ARGS[i][3:end]] = ARGS[i+1]
            i += 2
        else
            i += 1
        end
    end
    config = load_config(args["config"])
    seed = parse(Int, args["seed"])
    out = args["out"]
    rec = Recorder(out)

    # instrumented run with recording (scope: main)
    world = initialize_world_recorded!(rec, config, seed)
    flush_stream!(rec)
    history = Any[]
    push!(history, snapshot_dict(world))
    while world.tick < config.ticks && !isempty(world.organisms)
        step_recorded!(rec, world)
        if world.tick % config.observer_interval == 0 || world.tick == config.ticks || isempty(world.organisms)
            push!(history, snapshot_dict(world))
        end
    end
    flush_stream!(rec)
    episode_logs = Dict{String,Any}()
    assay = run_assay_recorded!(rec, world, episode_logs)
    flush_stream!(rec)

    # control run (frozen functions, no recording) — must match exactly
    control = initialize_world(config, seed)
    run!(control)
    control_assay = run_assay(control)
    @assert snapshot_dict(world) == snapshot_dict(control) "instrumented run diverged from the frozen control run"
    @assert all(getfield(world.flows, f) == getfield(control.flows, f) for f in fieldnames(FlowTotals)) "instrumented flows diverged"
    @assert string(assay.harvest_contribution) == string(control_assay.harvest_contribution) "instrumented assay diverged"

    dynamics_path = joinpath(dirname(pathof(Parworlds)), "worlds", "ResourceForaging", "Dynamics.jl")
    observables = Dict(
        "seed" => seed,
        "condition" => String(config.condition),
        "history" => history,
        "final" => snapshot_dict(world),
        "assay" => Dict(
            "sampled_genomes" => assay.sampled_genomes,
            "paired_episodes" => assay.paired_episodes,
            "mean_true_harvest" => assay.mean_true_harvest,
            "mean_ablated_harvest" => assay.mean_ablated_harvest,
            "harvest_contribution" => assay.harvest_contribution,
            "true_alignment_rate" => assay.true_alignment_rate,
            "ablated_alignment_rate" => assay.ablated_alignment_rate,
        ),
        "episodes" => episode_logs,
        "lineage_length" => length(world.lineage),
        "dynamics_sha256" => bytes2hex(sha256(read(dynamics_path))),
    )
    open(joinpath(out, "recorded_observables.json"), "w") do io
        println(io, json_value(observables))
    end
    println("recorded seed $seed ($(config.condition)) -> $out")
    println("assay harvest_contribution: ", assay.harvest_contribution)
    println("final population: ", length(world.organisms))
end

main()
