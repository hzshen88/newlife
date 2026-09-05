---
name: decidable-question
description: Turn any question into one that the later steps can actually settle — first triage whether simulation should answer it at all and whether it can be judged, then reshape an unjudgeable one until it can be. Produces an anchored goal draft for the execution system. Use when asked how to frame a question, whether something is worth simulating, how to make it decidable, or to start a goal. Not for a question whose criteria are already clear and only need writing up (that is preregister-verdict), nor for implementing and judging an already-decidable question (that is newlife init / freeze / run).
---

# decidable-question — turning a question into a solvable, real one

> **This file ships with the `newlife` wheel; `newlife skills install` copies it verbatim
> into your AI's config directory. No transformation** — the master and the deployed copy
> are one file, because "two copies drift apart" is a shape this project has paid for
> repeatedly.
>
> This is **step one**: pure method, zero tool dependencies, entirely conducted in
> conversation, producing a text. Works in ChatGPT, Claude or anywhere else. Step two
> (writing the criteria) is `preregister-verdict`; step three (execution and judgement) is
> `newlife init / freeze / run / check / audit`.

**Its output is the next step's input**: an anchored goal draft. It belongs in
`goal.md` inside the question folder, where a machine gate reads it — **whatever you
cannot state, `newlife freeze` refuses.**

---

## 0. One thing to see first

> **A simulation will always hand you a number.** You never receive the error "this
> question should not be simulated". You receive something that looks a great deal like a
> conclusion, and reflects only your assumptions.

So the entire value of this step is in **refusal**, not in production.

---

## 1. Generation: where candidates come from

**Reject "combine A and B" by default.** That opens a new intersection, which accounts for
3.2% of landmark papers over the last decade — against 71.3% for method or angle
innovations that open no new intersection, a ratio of 22:1. It is the easiest move to think
of and the least productive.

**Eight framing moves** (complete over 258 papers; there is no ninth):

| | Move | | Move |
|---|---|---|---|
| A | formalise | E | **promote an anomaly** |
| B | change the unit or level | F | **static → dynamic** |
| C | **operationalise** (55.3% of the last decade, the mainstream) | G | change the substrate |
| D | change the solution criterion | H | adjust the constraint set |

**The one useful dichotomy: E and F never act as carriers for cross-domain import — they
grow only out of a domain's own anomalies.** What can be carried across domains is
A/B/C/D/G/H.

> **The first source is an anomaly already on the record, and the move is E.**

**But watch where E's raw material points.** A measured lesson: across nineteen milestones
of one project, E was used several times and **everything promoted was an engineering
anomaly** ("this change broke last time's artifact") — so everything produced was a tool
question. **Nineteen rounds, zero questions about the world.**

> **E pointed at engineering anomalies → tool questions. E pointed at domain anomalies →
> world questions.** The rule does not change; where E looks does.

**E is not "fix it".** Patching it is H⁺ (fold it into the constraints), which is
engineering. E asks: **is it really the same cause every time it recurs?** — the anomaly
itself becomes the object of study.

---

## 2. Triage: three questions, in order

### Question 1: is the answer decided by design, or by running?

| | Meaning | Type |
|---|---|---|
| **decided by design** | asking whether the thing I built works as designed | **tool** |
| decided by design, but others would do the same | changing how research is done | **methodology** |
| **decided by running** | asking how a system I did not fully design will behave | **world** |

**Do not use "does the answer depend on some measurement" as the test.** It fails outright
for artificial life and purely computational objects, where the simulation *is* the object
of study. "design vs running" covers those.

**Tool and methodology questions are entirely legitimate** — but **they may not claim
conclusions about the world.**

### Question 2: which layer is the counterparty attacking?

Name a **specific** counterparty first — not "someone might disagree", but **which claim**,
and **what would be different if that claim were wrong**. Naming is harder to fake than
phrasing.

