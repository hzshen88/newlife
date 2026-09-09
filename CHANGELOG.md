# Changelog

`proofroot` and `newlife` are released together under one version from one tag; `exloop`
has its own version and its own repository. Dates are the PyPI upload dates.

## Unreleased

### Added

- **`newlife.scaffold.QUESTION_TOP_LEVEL`** — every name newlife puts at a question
  folder's top level, exported for the layout checkers research repositories write for
  themselves. `SCAFFOLD_FILES` is only day one; this set also carries what the freeze, the
  pilot and the run add later. A repository that keeps its own copy of the list is fine
  until newlife grows the skeleton, and then the copy turns a routine upgrade into a false
  positive on the user's next commit. A test runs `init` and refuses a list that has fallen
  behind what the scaffold actually writes.

### Changed

- **`exloop>=0.2,<0.3`.** The exploration stage now ships two skills, `exloop` and
  `idea-lab`, and both live in the `exloop` package, so one `pip install newlife` still
  brings the whole stage. exloop 0.2 must already be on PyPI when this tag is pushed —
  the build job's smoke install resolves it from there; `docs/releasing.md` says why.
- **Idea Lab is a reasoning pattern inside exploration, not a second front door.** "Explore
  this with me" stays the only entry point: `exloop` keeps the conversation, the persistent
  map, the pivots and the handoff, and reaches for `idea-lab`'s Draw—Attack—Compare—Check
  when one observation has several plausible explanations. The person never chooses between
  skills or fills in a second worksheet. The `newlife` skill, `NEXT.md`, both READMEs and
  `docs/first-question.md` now say it that way, and `newlife skills` counts five skills
  instead of four.
- **An anchor you cannot fill is no longer read as "drop the question".** `NEXT.md`'s triage
  step now has the AI offer candidate wording, narrow the question, or return to exploration
  first; only when no genuine counterparty and no changed decision survive that does the
  question stay an unfrozen curiosity — a useful outcome, not a failure.

## 0.1.3 — 2026-09-06

### Added

- **The freeze checks that `goal.md`'s commitments did not move after the last pilot.**
  `newlife pilot` digests four anchors (`counterparty`, `attack_layer`, `decides`,
  `who_changes_behavior`) into the ledger; the pilot gate refuses when they differ at the
  freeze unless `<!--@goal_changed: …-->` in `prereg.md` records why. The pilot may change
  how you measure, never what or which way (`newlife-prereg` rule one, second half).
  Ledgers written before this stay green.
- **Rule seven is enforced, not described.** 0.1.2's note said `newlife.gates.judgement_design`
  refuses a freeze; nothing called it. The freeze now reads `prereg.md`'s
  `@reproduction_class` anchor: `seeded` or `stochastic` must have a `judgement-design.json`
  whose N re-derives from its premises, and the freeze pins that file with the criteria;
  `deterministic`, or an anchor left as the template's placeholder, is treated as S0 as
  written and said aloud at the freeze. `newlife check` reports the same gate for those
  classes.
- The environment-drift refusal names the interpreter the pilot ran under and the one
  freezing, because two newlife installations on one machine are the usual cause; the
  ledger records `python`.

### Removed

- **`newlife check`.** Its two scans of the runner (criteria true by construction, parse
  failures that fall back to a default) now run inside `newlife freeze` and refuse it — a
  vacuous criterion frozen costs the round, so the check belongs before the irreversible
  step. Its unit-alignment check runs inside `newlife run`, after the verdict, where the
  artifact it needs exists. Nothing is advisory any more; every check has one moment.

### Changed

- The freeze lists files under `data/` it is not pinning, so a dataset the verdict reads
  and nobody pinned leaves a trace; it does not refuse.
- The environment-drift refusal says that a short pilot on a few configurations is enough
  after installing a package: coverage is the union of every pilot, the check reads only
  the latest.
- `newlife-prereg`: rule five is a checklist line (`run` enforces it); rule seven keeps the
  class declaration and points at `references/design.md` for the six questions behind the
  repetition count; the anchors that waive or record are listed in one table.
