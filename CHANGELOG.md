# Changelog

`proofroot` and `newlife` are released together under one version from one tag; `exloop`
has its own version and its own repository. Dates are the PyPI upload dates.

## Unreleased

### Added

- **The freeze now refuses when the environment changed after the last pilot.**
  `newlife pilot` records a digest of the live environment in `pilot/ledger.jsonl`, and the
  pilot gate compares it with the environment at the freeze. Installing a package in
  between used to be invisible: the freeze rewrites `env.lock` from the new environment, so
  S1 went green against an environment in which the runner had **never once been
  executed** — and the discovery came at run time, after the one irreversible step, when
  repairing the environment would itself turn S1 red. A ledger written before this existed
  carries no digest and stays green, so registrations already in flight can still freeze.

### Fixed

- **A registration frozen without the `**Frozen at commit:** _pending_` line could never
  pass an audit, and nothing said so at the time.** The stamp could then only be *inserted*;
  the audit's `strip_stamp` removes the stamp line but not the blank line inserted with it,
  so INTEGRITY failed on every audit from then on — surfacing one pilot and one full verdict
  later, when "never re-freeze" leaves no repair and the round has to be demoted to
  exploratory. `newlife pilot` and `newlife freeze` now restore the line before they do
  anything else, so the stamp is always an in-place replacement. Reported from a real
  question that lost a round to it; an assistant drafting the registration by writing the
  whole file drops that line without noticing, because it reads as metadata waiting to be
  filled in rather than a functional anchor. The runner's own error message now says how to
  put it back, for the case where `verdict.py` is invoked directly.
- `newlife blocks` gave the install command only when **nothing** could be imported, so
  someone with `process-bigraph` but not `spatio-flux` saw a listing that worked and never
  learned the other backends existed. It now reports whenever something is absent, and
  separates "not installed" from "installed but the import fails" — `bsp` is the second
  kind and reinstalling it does not help. A package that is not a newlife extra no longer
  gets an install command that cannot resolve.

### Changed

- `docs/writing-a-world.md` says why that example's `PortBinding` is `"add"`: the third
  field is a claim about what the wrapped `update` returns, not a default. Copying the line
  to wrap a simulator that returns absolute values writes a level in as though it were an
  increment — **nothing raises**, the numbers stay plausible and in the right units, and
  the pilot records them as covered. `newlife-prereg` rule six states the same trap for the
  person writing the criteria.
- The bytes of `env.lock` are built by one function, `provenance.env_text()`, rather than
  the same expression spelled out in the scaffold, the freeze and the runner template.

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
