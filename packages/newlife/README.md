# newlife

**A preregistration harness for simulation.** Freeze what would count as an answer
*before* you run anything; let the machine — not your judgement after the fact —
decide whether the criteria were met.

## Install

Requires Python 3.12 or newer and `git`.

```bash
python -m pip install newlife
# Optional simulation backends:
python -m pip install "newlife[process-bigraph]"
python -m pip install "newlife[spatio-flux]"
```

Start in your own repository:

```bash
mkdir my-research && cd my-research
git init
git config user.name "Your Name"
git config user.email "you@example.com"
newlife init 2026-09-05-my-question   # scaffold a question folder; commits it,
                                      # deliberately leaving prereg.md uncommitted
$EDITOR questions/2026-09-05-my-question/prereg.md
newlife freeze questions/2026-09-05-my-question
$EDITOR questions/2026-09-05-my-question/verdict.py
newlife run questions/2026-09-05-my-question
newlife check questions/2026-09-05-my-question
git add questions/2026-09-05-my-question/results
git commit -m "record verdict"
newlife audit questions/2026-09-05-my-question
```

`audit` proves, from commit ancestry rather than forgeable dates: the registration has a
freeze commit, the stamped hash matches it, the content was never edited afterwards, and
**every committed output post-dates the freeze**. Questions are siblings, not a chain:
a question's verdict never runs another question's runner.

## What the contract layer does

`BiologicalProfile` enforces four contracts — `StateClaim`, `MechanismSpec`, `Effect`,
`Resolver`. A mechanism declares which paths it owns and which effects it may emit;
writing anywhere else raises `newlife.core.errors.CommitAuthorityError` **from the
contract layer, not from your solver**. That distinction is load-bearing: "an exception
was raised" is not the same as "the contract stopped it", and a negative control that
conflates them proves nothing.

Third-party simulation processes are admitted unmodified. Verified against
`process-bigraph`'s own processes, `spatio-flux` (Monod kinetics, dynamic FBA behind a
GLPK solver), and a hand-wrapped `tellurium` ODE model — trajectories byte-identical to
running the same code without newlife.

## Gates that ship with it

`newlife check` runs three checks against your files: criteria that are **true by
construction** (a comprehension iterating a named constant while discarding the loop
variable is a repetition, not a sweep); parse failures that **silently fall back to a
convenient default**; and whether the units your registration declares are exactly the
units your runner computes. Each of the three was written after that exact defect shipped
undetected — the third one caught a real misalignment the first time it ran.

Also included: `newlife skills install` puts two AI skills (shaping a question into a
decidable one; writing a registration that will not veto itself) where your assistant
reads them.

`proofroot` is installed transitively and supplies RNG stream derivation, canonical
serialization, and the evidence-tier vocabulary.

Source, design rationale, and the record of every milestone judged so far:
<https://github.com/hzshen88/newlife>