- `newlife-prereg` and `newlife-goal` keep rules and checklists in `SKILL.md`; the cases,
  measurements and limits behind them moved to `references/` (`cases.md`, `evidence.md`),
  which ship in the wheel and install with the skill.
- The gate modules are not standalone files any more: their selftests run as
  `python -m newlife.gates.<name> --selftest` (CI does), and the shebangs are gone.

### Fixed

- An unused import in `newlife.stochastic.design`.
- `NEXT.md` went stale after an upgrade: `newlife start` never touched an existing one, so
  a research repository kept guidance naming commands that no longer existed. The template
  now opens with a marker, and `start` rewrites a `NEXT.md` that carries it when it differs
  from the current template; a file without the marker is a person's own and is left alone.

## 0.1.2 — 2026-09-06

### Added

- **The freeze now refuses when the environment changed after the last pilot.**
  `newlife pilot` records a digest of the live environment in `pilot/ledger.jsonl`, and the
  pilot gate compares it with the environment at the freeze. Installing a package in
  between used to be invisible: the freeze rewrites `env.lock` from the new environment, so
  S1 went green against an environment in which the runner had **never once been
  executed** — and the discovery came at run time, after the one irreversible step, when
  repairing the environment would itself turn S1 red. A ledger written before this existed
  carries no digest and stays green, so registrations already in flight can still freeze.

- **Rule seven now says where the repetition count comes from** — and it is not a number
  anyone can hand you. Six questions must be answered before freezing (in
  `judgement-design.json`, pinned with `--data` so it is as immutable as the criteria), and
  `newlife.gates.judgement_design` refuses a freeze when they are unanswered **or when the
  declared N does not re-derive from the premises written beside it**. The order matters:
  the shape of the data chooses the statistic, and only then does the statistic choose N —
  the regular bootstrap fails on the mean of heavy-tailed samples, where a trimmed mean
  reached the target at n=64 and the mean never reached it within 256. N comes from a
  bootstrap power analysis running the very test you will judge with, never from
  `n = 2(z+z)²σ²/δ²`, which assumes normality and describes a t-test. **"Undecidable within
  this budget" is one of the answers**, and the first real use returned it. The gate never
  judges whether an effect size is worth caring about; it checks that a reason was given and
  that the arithmetic follows. **Scope is stated rather than implied**: two groups compared
  on a location statistic — not trends, not more than two groups, not slopes or proportions.
- **`newlife.stochastic.equivalence`**: one equivalence test, used in both directions, for
  worlds whose outcome differs every run. Two batches of the same configuration must come
  back equivalent; two genuinely different configurations must not — **the same test and
  the same threshold answer both**, because loosening it passes one end and tightening it
  passes the other, and using two tests is how that trade-off gets dodged. How many
  repetitions is not a constant in the code: the rule splits the batch in half and applies
  the same yardstick, so the data decides. Percentile bootstrap, no normality assumption,
  seeded — the judgement layer reproduces byte for byte even when the world does not.
  Bonferroni across sweep points, because "every point contains zero" is a conjunction and
  two points at 95% land near 90%.
- **A world now states which kind of reproduction it can offer** (`newlife-prereg` rule
  seven, plus an `@reproduction_class` line in the `prereg.md` template). S0 asks for a
  byte-identical rerun and a false S0 becomes `INVALID` — no conclusion at all, not a
  weaker one. That is right for a deterministic world and wrong for two others: a `seeded`
  world satisfies S0 by fixing its seed, which proves the seed was fixed and **not** that
  the conclusion survives a different one (so it owes a unit over a frozen set of seeds);
  a `stochastic` world — GPU reductions, concurrency, a remote service or model — cannot
  satisfy S0 at all, and must waive it on the record and judge over a distribution.
  Measured the same day: a runner whose simulator was an LLM behind an HTTP call went
  green on S0, S1 and all five audit arms, while swapping the model behind an unchanged
  `verdict.py` moved every number. **Whatever decides the result has to appear in the
  conjunction** — `env.lock` records installed distributions, not a model version, an
  endpoint, or an environment variable, and S0's inner run inherits `os.environ`.

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
