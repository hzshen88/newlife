# Your first question, in about ten minutes

This walks one question from `pip install` to a passing audit. Every block of output below
is real: it was produced on 2026-09-06 in a fresh repository, with the paths shortened to
`~/my-research`. The "world" is the placeholder model that `newlife init` scaffolds, so the
verdict at the end says nothing about anything; what it shows is the mechanics, and where a
real question differs is said at each step.

You would not normally type any of this. The skills that `newlife start` installs tell
your AI when to run which command; you say what you want and decide at the two moments
that are yours. The commands are shown so that you can see what the AI is doing for you.

## 1. Start

```
$ python -m pip install newlife
$ newlife start my-research
  git init      ~/my-research
  wrote         ~/my-research/.gitignore
  wrote         ~/my-research/NEXT.md

Open ~/my-research in your AI tool (Claude Code, Codex, ...) and say:
    "Explore this with me: <your curiosity>"
The rest is conversation. NEXT.md in the repository says what happens from here.
```

`start` also copies the five skills into every AI tool directory it finds on the machine
(`~/.claude/skills`, `~/.codex/skills`, ...). Here they were already present and identical,
so nothing was printed for them.

A real question begins with that sentence: the `exloop` skill explores with you. If several
explanations fit, it invokes `idea-lab` inside the same conversation; this is not another
choice or worksheet for you. When a boundary becomes decidable, `exloop` hands the record
into the question folder's `origin/`. This walkthrough skips straight to the folder.

## 2. Scaffold a question

```
$ cd my-research
$ newlife init 2026-09-06-first-question
Created questions/2026-09-06-first-question/ — scaffold committed, prereg.md deliberately left uncommitted.
Next:
  0. edit questions/2026-09-06-first-question/goal.md — six anchors. **It is red on purpose** ...
  1. edit questions/2026-09-06-first-question/verdict.py and put your world in it (exploratory for now)
  2. newlife pilot questions/2026-09-06-first-question       <- look at every quantity a criterion will name
  3. edit questions/2026-09-06-first-question/prereg.md and write the criteria; mark every row seen / blind / mechanical
  4. newlife freeze questions/2026-09-06-first-question      <- do not commit prereg.md before this (never `git add -A` here)
  5. newlife run questions/2026-09-06-first-question && git add questions/2026-09-06-first-question/results && git commit
  6. newlife audit questions/2026-09-06-first-question
```

One folder per question. `goal.md`, `verdict.py`, `env.lock` and `origin/README.md` are
committed; `prereg.md` is not, because the freeze has to be that file's first commit.

## 3. Where am I?

```
$ newlife status questions/2026-09-06-first-question
~/my-research/questions/2026-09-06-first-question
  stage      goal  (not frozen)
  done       scaffold
  blocked    @evidence: literature_searched must be yes or no
             @counterparty is a placeholder or too short: 'TODO' — say what grounds the other side would bet on
             @decides must be design or run
             @attack_layer must be conclusion / premise / definition
             @who_changes_behavior is a placeholder or too short: 'TODO' — name the person and the decision
             @size_estimate is missing the numeric field impl_lines=
             @size_estimate is missing the numeric field criteria=
             @size_estimate is missing the numeric field failure_modes=
  next       fill the six anchors in goal.md with the newlife-goal skill — or waive the stage on the record
  decide     who would bet the other way, and on what grounds
             does the answer depend on the design or on running it
             who changes which decision because of the answer
  origin     empty — where did this question come from?
```

This is what your AI runs when you ask "which step are we at". It reads the folder the way
the gates do, so it cannot drift from them.

## 4. The freeze refuses until the goal is ready

```
$ newlife freeze questions/2026-09-06-first-question
The goal is ready: goal.md has all six (literature · counterparty · attack layer · design or run · who changes behaviour · size).
Pilot coverage: 4 unit(s) all marked, every seen unit has a run behind it, blind: none (waived on the record).
Reproduction class: not stated (prereg.md's @reproduction_class line is absent or still the template's placeholder) — treated as deterministic, S0 as written. Say `seeded` or `stochastic` there to have the repetition count checked (newlife-prereg rule seven).
scanned 1 file(s); no silent-degradation pattern found (R1 syntactic + R2 semantic + R3 swallowed)
FROZEN: questions/2026-09-06-first-question/prereg.md
  freeze commit: bbec18297cdc27d858c9cdc22a9a5f8268e599f2
  This commit is the timestamp proving the prediction preceded the result.
  From here on: any edit to this file, and any output committed at-or-before
  the freeze, will fail 'prereg.sh audit'.

$ git log --oneline
edbc48e prereg-stamp: questions/2026-09-06-first-question/prereg.md bbec18297cdc27d858c9cdc22a9a5f8268e599f2
bbec182 prereg-freeze: questions/2026-09-06-first-question/prereg.md
261570f question(2026-09-06-first-question): scaffold (prereg.md left uncommitted, awaiting freeze)
```

