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

It happens (failure six, `references/cases.md`): the pilot showed the first conjunct of H1
to be false before anything was frozen, and freezing it would have passed every gate and
been worth nothing. Three legitimate exits, cheapest first:

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

A change of null or statistic can flip the reading on its own (two measured cases in
`references/cases.md`). So every move in the "how" row owes two things:

- **a record** — which null, which statistic, and the reading before and after; it goes in §0
- **a two-sided check at the real data scale** — no false alarm on structureless data
  (≤ 2× nominal) *and* detects a planted structure (> 4×). One direction is not a check, and
  a pass at 1200×600 does not transfer to 11258×2000.

### What this rule does not protect you from

Three limits, stated in `references/cases.md`. The one that changes what you write: exit 2
keeps the *data* unread, not the analyst — its conditions are necessary, not sufficient,
and the residual belongs in §5 as a stated limit of the conclusion.

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

The freeze runs a vacuous-criterion scan and refuses the first kind.

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

### How many repetitions

`seeded` and `stochastic` owe a repetition count, and **there is no rule that supplies it**:
it depends on the effect worth detecting, the shape of the noise and what a sample costs.
**Before writing `judgement-design.json`, read `references/design.md`** — the six questions
(M1–M6) whose answers determine N, why the statistic is chosen before N, why N comes from a
bootstrap power analysis and not a formula, and the scope (two groups compared on a
location statistic; not trends, not proportions, not more than two groups).

**The freeze runs this check** when the `@reproduction_class` anchor in `prereg.md` says
`seeded` or `stochastic`: the six answers must be present with their reasons, and **the
declared N must re-derive from the premises stated next to it**; the freeze pins
`judgement-design.json` with the criteria. It never judges whether an effect size is the
right one to care about — that would need a referee who understands the question better
than the person asking, and there is none. An anchor left as the template's placeholder is
treated as `deterministic`, and the freeze says so.

Measured on 2026-09-06 (`references/cases.md`): a runner whose simulator was an LLM went
green on every check while swapping the model moved every number. **So the rule has a
second half**: whatever decides your result must be *named in the
conjunction*. `env.lock` records the distributions installed here — it knows nothing about a
model version, an endpoint, or an environment variable, and S0's inner run inherits
`os.environ`, so self-reproduction cannot see them either. If a remote service, a model
identity, or an env var can change your numbers, **put it in a unit**, or you have a
registration that passes every gate and rests on something nobody wrote down.

---

## Anchors that waive or record

Every override is written down where the gate reads it. These are all of them:

| Anchor | File | Meaning |
|---|---|---|
| `<!--@goal_gate: not_applicable — why-->` | goal.md | the goal stage does not apply (a toolchain smoke test, a reproduction to learn the tooling) |
| `<!--@pilot_gate: not_applicable — why-->` | prereg.md | the pilot stage does not apply |
| `<!--@pilot_gate: no_blind_waived — why-->` | prereg.md | the pilot applies, nothing is blind, and here is why that is honest |
| `<!--@goal_changed: what moved, and why it is not a response to the pilot-->` | prereg.md | not a waiver: the record of a commitment that moved after the pilot |
| `reason=… waived_by=…` inside `@evidence` | goal.md | the literature search was skipped, by a named person, for a stated reason |
| `split_waived=…` inside `@size_estimate` | goal.md | two failure modes kept in one question, and why |

A waiver is checked for existence, never for truth. It puts the decision on the record so
that closeout cannot pretend it was never made.

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
- [ ] every unit name in §2 (`S0`, `S1`, …) is the prefix of the runner's key for it
      (`S2_increases_across_sweep`), one for one, and the artifact carries no unit the
      registration never declared — `newlife run` checks the alignment (`references/cases.md`:
      it caught a conjunction one unit weaker than it read, the first time it ran)
- [ ] `newlife pilot` and `newlife freeze` were run from the **same** newlife — two
      installations on one machine are two environments, and the freeze refuses when the
      last pilot's differs; installed a package since the last pilot? A short pilot on a few
      configurations is enough — coverage is the union of every pilot, the environment
      check reads only the latest
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
