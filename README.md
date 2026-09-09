# newlife

[![PyPI](https://img.shields.io/pypi/v/newlife)](https://pypi.org/project/newlife/)
[![lint-and-test](https://github.com/hzshen88/newlife/actions/workflows/lint.yml/badge.svg)](https://github.com/hzshen88/newlife/actions/workflows/lint.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Turn a curiosity into a question that can be settled, freeze what would count as an
answer before running anything, and leave a verdict that can be audited from git alone.**

You talk to your AI; it runs the commands. Setup is two lines:

```bash
python -m pip install newlife
newlife start my-research
```

Open `my-research` in Claude Code, Codex, or any AI tool that reads `SKILL.md` files, and
say:

> Explore this with me: *your curiosity*

`NEXT.md` in that folder says what happens from here. If you get lost, ask your AI "how
does this work" or "which step are we at"; the installed `newlife` skill answers in your
terms. [`docs/first-question.md`](docs/first-question.md) walks one question end to end
in about ten minutes, with the real output of every command.

Requires Python 3.12 or newer and `git` (the freeze is a git commit; that is what makes the
timestamp real). `start` tells you if git has no identity to sign with, rather than
guessing one.

## What happens, in your words

1. **Explore.** Your AI asks one or two honing questions, then walks one edge at a time and
   keeps a map silently. When several explanations fit, it uses idea-lab's
   Draw–Attack–Compare–Check reasoning inside the same conversation; you never choose a
   second workflow. You answer and decide. (`exloop` and `idea-lab` ship together in the
   [`exloop`](https://pypi.org/project/exloop/) package; newlife depends on it, so the same
   install brings both.)
2. **Hand off.** When a boundary can be stated as "what measurement would make the answer
   different", the AI says so once. If you agree, a question folder appears with the
   exploration record inside it.
3. **Is it worth asking?** The AI asks only what the map cannot supply: who would bet the
   other way, is the answer settled by design or by running, who changes what they do.
   Six anchors go into `goal.md`. One you cannot fill yet means keep exploring or narrow,
   not a failure.
4. **World and pilot.** Your simulator goes into `verdict.py`; a pilot run shows you every
   quantity a criterion will name. Everything seen is now *seen*.
5. **Criteria.** Every judgement unit is marked seen / blind / mechanical, and at least one
   is blind. A confirmatory round in which every number was already seen carries no
   information.
6. **Freeze.** The one irreversible step; the AI asks you first. Two gates refuse on their
   own if the goal is unfilled or a criterion was never piloted. Your environment and any
   downloaded data are pinned by hash at this moment.
7. **Verdict.** H1, H0 or INVALID, computed by your runner from the frozen conjunction,
   never written by hand, with an audit from git history alone.

Two moments are yours alone: the freeze, and committing the results.

## What the record can prove afterwards

`newlife audit` shows, from commit ancestry rather than dates anyone could type: the
registration has a freeze commit; the stamped hash matches it; the criteria were never
edited afterwards; every committed output post-dates the freeze; and `env.lock` and every
pinned data file still hash to what was frozen. The runner's own units add the other half:
the run reproduces itself byte for byte, the packages installed at run time are exactly the
ones recorded, and every criterion proves at run time that it *can* go red.

The freeze refuses on five checks against your own files: goal readiness, pilot coverage,
the reproduction class (a `seeded` or `stochastic` world must account for its repetition
count), a scan for criteria that are true by construction, and a scan for parse failures
that silently fall back to a convenient default. The run then checks that the units
`prereg.md` declares are exactly the units the runner computed.

A registration whose criteria turn out to be defective is left as `INVALID`, exactly as it
stands, and a new one is opened. Never re-frozen. That record is how a conclusion was
reached, not a failure to tidy away.

## If you would rather type

```bash
cd my-research
newlife init 2026-09-05-my-question                 # scaffold; prereg.md is left uncommitted on purpose
$EDITOR questions/2026-09-05-my-question/goal.md    # is this worth asking? six anchors
$EDITOR questions/2026-09-05-my-question/verdict.py # your world
newlife pilot  questions/2026-09-05-my-question     # look at every quantity a criterion will name
$EDITOR questions/2026-09-05-my-question/prereg.md  # the criteria; every row seen / blind / mechanical
newlife freeze questions/2026-09-05-my-question     # this commit is the proof
#   … --data questions/2026-09-05-my-question/data/*.csv   # reading downloaded data? pin it
newlife run    questions/2026-09-05-my-question
newlife status questions/2026-09-05-my-question     # stage, blockers, next step, decisions
git add questions/2026-09-05-my-question/results && git commit -m "verdict"
newlife audit  questions/2026-09-05-my-question
```

Never `git add -A` before the freeze: `prereg.md` must be committed by the freeze itself,
and `newlife init` leaves exactly that file uncommitted for that reason. Questions are
siblings, not a chain: a question's verdict never runs another question's runner.

## Underneath

| Package | What it is | Where |
|---|---|---|
| `newlife` | The harness: scaffold, gates, freeze, verdict runner template, audit, and the `newlife`, `newlife-goal`, `newlife-prereg` skills. | [`packages/newlife`](packages/newlife/), [PyPI](https://pypi.org/project/newlife/) |
| `proofroot` | Language-neutral trust core: named RNG stream derivation, run phases, evidence tiers, canonical serialization with cross-language vectors. Zero dependencies. | [`packages/proofroot`](packages/proofroot/), [PyPI](https://pypi.org/project/proofroot/) |
| `exloop` | The exploration skills (`exloop` plus its nested `idea-lab`) and the zero-dependency state helper they use. A dependency of newlife; its own repository. | [github.com/hzshen88/exloop](https://github.com/hzshen88/exloop), [PyPI](https://pypi.org/project/exloop/) |

Optional simulation backends: `pip install "newlife[spatio-flux]"` (Monod kinetics, dynamic
FBA with GLPK, diffusion, particles) or `"newlife[process-bigraph]"` for the runtime alone;
`newlife blocks` lists what is installed. Third-party processes run unmodified inside a
declared contract: a mechanism says which state paths it owns and which effects it may
emit, and writing anywhere else is refused by the contract layer, not by your solver.
[`docs/writing-a-world.md`](docs/writing-a-world.md) shows the twenty lines that wrap a
simulator which is not a process-bigraph `Process`, and — for code that is **not** an
installed package, such as a local checkout of your own or sources written inside the
question folder — what has to be recorded for the run to be repeatable, and by whom.

## This repository

| Path | What it holds |
|---|---|
| `packages/` | The two libraries above. |
| `docs/` | English documents for users and contributors; [`docs/README.md`](docs/README.md) is the index. |
| `docs/zh/` | The author's working documents, in Chinese: the design proposal, one document per milestone, product notes. |
| `results/` | One directory per closed milestone of newlife itself, holding the machine-computed verdict bundle. |
| `examples/` | Application layer, data only; `import-lint` enforces zero Python files here. |
| `scripts/` | Release checks, the import lint, the record reconciler. |
| `vendor/` | Third-party reference oracles, vendored verbatim and pinned by SHA-256 (currently Hudson's `ms`). |
| `tools/` | Julia helpers for the first world's cross-language comparison. |

### How newlife itself was built, and what you can check here

newlife was built under the discipline it ships. `results/` holds twenty-two verdict
bundles, one per closed milestone, and the two most recent live under
`questions/` — the first milestones run in the same shape this tool gives you, with the
registration and the artifact in one repository, which is what lets `newlife audit`
establish CHRONOLOGY at all; from the second world onward each was judged against a
preregistration frozen before the implementation existed, and the table in
[`docs/milestones.md`](docs/milestones.md) records the H0s and the one INVALID alongside the
H1s. The four earliest milestones predate the goal stage, and one (archival replay) was run
without a separate registration; both facts are in the table.

**What is not public.** The frozen registration documents for those milestones (goal,
question, plan, preregistration) live in the author's private exploration archive, together
with the git history that stamps them. They are not published. A reader of this repository
therefore **cannot audit the author's milestones the way `newlife audit` audits a
question**: what is here is the runners under `packages/newlife/src/newlife/conform/`, the
bundles they produced, and the Chinese world documents that describe each question. The
claim this project makes is about *your* questions, in *your* repository, where `prereg.md`
and `results/` share one git ancestry. Read the author's milestones as history, not as
evidence you are asked to trust.

The bundles under `results/` contain absolute paths from the author's machine. They are
frozen artifacts and are left exactly as they were produced.

### Documents in two languages

Everything a user or contributor needs is in English: this file, the package READMEs,
`docs/first-question.md`, `docs/writing-a-world.md`, `docs/milestones.md`,
`docs/releasing.md`, `CONTRIBUTING.md`, and the skills. The documents under `docs/zh/` are
the author's working record of how the design decisions were reached, written in Chinese
as they happened; nothing there is needed to use the tool.

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md): how to run the tests, what the import lint enforces,
how a milestone of newlife itself gets accepted, and how a release is cut.

## License

Apache-2.0. Upstream notices are preserved per the Apache-2.0 requirements; see
`docs/zh/design/proposal.md` §6.