Two commits: the freeze itself, and a stamp that writes the freeze commit's hash back into
the file. Before it, the freeze said which reproduction class applies (none stated, so
deterministic) and scanned the runner for criteria true by construction and for silent
fallbacks. `env.lock` was rewritten from the live environment and pinned at this moment
(here it had not changed since the scaffold, so no extra commit appears). If a criterion
later turns out to be defective, the registration is left as it is and marked INVALID, and
a new folder is opened; it is never re-frozen.

The audit already has something to say, and it is careful about what it does not say:

```
$ newlife audit questions/2026-09-06-first-question
== prereg audit: questions/2026-09-06-first-question/prereg.md ==
PASS  FROZEN: first committed at bbec182 (2026-09-06)
PASS  STAMP: stamped hash matches the freeze commit
PASS  INTEGRITY: content unchanged since the freeze
WARN  CHRONOLOGY: NOT established -- no committed outputs examined under: questions/2026-09-06-first-question/results
      This audit says nothing about whether any result post-dates the freeze.
PASS  DATA: 1 frozen data checksum(s) verified

RESULT: PARTIAL (1 warning(s)) — the registration was never edited after the freeze.
$ echo $?
3
```

## 8. Verdict

```
$ newlife run questions/2026-09-06-first-question
  S1_env_unchanged                   True
  S2_increases_across_sweep          True
  S3_criteria_can_fail               True
  S0_byte_identical_on_rerun         True

verdict: H1

~/my-research/questions/2026-09-06-first-question: units aligned — 4 declared (S0 S1 S2 S3), every one present in the artifact.
```

H1, H0 or INVALID, computed by the runner from the frozen conjunction, never written by
hand. Here H1 means only that a placeholder function is increasing; in a real question it
means your blind prediction held.

```
$ newlife status questions/2026-09-06-first-question
  stage      verdict computed, not committed  (frozen at bbec18297cdc)
  verdict    H1
  next       commit results/ (only results/), then `newlife audit`
  decide     commit these results as the record of this question

```

The last line is the run checking that the units the registration declares are exactly the
units the runner computed; a conjunction one unit weaker than it reads is what that caught
the first time it ran on a real question.

The second moment that is yours: committing the results. Only `results/`, nothing else.

```
$ git add questions/2026-09-06-first-question/results
$ git commit -m "question(2026-09-06-first-question): verdict" -- questions/2026-09-06-first-question/results

$ newlife audit questions/2026-09-06-first-question
== prereg audit: questions/2026-09-06-first-question/prereg.md ==
PASS  FROZEN: first committed at bbec182 (2026-09-06)
PASS  STAMP: stamped hash matches the freeze commit
PASS  INTEGRITY: content unchanged since the freeze
PASS  CHRONOLOGY: every committed output post-dates the freeze (1 commit(s) examined)
PASS  DATA: 1 frozen data checksum(s) verified

RESULT: PASS (0 warning(s)) — freeze verified: predictions pre-date outputs and were never edited.
```

Everything the audit says comes from commit ancestry and hashes, not from dates anyone
typed. Anyone with a clone of your repository can run it.

## 9. Closeout

```
$ newlife status questions/2026-09-06-first-question
  stage      closeout  (frozen at bbec18297cdc)
  verdict    H1
  done       scaffold · goal ready · frozen at bbec18297cdc · verdict computed: H1 · results committed
  blocked    goal.md section 5 still holds the placeholder
  next       `newlife audit`; then the closeout judgement in goal.md section 5 (achieved / not_achieved / regressed / not_applicable) and a mark on the exploration map
  decide     was the goal achieved, regardless of the verdict
```

The last question is separate from the verdict: did this buy what the goal said it would?
That goes into `goal.md` §5 as one of `achieved / not_achieved / regressed /
not_applicable`, and a mark goes on the exploration map. A supported hypothesis with a
goal that went backwards is a legitimate, and recorded, outcome.

## What you have now

```
questions/2026-09-06-first-question/env.lock
questions/2026-09-06-first-question/goal.md
questions/2026-09-06-first-question/origin/README.md
questions/2026-09-06-first-question/pilot/20260906T010110Z/reproduction.json
questions/2026-09-06-first-question/pilot/20260906T010110Z/summary.json
questions/2026-09-06-first-question/pilot/ledger.jsonl
questions/2026-09-06-first-question/prereg.md
questions/2026-09-06-first-question/results/reproduction.json
questions/2026-09-06-first-question/results/summary.json
questions/2026-09-06-first-question/verdict.py
```

Four commits: scaffold, freeze, stamp, verdict. The next question is a sibling folder, not
a continuation: a question's verdict never runs another question's runner.

For a real question, start where this walkthrough skipped: open the repository in your AI
tool and say *"Explore this with me: …"*.