| The counterparty attacks | Meaning | Correct output |
|---|---|---|
| **the conclusion** | the mechanism is uncontested, the consequence is | simulation can settle it → **a conclusion** |
| **a premise** (mechanism / parameters / model form) | the model itself is in dispute | **cannot** settle it → see the loop in §4 |
| **whether the question means anything** | a dispute about definitions | do not simulate |

**Then look again: if the counterparty is betting *with* you, the candidate is too safe.
Pick another.**

### Question 3: who changes what they do because of the answer?

If you cannot name **a specific person** and **a specific decision**, this is the
"unimportant but decidable" tier — **it will pass every gate downstream and it is not worth
asking.**

---

## 3. Making it decidable: four pieces, none optional

Stated **in advance**:

1. **the mechanism** — what changes what
2. **the observable** — which number you read off at the end
3. **the control** — what that number is compared against
4. **which mutation would turn it red** ← **the watershed**

The fourth is the easiest to skip and the most fatal. **A question is computable not
because you can produce a number, but because you can say in advance what would have it
judged false.**

**The accompanying counterexample** (walked into twice): the mutation must **actually
detect something**. "Multiply the list by 2" does not change its i-th element; "replace the
four decimals that get displayed" does not change the full-precision value in the JSON.
**Declaring a pass on the strength of a mutation that detects nothing is self-deception.**

### The shape of the criteria

- **A conjunction, not a weighted score.** Any one false makes the whole false.
- **The criterion must not be the very difference this change was made to produce**
  (a constructed criterion is circular).
- **"behaves the same" is usually not enough.** Measured: one wrong parameter left the
  trajectory identical and nothing raised an alarm. Compare **item by item**.

---

## 4. When it is not decidable: reshape it, do not discard it

### There is exactly one reshaping pattern

> **Replace "can it" with "is there a mutation, nameable in advance, that would turn it
> red".**

Three measured examples:

| Original question | Reshaped into |
|---|---|
| **can** this declaration be derived automatically | the derived declaration is **identical item by item** to the hand-written one (not "behaves the same") |
| **can** this phenomenological model represent this degree of freedom | pin the parameter at **one** point and see whether it moves at **the others** |
| **does** this framework need some feature | can the feature be expressed as pure data over a **closed operator set** |

### No simulator for it: five options, ordered by cost

| | What to do | Move | Cost (measured order of magnitude) |
|---|---|---|---|
| 1 | **reframe the question** so what you have can reach it | B / H | cheapest, and most often skipped |
| 2 | **admit a third-party simulator** | G, change the substrate | tens of lines of declaration |
| 3 | **extend what you have** | H⁺ | depends on the gap |
| 4 | **write one from scratch** | C, operationalise | hundreds to thousands of lines |
| 5 | **judge that it should not be answered by simulation** | — | zero |

**Option 5 is not a failure.** The correct output for "important but undecidable" is
**"what the premises would have to become for it to be decidable"**, not a conclusion.

### When the counterparty attacks a premise, that is a loop, not a wall

```
question -> counterparty
             |- attacks the conclusion -> settle it -> a conclusion
             `- attacks a premise      -> revising that premise is the next round -> back to the top
```

**But the loop needs a legitimacy condition, or it degenerates into curve-fitting:**

> **The next round's criterion must not be the very difference this round's revision was
> made to produce.**

Add a reaction to a model and of course it can now produce that thing — taking "it can now"
as the criterion is circular. The correct shape: **fix the new parameter at one point and
predict the others.**

**Stopping condition**: stop when a round's revision **yields no non-constructive
discriminating prediction**. If it cannot, that round only fits the known difference and
predicts nothing else — that is adding a parameter, not improving a model.

**⚠️ "the counterparty attacked a premise → I changed the model → now it is right" is
HARKing at the level of the model.** The only thing that stops it is **freezing the
criteria before changing the model, every single round.**

---

## 5. Output: an anchored goal draft

**Write it to `questions/<slug>/goal.md`.** `newlife init` scaffolds that file already,
**deliberately red**: `newlife freeze` refuses until these six anchors are filled in, and
`newlife check` reports the same gate. **Whatever you cannot state, the freeze rejects.**

If the stage genuinely does not apply — a toolchain smoke test with no claim about the
world — waive it on the record rather than leaving the file half-filled:
`<!--@goal_gate: not_applicable ... reason ...-->`. An anchor body must not contain `>`;
the parser stops at the first one and the anchor then silently does not exist.

```markdown
# Goal — <one sentence, phrased as a question>

