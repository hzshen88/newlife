# Changelog

`proofroot` and `newlife` are released together under one version from one tag; `exloop`
has its own version and its own repository. Dates are the PyPI upload dates.

## 0.1.1 — 2026-09-06

Depends on `exloop>=0.1,<0.2`, released to PyPI the same day.

### Fixed

- **S1 was true by construction.** The scaffolded runner compared `env.lock` with a hash
  of itself. `newlife freeze` now rewrites `env.lock` from the live environment, commits
  that one file and pins it into the registration; the runner's S1 compares the packages
  installed at run time against it; `newlife audit` re-hashes it (and every `--data` file)
  and goes red on drift. The four questions registered under 0.1.0 carry the vacuous S1;
  recorded in `docs/zh/product/2026-09-04-first-user-questions.md`.
- `env.lock` depended on import order. The environment was enumerated from `sys.path` as
  it stood, and libraries such as `ray` (behind `spatio-flux`) insert a vendored directory
  into `sys.path` on import, so a runner that imported them saw one more distribution than
  the process that wrote the lock and S1 went red for no reason. Distributions are now
  read from the interpreter's site-packages directories only.
- The recovery message after committing `prereg.md` by mistake pointed at a path that does
  not work; it now says to open a new question folder and leave the old one as a record.
- `newlife pilot` prints `PILOT (exploratory, no evidential weight)` instead of a line that
  read like a verdict.
- `newlife start` no longer promises the exploration stage when the `exloop` package is
  missing; with exloop now a dependency that branch is a safety net.
- `newlife blocks` gives the install command when nothing can be imported.

### Added

- `newlife start <folder>`: git init, `.gitignore`, `NEXT.md`, and the skills installed into
  every AI tool directory found on the machine. One command from `pip install` to talking
  to your AI.
- `newlife pilot`: runs the runner before the freeze into `pilot/<stamp>/`, never
  `results/`, and appends the units it produced to `pilot/ledger.jsonl`.
- **Two freeze gates**: goal readiness (the six anchors in `goal.md`) and pilot coverage
  (every row of `prereg.md` §2 marked seen / blind / mechanical, every seen row backed by
  a pilot run, at least one blind row or a waiver on the record).
- `origin/` in every question folder: where the record of the exploration that produced
  the question goes; everything in it counts as seen.
- `newlife freeze --data FILE...`: pins downloaded inputs by git blob hash into the
  registration; `audit` re-checks them. The `.gitignore` template ignores
  `questions/*/data/` by default.
- `newlife status <folder>`: stage, what is done, what blocks, the next step and what the
  person has to decide, read off the folder; knows that `summary.json` without
  `reproduction.json` is an interrupted run, not a verdict.
- `newlife --version`.
- The `newlife` entry skill: answers "how does this work" and "which step are we at" in the
  person's terms and routes to the stage skills.
- `exloop` is a declared dependency; `pip install newlife` brings the exploration skill.

### Changed

- Skills renamed: `decidable-question` → `newlife-goal`, `preregister-verdict` →
  `newlife-prereg`, `exploration-loop` → `exloop`. `newlife skills install` installs
  whole skill directories and finds `~/.claude/skills`, `~/.codex/skills` and
  `~/.workbuddy/skills` on its own; copies that differ from the master are skipped unless
  `--force`.
- The PyPI page and the repository README are written for the person who will use the
  tool, not for its implementer. The author's Chinese working documents moved to
  `docs/zh/`.

## 0.1.0 — 2026-09-04

First release of `proofroot` and `newlife` on PyPI.

- `newlife init / freeze / run / check / audit`: one folder per question; the freeze is the
  first git commit of `prereg.md` (vendored `prereg.sh`); the verdict is computed by the
  scaffolded runner from a frozen conjunction; the audit proves from commit ancestry that
  the registration was frozen, never edited, and that every committed output post-dates it.
- `check` with three gates: vacuous-criterion scan, silent-degradation scan, unit alignment.
- Three skills shipped in the wheel (under their old names) and `newlife skills install`.
- Optional extras `process-bigraph` and `spatio-flux`; `newlife blocks` lists installed
  building blocks.
- Known defect, fixed in 0.1.1: the scaffolded S1 compared `env.lock` with itself.
