---
name: newlife
description: Use when the person asks how newlife or exloop works, how to use it, where to start, what happens next, or which step a question is at. Answer in terms of what they say and decide — never a table of shell commands; the assistant runs every command. Also the router to the three stage skills (exloop, newlife-goal, newlife-prereg). Not for doing a stage's work; that is the stage skill.
---

# newlife — how this works, said for the person

## The one rule for answering "how do I use this"

**The person never types a command. You do.** When they ask how it works, where to start,
what comes next, or where they are, answer with what *they* will say and decide and what
*you* will do for them. Do not print the CLI table; `newlife init / pilot / freeze / run /
check / audit` and exloop's `archive / handoff` are your instruments, documented in the
stage skills, and a person who sees them listed reasonably concludes they are expected to
type them. This exact misreading has happened.

## What the person does, in their words

1. **They say "Explore this with me: X".** The `exloop` skill: you ask one or two honing
   questions, walk one edge at a time, keep the map silently, offer reachable directions.
   They answer and decide. First time in a repository, you also do the setup (that skill's
   bootstrap section): install `newlife` if missing, run `newlife start .`.
2. **You notice a boundary has become decidable** — they can say what measurement would
   make the answer different. You say so once; if they say yes, you run `newlife init` and
   `handoff`. They see: a question folder exists, with the exploration record in `origin/`.
3. **You ask them three things the map cannot supply** (`newlife-goal`): who would bet the
   other way, is the answer settled by design or by running, who changes what they do.
   Six anchors go into `goal.md`. An anchor they cannot fill **yet** is not a verdict
   on them or on the question: offer two or three candidate wordings, or narrow the
   question, or go back to exploring exactly that gap — all normal exits. Only when,
   after that, nobody can be named who would bet the other way or change a decision is
   the question not worth freezing; say so plainly, and that keeping it as a curiosity
   is a fine outcome. Reproducing a known result to learn the toolchain is legitimate
   too: waive the goal gate on the record and label the verdict a reproduction.
4. **You write the world with them** into `verdict.py` and run `newlife pilot`. They see
   numbers; everything seen is now *seen*.
5. **You write the criteria with them** (`newlife-prereg`): every row marked seen / blind /
   mechanical; they choose the blind one.
6. **You ask before freezing. They say yes. You run `newlife freeze`.** The one
   irreversible step. Two gates (goal, pilot) refuse on their own if something is missing;
   you relay the reason in their words.
7. **You run the verdict**, `check`, commit `results/` (ask first), `audit`, and report
   H1 / H0 / INVALID with the five gates. The closeout goes into `goal.md` §5 and the map.

Two moments are theirs alone: the freeze, and committing results.

## How you ask, whichever stage

- Restate what you already understood before asking anything; do not ask twice.
- One question at a time, and say what it decides ("this fixes which rows can be blind").
- When they are stuck, offer concrete candidate phrasings and the difference between them.
- "Hold this", "keep exploring", "narrow it" are normal exits, not failures. A clearer
  question is a fine result of a first session.

## "Where are we?" — run `newlife status`, do not ask them and do not guess

For each folder under `questions/`, run `newlife status <folder>` and relay what it says:
the stage, what is done, what blocks, what comes next, and what the person has to decide.
It reads the folder the way the gates do, and it knows the one case a glance gets wrong —
`results/summary.json` present but `reproduction.json` missing is a run that died before
the self-reproduction, not a verdict.

Before any question exists: no `NEXT.md` or not a git repository means setup (the exloop
skill's bootstrap section); a repository with `NEXT.md` and no `questions/` means still
exploring, or a boundary ready to hand off.

Say the stage in one sentence, then what you are about to do. `NEXT.md` in the repository
carries the same loop for the person to read.

## What does not belong here

Skills for developing newlife itself (an author's `newlife-milestone`, with a
two-repository layout) do not apply to a research repository laid out as
`questions/<slug>/`. Do not import their path tables.

## Setup, if they ask how to install

`pip install newlife`, then `newlife start .` in their research folder, which also
installs these skills into every AI tool on the machine. The exploration skill ships in
the `exloop` package, a dependency of newlife, so the same install brings it; if it is
somehow missing, `start` says so and exits non-zero, and `pip install exloop` repairs it. You can do all of that for them; the exploration skill says how.
