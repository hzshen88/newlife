# newlife

**Turn a curiosity into a question that can be settled, freeze what would count as an
answer before running anything, and leave a verdict that can be audited from git alone.**

You talk to your AI; it runs the commands. Setup is two lines:

```bash
python -m pip install newlife
newlife start my-research
```

Then open `my-research` in Claude Code, Codex, or any AI tool that reads `SKILL.md` files,
and say:

> Explore this with me: *your curiosity*

`NEXT.md` in that folder says what happens from here. If you get lost, ask your AI "how does
this work" or "which step are we at" — the installed `newlife` skill answers in your terms.

Requires Python 3.12 or newer and `git` (the freeze is a git commit; that is what makes the
timestamp real). `start` tells you if git has no identity to sign with, rather than
guessing one.

## What happens, in your words

1. **Explore.** Your AI asks one or two honing questions, then walks one edge at a time and
   keeps a map silently. When several explanations fit, it uses idea-lab's
   Draw–Attack–Compare–Check reasoning inside the same conversation; you never choose a
   second workflow. You answer and decide. (`exloop` and `idea-lab` ship together in the
   `exloop` package; newlife depends on it, so the same install brings both.)
2. **Hand off.** When a boundary can be stated as "what measurement would make the answer
   different", the AI says so once. If you agree, a question folder appears with the
   exploration record inside it.
3. **Is it worth asking?** The AI asks only what the map cannot supply: who would bet the
   other way, is the answer settled by design or by running, who changes what they do.
   Six anchors go into `goal.md`. One you cannot fill yet means keep exploring or narrow —
   not a failure.
4. **World and pilot.** Your simulator goes into `verdict.py`; a pilot run shows you every
   quantity a criterion will name. Everything seen is now *seen*.
5. **Criteria.** Every judgement unit is marked seen / blind / mechanical, and at least one
   is blind — a confirmatory round in which every number was already seen carries no
   information.
6. **Freeze.** The one irreversible step; the AI asks you first. Two gates refuse on their
   own if the goal is unfilled or a criterion was never piloted. Your environment and any
   downloaded data are pinned by hash at this moment.
7. **Execute and close.** The execution skill resumes the real repository state, runs and
   verifies the frozen question, diagnoses anomalies without changing its rules, audits it,
   and delivers the report. H1, H0 or INVALID is computed by the runner, never written by
   hand. The AI asks separately before committing `results/`.

Two moments are yours alone: the freeze, and committing the results.

## What the record can prove afterwards

`newlife audit` shows, from commit ancestry rather than dates anyone could type: the
registration has a freeze commit; the stamped hash matches it; the criteria were never
edited afterwards; every committed output post-dates the freeze; and `env.lock` and every
pinned data file still hash to what was frozen. The runner's own units add the other half:
the run reproduces itself byte for byte, the packages installed at run time are exactly the
ones recorded, and every criterion proves at run time that it *can* go red.

A registration whose criteria turn out to be defective is left as `INVALID`, exactly as it
stands, and a new one is opened. Never re-frozen. That record is how a conclusion was
reached, not a failure to tidy away.

## If you would rather type

```
newlife init <slug>       newlife pilot <folder>      newlife freeze <folder> [--data FILE...]
newlife run <folder>      newlife status <folder>
newlife audit <folder>
newlife skills install    newlife skills path         newlife blocks
```

Never `git add -A` before the freeze: `prereg.md` must be committed by the freeze itself,
and `newlife init` leaves exactly that file uncommitted for that reason.

## Underneath

Optional simulation backends: `pip install "newlife[spatio-flux]"` (Monod kinetics, dynamic
FBA with GLPK, diffusion, particles) or `"newlife[process-bigraph]"` for the runtime alone;
`newlife blocks` lists what is installed. Third-party processes run unmodified inside a
declared contract — a mechanism says which state paths it owns and which effects it may
emit, and writing anywhere else is refused by the contract layer, not by your solver.
`proofroot` is installed transitively and supplies RNG stream derivation, canonical
serialization and the evidence-tier vocabulary.

Source, design rationale, and the record of every milestone judged so far:
<https://github.com/hzshen88/newlife>
