# Generate cross-language test vectors for proofroot from the EvidenceCore.jl
# oracle (frozen in place in ParaLife; see newlife docs/design/proposal.md §5.10).
#
# Scope (proofroot schedule step 1, per §5.10 discipline 1): D1 current encoding
# (`evidencecore-rng-v1` ONLY — legacy encodings are deliberately not ported and
# get no vectors here), D4 bank seed derivation incl. lowercase normalization,
# D2 phase terminality. D5 is a constant vocabulary; nothing to vectorize.
#
# Regenerate:  julia generate_vectors.jl > evidencecore_rng_v1.json
# (run from this directory; adjust ORACLE_PATH if ParaLife moves).

module Oracle
include("/Users/hzshen/Projects/paralife/packages/EvidenceCore/src/EvidenceCore.jl")
end

using .Oracle
using Random
using Dates

const ROOT_SEEDS = UInt64[
    0x0000000000000000, 0x0000000000000001, 0x000000000000002a,
    0x8000000000000000, 0xffffffffffffffff,
]
const STREAM_NAMES = String[
    "a", "mutation", "sampling", "world_0", "cell-division",
    "a-very-long-stream-name_used-in-parworlds-000",
]
# One declaration list per bank snapshot; all names must match the D4 name
# regex as declared (the oracle validates BEFORE lowercasing).
const BANK_DECLARATIONS = [
    ["mutation", "sampling"],
    ["a", "world_0", "cell-division"],
]

hex64(x::UInt64) = "0x" * string(x, base = 16, pad = 16)

function main()
    println("{")
    println("\"schema\": \"proofroot.vectors.evidencecore-rng-v1\",")
    println("\"oracle\": \"EvidenceCore.jl (ParaLife, frozen in place)\",")
    println("\"generated\": \"$(today())\",")

    # D1: derive_stream_seed over the root x name grid.
    println("\"derive_stream_seed\": [")
    entries = String[]
    for root in ROOT_SEEDS, name in STREAM_NAMES
        s = Oracle.derive_stream_seed(Oracle.EVIDENCECORE_RNG_V1, root, name)
        push!(entries, "  {\"root_seed_dec\": \"$(string(root))\", " *
            "\"root_seed_hex\": \"$(hex64(root))\", " *
            "\"name\": \"$name\", " *
            "\"seed_dec\": \"$(string(s))\", \"seed_hex\": \"$(hex64(s))\"}")
    end
    println(join(entries, ",\n"))
    println("],")

    # D4: bank snapshot — derived per-stream seeds (the provenance product).
    println("\"bank_stream_seeds\": [")
    entries = String[]
    for root in ROOT_SEEDS, names in BANK_DECLARATIONS
        bank = Oracle.RngBank(root, names, Oracle.EVIDENCECORE_RNG_V1)
        seeds = Oracle.rng_stream_seeds(bank)
        pairs = String[]
        for key in sort!(collect(keys(seeds)))
            push!(pairs, "{\"name\": \"$key\", \"seed_dec\": \"$(string(seeds[key]))\", \"seed_hex\": \"$(hex64(seeds[key]))\"}")
        end
        decl = join(names, " ")
        push!(entries, "  {\"root_seed_hex\": \"$(hex64(root))\", \"declared\": \"[$decl]\", \"streams\": [$(join(pairs, ", "))]}")
    end
    println(join(entries, ",\n"))
    println("],")

    # D2: phase terminality (TitleCase spellings only; legacy UPPER parse is
    # not ported to proofroot and gets no vectors).
    println("\"phase_terminality\": [")
    phases = string.(instances(Oracle.RunPhase))
    entries = String[]
    for ph in phases
        v = Oracle.parse_phase(ph)
        push!(entries, "  {\"name\": \"$ph\", \"is_terminal\": $(Oracle.is_terminal(v))}")
    end
    println(join(entries, ",\n"))
    println("]")

    println("}")
end

main()
