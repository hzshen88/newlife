---
name: newlife-prereg
description: Help the user write a preregistration whose criteria will not sabotage themselves, then freeze it. Use when the question is already clear and they are writing prereg.md, fixing H1/H0 and the judgement units, or about to run `newlife freeze`. The core rule is "pilot before freezing, covering every quantity that appears in a criterion". Not for a question that has not taken shape yet (that is newlife-goal), and not for ordinary code changes.
---

# newlife-prereg — writing criteria that will not sabotage themselves

> **Commands in this file are for you, the assistant, to run; the person decides.**
> Asked how this works or where they are, describe what *they* do — see the `newlife` skill.

Once frozen, criteria cannot be changed. **Something unchangeable that is wrong costs you
the whole round.**

Every rule below comes from an actual failure, not from general advice.
**Three judgements, two of them thrown out because of a defect in the criteria
themselves — while the science underneath was right both times.**

---

## Rule one: the pilot must cover **every** quantity a criterion names — and may change only **how** they are measured

**Not most of them.**

- **Failure one**: an integration window of `t=5.0` was frozen with no pilot run at all.
  The two models' steady states differed by 1.8% while the criterion demanded <1e-3 →
  invalid. **A two-second run would have found it.**
- **Failure two**: a pilot *was* run — t½ and steady states were checked — but
  **only one trajectory's "distinct value count" was looked at (401/401) before writing a
  criterion about "every trajectory"**. The other model's increments underflowed to zero
  after convergence, giving 177/401 → invalid.

**How**: read the pass-condition of every row in the criteria table word for word and list
every measurable quantity in it. For each one ask: **have I actually run this and looked at
the number?** If not, either measure it now or delete that criterion.

