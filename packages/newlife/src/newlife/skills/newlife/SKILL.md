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
   Six anchors go into `goal.md`. An anchor they cannot fill means the question is not
   worth asking — say so; dropping it here is cheap and allowed.
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

## "Where are we?" — read the folder, do not ask them

| What you find | Step | What you say and do |
|---|---|---|
| no `NEXT.md`, or not a git repository | setup | "Setting this up as a research repository" — exloop bootstrap |
| no `questions/<slug>/` for this topic | 1–2 | still exploring; or propose the handoff if a boundary is decidable |
| `goal.md` with `TODO` anchors | 3 | ask the three questions, fill the anchors |
| no `pilot/ledger.jsonl` | 4 | write the world, run `newlife pilot` |
| `prereg.md` says `Frozen at commit: _pending_` | 5–6 | write the criteria; ask; freeze |
| no `results/summary.json` | 7 | run, check |
| `results/summary.json` present | closeout | report the verdict; fill `goal.md` §5; mark the map |

Say the step in one sentence, then what you are about to do. `NEXT.md` in the repository
carries the same loop for the person to read.

## What does not belong here

Skills for developing newlife itself (an author's `newlife-milestone`, with a
two-repository layout) do not apply to a research repository laid out as
`questions/<slug>/`. Do not import their path tables.

## Setup, if they ask how to install

`pip install newlife` (it brings `exloop`), then `newlife start .` in their research
folder, which also installs these skills into every AI tool on the machine. You can do
all of that for them; the exploration skill says how.
