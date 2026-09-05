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

## Rule one: the pilot must cover **every** quantity that appears in a criterion

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

---

## Rule two: hygiene checks belong in the **invalidation conditions**, not the conjunction

Criteria say whether the hypothesis holds. Invalidation conditions say whether the run
counts at all. **Merge them and one mechanical check can veto a scientifically successful
run.**

- **Failure three**: a "did the timestep take effect" hygiene check was placed in both the
  conjunction and the invalidation set. It failed on perfectly legitimate data (the model
  had converged), **vetoing a round in which every scientific unit held.**

**The test**: ask "could this criterion fail on **completely normal** data?"
- yes → it is a hygiene check; move it to IC, or drop it
- no → it is a scientific criterion and may enter the conjunction

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

## Before freezing

- [ ] **run a pilot** covering every quantity that appears in a criterion (rule one) — `newlife pilot`; the freeze checks `pilot/ledger.jsonl`
- [ ] add the "Piloted?" column and mark every row; **confirm at least one is blind** (rule three)
- [ ] ask of each criterion "could it fail on normal data?"; move those that could into IC (rule two)
- [ ] ask of each criterion "what would make it go red?"; no answer means it is vacuous (rule four)
- [ ] write the criteria and the invalidation conditions **separately** — otherwise a
      disappointing result gets quietly reclassified as "the run didn't count"
- [ ] §5 states **what this round does not establish**; at closeout "we showed A" must never
      stand in for "B also holds"
- [ ] `git log -- <prereg path>` is empty — **the freeze must be its first commit**
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