`newlife pilot <folder>` is how you look: it runs the runner into `pilot/<stamp>/` (never
`results/`) and appends the units it produced to `pilot/ledger.jsonl`. **The freeze reads
that ledger** — a row marked `seen` with no run behind it is refused. Anything that came in
through `origin/` (the exploration's record) is seen as well, even though no ledger line
says so.

> **"I derived it, so I know" does not count as having looked.** Numerical integration,
> floating point and discrete timesteps all get a vote.

### What the pilot is entitled to move

Obeying the paragraph above means that sooner or later you will look at the quantity the
whole question turns on, and know the answer before anything is frozen. **That is not a
corner case to be patched; it is the normal consequence of doing rule one properly**, and
it is why this rule has a second half.

Two cuts, and you need both:

**Which values.** The pilot exercises the *measurement*: the method, its numerical
stability, the run conditions, the order of magnitude of every quantity a criterion names.
What stays unrun until after the freeze is the *test*: the parameter values, seeds or data
subsets the confirmatory claim will be judged on. Piloting the measurement on other values
is looking; piloting it on the values you are about to freeze is peeking. (This is also
where rule three's blind unit comes from.)

**Which parts of the question.** Independently of the values:

| | Examples | After the pilot |
|---|---|---|
| **what you measure, and which way you expect it** | H1's direction, the counterparty, which mutation would turn it red (`newlife-goal` §3, piece 4) | **fixed.** Changing it after seeing the pilot is HARKing, however reasonable the reason sounds |
| **how you measure** | the statistic, the construction of the null, the sweep range of a nuisance parameter, regularisation strength | **must be free to move** — calibrating this is what the pilot is *for* |
| **where the line falls** | thresholds, N, power | **the pilot fixes the value; how it would be fixed was written down beforehand** (rule seven, M1–M6) |

> **One line: the pilot may change how you measure, not what you measure or which way you
> expect it to go.**

This is why `goal.md` is written *before* the pilot rather than after. Its six anchors and
its four pieces are the row-one commitments; the pilot is not entitled to any of them.

### When the pilot has already answered the main criterion

- **Failure six**: a pilot run under this rule measured S3 — the fraction of
  narrow-interface modules in K562 — across 12 configurations, and every one fell inside
  the surrogate null. The first conjunct of H1 was thereby known to be false. Freezing it
  would have registered a question whose answer was already in hand: **it would have passed
  every gate and been worth nothing**, in direct conflict with the first line of
  `newlife-goal` §6 — *you genuinely do not know the answer while drafting.*

Three legitimate exits, cheapest first:

1. **Report it as an exploratory negative result and do not freeze.** A round that ends
   here is not a failed round; it cost one pilot and it produced a real answer.
2. **Keep H1's direction and re-point it at data that has never been read.** Conditions: the
   new criterion may use only quantities never yet computed, and it must not be the very
   difference the re-pointing was made to produce. If H1 has become **"no effect
   reproduces"**, it owes a **power demonstration** — a blunt instrument reproduces a null
   trivially.
3. **Fall back to a secondary hypothesis already written in `goal.md` before the pilot** —
   not one thought of now.

**Illegitimate, and it is the only one**: seeing the pilot, flipping H1, and freezing it on
the same data.

At closeout, **"we confirmed A" and "A was chosen after seeing B" are two sentences.** They
may not be merged, and the second does not disappear because the first is true.

### Moving the "how" is not free either

- **In a registered round**: swapping a random-gene-set null for a spectrum-preserving
  surrogate moved the reading from **0.8–1.0 to 0.0–0.077** — and at the time nobody knew
  that choice would flip the conclusion.
- **In an exploration one day later** (no criteria existed, so this is an illustration of
  the mechanism, not a seventh failure of this rule): a curve read as "regulon enrichment
  rises 21× → 70× once the low-rank layer is stripped" survived a shuffled null and **died
  against a spectrum-preserving one, which produced the same rising trend with no block
  structure at all**. The signal was real; the reading of the trend was not.

So every move in the "how" row owes two things:

- **a record** — which null, which statistic, and the reading before and after; it goes in §0
- **a two-sided check at the real data scale** — no false alarm on structureless data
  (≤ 2× nominal) *and* detects a planted structure (> 4×). One direction is not a check, and
  a pass at 1200×600 does not transfer to 11258×2000.

### What this rule does not protect you from

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

---

## Rule two: hygiene checks belong in the **invalidation conditions**, not the conjunction

Criteria say whether the hypothesis holds. Invalidation conditions say whether the run
counts at all. **Merge them and one mechanical check can veto a scientifically successful
run.**

- **Failure three**: a "did the timestep take effect" hygiene check was placed in both the
  conjunction and the invalidation set. It failed on perfectly legitimate data (the model
  had converged), **vetoing a round in which every scientific unit held.**

**The test**: ask "could this go red on a run in which **the hypothesis is true and the
measurement is sound**?"
- yes → it is measuring the run, not the hypothesis: a hygiene check; move it to IC, or drop it
- no → it is a scientific criterion and may enter the conjunction

A scientific criterion also fails on perfectly normal data — when the hypothesis is false.
That is H0, not hygiene. The question is never *whether* it can fail but what a failure
would **mean**: "the claim is wrong" or "this run cannot be interpreted".

**Corollary**: **do not write a question-level criterion for something the library already
hard-fails on.** Adding your own check for a bug you just fixed is handing yourself a veto.

---

## Rule three: a confirmatory round must keep one unit genuinely **blind**

When reproducing a known result, the criteria tend to confirm numbers you have already
seen — and then the round carries no information.

**How**: add a "Piloted?" column to the criteria table and mark every row
`seen` / `blind` / `mechanical`. **Keep at least one dimension you have never run.**
The freeze refuses a table with no `blind` row; if this round genuinely has nothing blind,
waive it on the record with `<!--@pilot_gate: no_blind_waived — why-->` inside `prereg.md`.
Common blind dimensions: change a parameter, change a scale, extrapolate one step out
rather than interpolate.

- **A positive example**: six of eight units had been seen before drafting; only the decay
  rate had never been swept. The two blind criteria (the gap shrinks with the rate; the
  ratio is independent of it) were **both derived from the structure of the model**, and
  both held. **All of that round's information was in those two units.**

Derive the blind unit **from the mechanism**; do not guess. Put the derivation in §1 of the
registration, so that it means something when it holds and you know which step was wrong
when it does not.

---

## Rule four: every criterion must **prove it can go red**

**A criterion that is true by construction never goes red, and people only investigate what
is red.**

- **Failure four**: a negative control written as `[f(x) for _ in SWEEP]` — the loop
  variable was discarded, so five runs of the same configuration were compared with each
  other. True under any configuration, **and it sat inside the conjunction for an entire
  milestone.**
- **Failure five**: the self-proof was written `a > b is False`. In Python that is the
  chained comparison `(a > b) and (b is False)` — **always false**. The "this criterion can
  fail" slot was itself broken.

**How**: write each criterion as a **pure predicate** (taking numbers, running no
simulation), then have the runner feed it synthetic counterexamples at runtime and confirm
it returns false. **Write each demonstration as an independent statement** — no chained
comparisons.

Run `newlife check` — its vacuous-criterion scan catches the first kind.

---

## Rule five: the unit names must match the runner's keys, one for one

    the registration says  verdict = S0 ∧ S1 ∧ S2 ∧ S3
    the runner computed only three — **and nobody would notice**

The conjunction is one unit weaker than it looks. Check the reverse too: **a unit in the
artifact that the registration never declared** is a criterion added after the fact.

The unit-alignment gate in `newlife check` checks this. **It caught a real misalignment the
first time it ran.**

---

## Rule six: a third-party process needs a hand-written declaration, and one half of it the pilot cannot check

Admitting a third-party `process_bigraph` `Process` is **not** "install it and it runs".
`admit()` requires a `PortBinding` table and a `lowering` map, written by hand, for every
foreign process — there is no exception and no autodetection. Two of the things that table
must state are things the third party **does not provide**:

- **which state path a port writes to** — `outputs()` gives a type (`'float'`), never a location
- **whether the write is `add` or `set`** — a process returning an increment cannot say so
  in its signature

The first half is safe: writing a port that was never declared **hard-fails** in `admit`.
The second half is not.

> **Getting `add`/`set` backwards never raises.** `set` where `add` was meant overwrites
> the quantity with the increment, and the run still produces results — plausible numbers,
> in the right units, monotone where you expected monotone. **The pilot sees those numbers
> and reports them as covered.** Rule one does not protect you here: the quantity *was*
> piloted; it was piloted wrong.

**How to decide, every time**: read what the foreign `update` returns. Does it return the
new absolute value, or the change since the last step? `docs/writing-a-world.md` shows
`PortBinding("species", ("species",), "add")` — correct **there** because that Tellurium
wrapper returns `float(self.rr[n]) - float(state["species"][n])`, a difference. **Copying
that line to wrap a simulator that returns absolute values is the same error in reverse.**
Say out loud which of the two the process returns, and say it before writing the binding.

Nothing downstream catches this — not `admit`, not the pilot, not the five gates. What can
catch it is a criterion you write on purpose: a conserved total that must stay conserved
when there is no source or sink, or a unit check that an increment and a level cannot both
be right. **If a foreign process is in the composite, one such criterion belongs in the
conjunction.**

**Install before you freeze.** `env.lock` records every distribution in the environment at
the freeze, and S1 re-reads the live environment at run time and compares the file
character by character. Installing anything after the freeze — including a dependency you
discover you need while wiring a foreign process — **turns S1 red**. Get the third party
installed, admitted and piloted first; the freeze rewrites `env.lock` from the live
environment and pins it.

---

## Rule seven: say which kind of reproduction your world can offer, before S0 decides for you

S0 asks for a byte-identical rerun, and `verdict.py` turns a false S0 into `INVALID` — not
a weaker conclusion, **no conclusion**. That is right for a deterministic world and wrong
for two other kinds, so state which one you are in.

| Class | Your world | What S0 buys, and what you owe |
|---|---|---|
| `deterministic` | same inputs, same bytes | S0 as written; nothing to add |
| `seeded` | random, but the seed is a recorded input | S0 still holds — **and it is not enough**. Add a unit: **the verdict is unchanged across a frozen set of seeds** |
| `stochastic` | varies run to run with no seed in control — GPU reductions, concurrency, a remote service or model | **S0 cannot hold.** Waive it on the record with a reason, and judge over a *distribution*: N repetitions, N frozen in the registration |

> **A green S0 on a seeded world proves the seed was fixed, not that the conclusion
> survives a different one.** Those are different claims and only one of them is science.

### How many repetitions — and it is not a number anyone can give you

`seeded` and `stochastic` both owe a repetition count, and **there is no rule that supplies
it**. It depends on the effect you care about, on the shape of your noise, and on what a
sample costs you — all three differ per question. What can be given is the sequence of
questions whose answers determine it, and a gate that refuses when they are unanswered.

**Answer these before freezing** (they go in `judgement-design.json` beside the
registration; freeze it with `--data` so it is as immutable as the criteria):

| | | Why it cannot be skipped |
|---|---|---|
| **M1** | The **effect worth detecting**, in your quantity's own units | Without a target, a convergence rule has nothing to aim at and ends up asking a proxy |
| **M2** | Which **location statistic** is compared, and which estimates spread — **plus why it suits your data's shape** | The heaviest-consequence answer of the six; see below |
| **M3** | The false-alarm and miss rates you accept | "It could not be detected" is uninterpretable without them |
| **M4** | How N follows from M1–M3 | So a reader can re-derive it rather than take it |
| **M5** | The budget past which you declare the question **undecidable for now** | Without a ceiling the method returns a number nobody can run and nobody admits to |
| **M6** | Whether the data is heavy-tailed, and if so why M2 is still defensible | Measured, not asserted — the gate cross-checks it |

**The order matters: shape first, then statistic, then N.** The regular bootstrap fails to
estimate the distribution of a sample *mean* under heavy tails, while robust locations keep
their power there. Measured on synthetic heavy-tailed data: **a trimmed mean reached the
target with n=64 while the mean never reached it within a budget of 256.** Choosing the
statistic is not a matter of taste; it is the difference between decidable and not.

**Derive N by bootstrap power analysis, not by a formula.** `n = 2(z+z)²σ²/δ²` assumes
normality and equal variance and describes a t-test — three things that are typically false
here. Instead: take the pilot as an empirical distribution, shift it by the effect, and for
each candidate N run **the same test you will judge with**, counting how often it fires.
Take the smallest N that reaches your power. Multiple comparisons need no extra correction
because the real test already contains them.

**"Undecidable within this budget" is a correct answer.** It happened on the first real
use: judging one LLM against another at one order of magnitude needed more than 64 calls at
two seconds each, so the method said so instead of returning a number that would have looked
fine. That output tells you what the question would cost — which is more than a wrong N
tells you.

**What this covers, and what it does not.** The derivation above is for **two groups
compared on a location statistic**. It does **not** cover monotone trends, more than two
groups, slopes, proportions, or variance itself. That boundary is not academic: the
milestone that produced this method had, as its own scientific question, whether a quantity
rises monotonically — **a shape this method cannot judge.** Forcing such a question into a
two-group derivation yields a number unrelated to what is being asked.

`newlife.gates.judgement_design` checks two things: that the six answers are present with
their reasons, and that **the declared N re-derives from the premises stated next to it**.
It never judges whether an effect size is the right one to care about — that would need a
referee who understands the question better than the person asking, and there is none.

**Why the `stochastic` row is not hypothetical.** A runner whose "simulator" is an LLM
behind an HTTP call was measured on 2026-09-06: at `temperature=0` the model is
byte-deterministic, so **S0 went green, S1 went green, and `newlife audit` returned PASS on
all five arms** — while swapping the model behind the same unchanged `verdict.py` moved the
data from `[-10.0, -1.5, -1.2, -1.25]` to `[-1.0, -1.0, -12.5, -12.5]`. Every check was
green and nothing recorded the thing that decided the answer.

**So the rule has a second half**: whatever decides your result must be *named in the
conjunction*. `env.lock` records the distributions installed here — it knows nothing about a
model version, an endpoint, or an environment variable, and S0's inner run inherits
`os.environ`, so self-reproduction cannot see them either. If a remote service, a model
identity, or an env var can change your numbers, **put it in a unit**, or you have a
registration that passes every gate and rests on something nobody wrote down.

---

## Before freezing

- [ ] **run a pilot** covering every quantity that appears in a criterion (rule one) — `newlife pilot`; the freeze checks `pilot/ledger.jsonl`
- [ ] add the "Piloted?" column and mark every row; **confirm at least one is blind** (rule three)
- [ ] the pilot did **not** move H1's direction, the counterparty, or which mutation turns it
      red; every change to *how* you measure is recorded in §0 with the reading before and
      after, and the new instrument passed a two-sided check (rule one, second half)
- [ ] ask of each criterion "could it fail on normal data?"; move those that could into IC (rule two)
- [ ] ask of each criterion "what would make it go red?"; no answer means it is vacuous (rule four)
- [ ] write the criteria and the invalidation conditions **separately** — otherwise a
      disappointing result gets quietly reclassified as "the run didn't count"
- [ ] §5 states **what this round does not establish**; at closeout "we showed A" must never
      stand in for "B also holds"
- [ ] `git log -- <prereg path>` is empty — **the freeze must be its first commit**
- [ ] **the reproduction class is stated** (rule seven), and if it is `seeded` or
      `stochastic`, the unit that class obliges you to add is actually in the conjunction
- [ ] **everything the question needs is installed now** — S1 compares the live environment
      against `env.lock` character by character, so a package installed after the freeze
      turns it red (rule six)
- [ ] a third-party process in the composite? Then its `PortBinding` `add`/`set` was decided
      by reading what its `update` returns, **not by copying an example**, and a conserved
      total or unit check guards it in the conjunction (rule six)
- [ ] the question reads files it did not generate (a downloaded dataset, a reference
      network)? Then freeze with `--data <those files>`: their hashes go into the
      registration and `newlife audit` re-checks them. Record where each came from
      (URL, commit or version, date) in a small manifest next to the data — a raw URL on a
      moving branch is not a source, and `env.lock` knows nothing about data

**Ask the person before running it.** The freeze is the one irreversible step in the whole
flow: a wrong criterion afterwards means a new registration, never an edit. Say in one
sentence what is about to be frozen, and wait for a yes. Then:

```bash
newlife freeze questions/<slug>      # this commit IS the timestamp
```

**After the freeze**: the criteria cannot change. If the criteria themselves turn out to be
defective, the correct move is to **write a new registration** (`newlife init` with a new
slug) and **leave the old one INVALID exactly as it stands** — it is the record of how the
conclusion was reached, not a failed attempt to be tidied away. **Never re-freeze.**

---

## The shape of a registration

The `prereg.md` that `newlife init` generates already has it: §1 hypothesis · §2 judgement
units (mechanical conjunction) · §3 frozen implementation constraints · §4 invalidation
conditions · §5 boundary of the conclusion.

**Add a §0 saying what you had already seen while drafting** — every number already run.
This is not a confession; it is what lets a reader tell which units are confirmatory and
which are blind.
