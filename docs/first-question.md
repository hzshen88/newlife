# Your first NewLife question

NewLife helps you turn a curiosity into a question whose answer can be checked later. You
talk to your AI; it reads the repository and runs the commands. You make the few decisions
that cannot be recovered from files.

The first useful feedback should take minutes. A defensible result takes as long as the
question requires.

## 1. Start with one sentence

```bash
python -m pip install newlife
newlife start my-research
```

Open `my-research` in an AI tool that reads skills and say:

> Explore this with me: would a small sign error change the model's conclusion?

You do not need to choose a workflow or know a command. The AI first explores what “small”,
“sign error” and “change the conclusion” could mean. It keeps the map in the repository so
a later session can resume it.

## 2. The first useful answer is a sharper question

A good response does not immediately build a simulation. It identifies the decision that
the result would change and the person who could reasonably expect the opposite result.

For example:

> The current question is too broad. There are two different claims:
>
> 1. any output changes after a 5% sign flip;
> 2. the majority decision changes after a 5% sign flip.
>
> Only the second would change whether the model is trusted for this decision. Which claim
> do you want to test?

The AI asks one consequential question at a time. Once the boundary is clear, it creates a
question folder and records where the question came from.

## 3. Decide what would count as an answer

Before looking at the answer, NewLife helps write:

- the claim and the counterclaim;
- the observable and control;
- the exact result that would turn the claim red;
- who changes which decision;
- the important boundary the result will not establish.

This becomes `goal.md`. The file begins deliberately incomplete: NewLife refuses to freeze
a question whose decision or counterparty is still vague.

The AI then implements the world in `verdict.py` and runs a pilot. A pilot tests whether the
measurement works; it does not spend the blind result.

```text
Pilot completed
  seen       S0 S1 S2 S3
  withheld  H1
```

`seen` means the value appeared in a pilot artifact. `withheld` means only the unit's name
was recorded; its value was not emitted. A unit cannot be both. If the runner crashes, the
attempt is kept for diagnosis but is not entered in the pilot ledger.

The pilot may change how a quantity is measured. It may not change the direction of the
hypothesis after revealing the answer. If the pilot already answers the main question, the
honest result is an exploratory closeout in `goal.md`, with no freeze.

## 4. Review the one irreversible decision

When the goal, pilot and criteria agree, the AI shows a short review rather than reading the
whole registration aloud:

```text
Ready to freeze

Question: does a 5% sign flip change the majority decision?
Seen: measurement checks S0-S3
Still blind: H1 and the second simulation seed
Expected work: 8 conditions, about 6 hours
After freezing: the hypothesis, thresholds and decision rule cannot change

Decision needed: freeze this question now?
```

Only the person can approve the freeze. If approved, the AI runs:

```bash
newlife freeze questions/<slug>
```

The freeze is a Git commit. Its ancestry is the proof that the prediction existed before
the result.

## 5. Leave and come back without reconstructing the history

At any time, ask:

> Where are we?

The AI runs `newlife status`. With no folder, it shows only questions that need a decision,
continued work or repair and summarizes completed work:

```text
YOUR DECISION
  sign-flip — ready to freeze
    next: review the frozen question, then freeze if you agree

NEEDS REPAIR
  old-question — audit failed
    why: one frozen input changed after the freeze

DONE  12 — 9 complete · 3 exploratory closed
```

For one question it reports four things:

```text
state      run
trust      registration frozen; no verdict yet
next       newlife run
```

Status reads Git history before today's templates. A valid older question does not move
backwards merely because it predates `goal.md`.

## 6. Run, audit and close

After the freeze, the AI follows the frozen implementation. H1, H0 and INVALID are
scientific outcomes written into the artifact; all are complete runs and exit zero. A
non-zero process exit means the execution is incomplete, never “the hypothesis lost”.

When results exist, the person separately decides whether to commit that exact result set.
After the commit, `newlife audit` checks from Git history that:

- the freeze commit and stamped hash agree;
- the registration was not edited after the freeze;
- committed outputs post-date the freeze;
- pinned environment and input files still match.

The verdict and goal closeout remain separate. H1 can fail to achieve the practical goal;
H0 can still buy a useful boundary. The closeout records that judgement in `goal.md` §5.

## Command reference

The AI normally runs these for you:

```bash
newlife status                            # workspace: what needs attention
newlife status questions/<slug>           # one question: state, trust, next step
newlife init <slug>                       # scaffold a formal question
newlife pilot questions/<slug>            # exercise measurements before the freeze
newlife freeze questions/<slug>           # irreversible registration commit
newlife run questions/<slug>              # compute the frozen verdict
newlife audit questions/<slug>            # verify freeze and result chronology
```

Never use `git add -A` before the freeze. `newlife init` commits the scaffold and leaves
`prereg.md` uncommitted because the freeze must be that file's first commit.