<!--@evidence: literature_searched=yes, sources=N, verdict=known|partly known|unknown-->
<!--@counterparty: which premise or conclusion, and what would differ if it were wrong-->
<!--@attack_layer: conclusion|premise|definition-->
<!--@decides: design|run-->
<!--@who_changes_behavior: a specific person + a specific decision-->
<!--@size_estimate: impl_lines=N, criteria=1, failure_modes=1-->

## 1. What this buys      (including cheap falsification results found while drafting)
## 2. Success criteria    <!--@criterion: C1-->  a conjunction; independent of H1
## 3. Explicitly not doing
## 4. Risks declared in advance  (including what this does not prove even if it holds)
## 5. Closeout judgement  (filled in afterwards: achieved / not_achieved / regressed / not_applicable)
```

**`failure_modes` must be 1.** More than one and the judgement turns muddy. If it will not
reduce to 1, the question has not been split yet — a complete list of components *and* a
single mode of failure, both, is what splitting correctly means.

**Size estimate: list the components in full, then report the sum directly.** Measured:
reporting the sum directly lands within ±5%; applying an overall correction factor makes it
worse. Add a margin only to the one component that is obviously of a kind never done before.

---

## 6. Self-check: would this draft pass every gate and still not be worth asking

In order; any "no" sends it back:

- [ ] you genuinely **do not know** the answer while drafting (a question whose answer is
      known passes every gate and is worth nothing)
- [ ] **failure still produces something** — you can say where the boundary is
- [ ] the counterparty is **named down to one specific claim**, not a sentence
- [ ] the counterparty is betting **against** you, not with you
- [ ] all four pieces are present, and **the mutation in piece 4 really does detect something**
- [ ] the success criteria are **not** a restatement of H1
- [ ] `failure_modes = 1`
- [ ] you can say **who changes what they do**, and to what

---

## 7. Fixtures: graded questions with known answers

A new rule is first made into a fixture that goes red, then the rule is changed — **TDD on
the methodology itself.**

| Question | Correct tier | Why it is easy to grade wrong |
|---|---|---|
| "install only the declared dependencies — can the frozen artifact still be replayed?" | **methodology** | it has a counterparty, literature and negative controls, so it **looks the most like science** — but the answer is decided by design |
| "phenomenological vs mechanistic model: what did the network layer buy?" | **methodology** | a real biological phenomenon and textbook curves make it **the easiest to misgrade as a world question** |
| "re-express a known model on a new platform, bit-for-bit" | **tool** | the criterion is "bit-for-bit" and it reproduces a known result |
| "does freezing this locus cause extinction or a uniform weakening?" | **world** | in artificial life there is no external measurement — **only "design vs running" grades it correctly** |

---

## 8. Evidence grading: which rules have been checked

| Rule | Status |
|---|---|
| eight moves complete, E/F endogenous-only, 3.2% for new intersections | **corpus statistics** (164 + 94 papers) |
| "the mutation must really detect something" | **walked into twice** |
| "behaving the same is not enough; compare item by item" | **walked into once** |
| size estimate: "list in full, report directly" | **calibrated three times, ±5%** |
| the "design vs running" grading | **20 cases validated retrospectively**, never prospectively |
| "who changes what they do" as an importance gate | **unvalidated** — it has never yet stopped a real candidate |
