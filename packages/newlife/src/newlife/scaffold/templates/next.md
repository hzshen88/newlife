# What happens from here

This is a research repository. Everything from here on is a conversation with your AI
tool — Claude Code, Codex, or anything that reads `SKILL.md` files. The skills that
`newlife start` installed tell the AI when to run which command; you decide, it types.
Begin with one sentence:

    "Explore this with me: <your curiosity>"

Lost at any point? Ask your AI "how does this work" or "which step are we at": the
`newlife` skill answers in your terms, and `newlife status <folder>` is how it reads the
answer off this repository — stage, what is done, what blocks, what you have to decide.

## The loop

1. **Explore** (skill: exloop). The AI asks one or two honing questions, then
   walks one edge at a time, keeps a map silently, and offers reachable directions at the
   end of each turn. You only answer and decide. While it runs, the record lives in
   `~/.exloop/explorations/<slug>/` and follows you across tools; when it closes, the AI
   archives it into `explorations/<slug>/` in this repository, next to `questions/`.
2. **Hand off.** When a boundary can be stated as "what measurement would make the answer
   different", the AI says so once and asks. If you agree, it runs `newlife init <slug>`
   and `handoff`; `questions/<slug>/origin/` then holds the map and a pre-filled goal draft.
3. **Triage** (skill: newlife-goal). The AI asks only what the map cannot supply: who
   would bet the other way, is the answer settled by the design or by the run, who changes
   what they do. Six anchors go into `goal.md`. An anchor you cannot fill is the signal to
   drop the question — that is allowed, and cheap here.
4. **World and pilot.** Your simulator goes into `verdict.py`. `newlife pilot` runs it into
   `pilot/`, never `results/`. Everything a pilot produces counts as seen.
5. **Criteria** (skill: newlife-prereg). Every row of `prereg.md` §2 is marked seen /
   blind / mechanical, and at least one row is blind.
6. **Freeze.** The one irreversible step. The AI must ask you first, then runs
   `newlife freeze`. Two gates (goal, pilot) refuse on their own if something is missing.
7. **Verdict.** `newlife run`, `newlife check`, commit `results/`, `newlife audit`. H1, H0 or
   INVALID, with five gates reported. The closeout goes back into `goal.md` §5 and the map.

## The two moments that are yours alone

- **The freeze** (step 6). After it the criteria cannot change; a wrong criterion means a
  new registration, never an edit.
- **Committing `results/`** (step 7). What is committed provably post-dates the freeze.

## If you would rather type

    newlife init <slug>        newlife pilot <folder>       newlife freeze <folder> [--data FILE...]
    newlife run <folder>       newlife status <folder>      newlife check <folder>
    newlife audit <folder>     newlife skills install       newlife blocks

Never `git add -A` before the freeze: `prereg.md` must be committed by the freeze itself,
and `newlife init` leaves exactly that file uncommitted for that reason.
