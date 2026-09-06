# Contributing

## Running the tests

Requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/). Nothing else is needed
for the trust core:

```bash
uv sync --package proofroot
uv run --package proofroot pytest packages/proofroot/tests -q
```

`newlife` itself needs the pinned upstream runtime, which lives behind an optional extra
(vendor types never reach the core, and packaging enforces it):

```bash
uv sync --package newlife --extra process-bigraph
uv run --package newlife pytest packages/newlife/tests -q
python3 scripts/check_imports.py                               # import lint
```

**The `--extra process-bigraph` is not optional in practice.** Five test modules import
`bigraph_schema` unconditionally; without the extra, pytest fails at collection with
`ModuleNotFoundError: No module named 'bigraph_schema'`.

Run the tests that cover what you changed rather than the whole suite while iterating; the
whole suite runs in CI on every push to `main` and every pull request (`lint.yml`).

Twelve tests skip unless the author's private exloop checkout is present: the third
world's oracle-conformance module (`tests/third_world/test_oracle_conformance.py`) replays
a Moran fixation oracle that lives in that repository's frozen verification documents, and
the module is `skipif`-gated on the file existing at `~/Projects/exloop/...`. On CI and on
any other machine they report as skipped, not as passed; the third world's own verdict
bundle under `results/third-world/` is the public record of that comparison.

Reproduce the second world (Hudson's `ms` minimal coalescent) end to end; this compiles
the vendored `ms` sources itself, so it needs a C compiler and nothing more:

```bash
uv run --package newlife python -m newlife.conform.second_world_verdict --output /tmp/second-world
```

It prints the verdict bundle and exits non-zero if the verdict does not hold. Expected:
`"passed": true`, `"verdict": "ms_minimal_coalescent_reproducible"`, 30 replicates.

The first world (Resource Foraging) is the one reproduction that cannot be run from this
repository alone: its L2 recorded-draw comparison replays draws recorded by the Julia
reference implementation, so it needs Julia and a checkout of ParaLife, which is private.
`examples/first-world/README.md` has the commands for anyone who has both.

## What the checks enforce

- `scripts/check_imports.py`: `examples/` holds no Python files (assembling mechanisms is
  configuration, not code), and vendor types stay behind the adapter layer.
- `scripts/check_record.py`: every closed milestone under `results/` is registered in the
  world documents, the proposal and the milestone table; a missing cell goes red.
- `scripts/check_release_artifacts.py` and `scripts/smoke_release_install.py`: what the
  release workflow runs against the built wheels before anything is uploaded.
- `packages/newlife/tests/test_public_english.py`: docstrings of public modules are English.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat(scope): …`, `fix(scope): …`, `docs(scope): …`). The history is written in Chinese;
  English is equally welcome.
- `ruff` for lint and format; type hints in the Python 3.11+ style; `pathlib.Path` over
  `os.path`.
- Public modules carry English docstrings. Tests and the author's working documents under
  `docs/zh/` are Chinese; user-facing documents under `docs/` are English.
- **Never edit anything under `results/`.** Each directory is a frozen verdict bundle. A
  defective registration is left as it is and a new one is opened.

## How a change to newlife itself gets accepted

Anything that changes what a verdict can mean goes through the same pipeline the tool
ships: a goal, a preregistration frozen before the implementation, a runner, a bundle under
`results/`, a world document. [`docs/milestones.md`](docs/milestones.md) describes the
pipeline and lists every milestone so far. Fixes to the harness, documentation and
packaging do not need a milestone; open a pull request.

## Releasing

[`docs/releasing.md`](docs/releasing.md). One tag publishes `proofroot` and `newlife`
through PyPI Trusted Publishing; `exloop` is released first, by hand, from its own
repository.
