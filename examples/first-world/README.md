# first-world: Resource Foraging (Parworlds Experiment 001)

**This directory is data, not code.** The world assembly and the experimental protocol are
configuration files (a verbatim copy of the frozen `resource-foraging-v1` semantics); the
entry point lives in the library:

```bash
# single world (training + causal assay)
uv run --package newlife python -m newlife.mechanisms.resource_foraging \
  --config examples/first-world/informative.toml --seed 101 \
  --output runs/first-world/informative-101.json

# paired control (same seed, the only controlled difference is the sensory cue)
uv run --package newlife python -m newlife.mechanisms.resource_foraging \
  --config examples/first-world/cue_neutral.toml --seed 101 \
  --output runs/first-world/cue_neutral-101.json
```

The cross-language value-by-value comparison (L2, recorded-draw injection) runs the
two-condition gate into a fresh output directory. It needs Julia and a checkout of
ParaLife's `parworlds`, which is a private repository:

```bash
uv run --package newlife python scripts/run_world1_l2.py \
  --parworlds /path/to/parworlds --out /tmp/newlife-world1-l2-101
```

It records `informative` and `cue-neutral` with the Julia recorder, then
`scripts/compare_world1.py` compares tick 0, the intervals, the final snapshot, the assay
and every named stream by proofroot's IEEE 754 bit pattern. Afterwards the gate acceptor
produces the pain-point measurements and the final verdict:

```bash
uv run --package newlife python scripts/accept_world1_gate.py \
  --parworlds /path/to/parworlds \
  --l2-root /tmp/newlife-world1-l2-101 \
  --out /tmp/newlife-world1-l2-101/gate.json
```

`--reuse-recordings` re-runs only the comparison on existing recordings.

The import lint enforces zero Python files in this directory: the application layer has no
runtime code to write, which is what "configuration, not code" means mechanically
(proposal §2, goal 5).
