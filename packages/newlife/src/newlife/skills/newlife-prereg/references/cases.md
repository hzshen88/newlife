# Cases and measurements behind the rules

Every rule in `SKILL.md` came from a failure or a measurement. They are kept here so the
rules stay short; open this file when a rule needs its evidence.

## Rule one

### Failure six: the pilot had already answered the main criterion

- **Failure six**: a pilot run under this rule measured S3 — the fraction of
  narrow-interface modules in K562 — across 12 configurations, and every one fell inside
  the surrogate null. The first conjunct of H1 was thereby known to be false. Freezing it
  would have registered a question whose answer was already in hand: **it would have passed
  every gate and been worth nothing**, in direct conflict with the first line of
  `newlife-goal` §6 — *you genuinely do not know the answer while drafting.*

### Two moves in the "how" that flipped a reading

- **In a registered round**: swapping a random-gene-set null for a spectrum-preserving
  surrogate moved the reading from **0.8–1.0 to 0.0–0.077** — and at the time nobody knew
  that choice would flip the conclusion.
- **In an exploration one day later** (no criteria existed, so this is an illustration of
  the mechanism, not a seventh failure of this rule): a curve read as "regulon enrichment
  rises 21× → 70× once the low-rank layer is stripped" survived a shuffled null and **died
  against a spectrum-preserving one, which produced the same rising trend with no block
  structure at all**. The signal was real; the reading of the trend was not.

### Limits of rule one

Three gaps, worth stating rather than papering over:

- **Exit 1 has no landing place in the tooling.** `goal.md` §5's closeout is filled in after
  a freeze; a round that correctly stops before freezing currently leaves a `pilot/`
  directory and nothing that records what was concluded. Write it up by hand until that
  exists.
- **Blind data is not a blind analyst.** Exit 2 keeps the *data* unread, but after seeing
  the first dataset your priors are already shaped by it — what you choose to measure next,
  which direction you expect, what size feels convincing. Clinical trials answer this with
  third-party analysis; at this scale there is no equivalent. Exit 2's conditions are
  therefore **necessary and not sufficient**, and the residual belongs in §5 as a stated
  limit of the conclusion.
- **The gate sees the anchors move, not whether the move was honest.** `newlife pilot`
  digests four `goal.md` anchors — `counterparty`, `attack_layer`, `decides`,
  `who_changes_behavior` — into `pilot/ledger.jsonl`, and the freeze refuses when they
  differ unless the change is recorded (`<!--@goal_changed: …-->`). What that buys is a
  trace: rewriting the bet after the pilot can no longer happen silently. What it cannot
  buy is judgement — a note saying "re-pointed at data never read" is checked for
  existence, never for truth. And a bet that shifted only in your head, with the anchors
  left untouched, is invisible to it.

## Rule seven

### The stochastic row, measured

**Why the `stochastic` row is not hypothetical.** A runner whose "simulator" is an LLM
behind an HTTP call was measured on 2026-09-06: at `temperature=0` the model is
byte-deterministic, so **S0 went green, S1 went green, and `newlife audit` returned PASS on
all five arms** — while swapping the model behind the same unchanged `verdict.py` moved the
data from `[-10.0, -1.5, -1.2, -1.25]` to `[-1.0, -1.0, -12.5, -12.5]`. Every check was
green and nothing recorded the thing that decided the answer.

### Heavy tails and the trimmed mean

Measured on synthetic heavy-tailed data: a trimmed mean reached the target with n=64 while
the mean never reached it within a budget of 256. The regular bootstrap fails to estimate
the distribution of a sample mean under heavy tails; robust locations keep their power there.

### "Undecidable within this budget", on first use

It happened on the first real
use: judging one LLM against another at one order of magnitude needed more than 64 calls at
two seconds each, so the method said so instead of returning a number that would have looked
fine. That output tells you what the question would cost — which is more than a wrong N
tells you.

## Rule five (now a line in the checklist)

    the registration says  verdict = S0 ∧ S1 ∧ S2 ∧ S3
    the runner computed only three — **and nobody would notice**

The conjunction is one unit weaker than it looks. Check the reverse too: **a unit in the
artifact that the registration never declared** is a criterion added after the fact.

`newlife run` checks this after the verdict. **It caught a real misalignment the
first time it ran.**
