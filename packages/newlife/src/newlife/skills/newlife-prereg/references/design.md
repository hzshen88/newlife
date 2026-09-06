# Designing the repetition count (rule seven)

Read before writing `judgement-design.json`. The freeze runs `newlife.gates.judgement_design`
for `seeded` and `stochastic` worlds: the six answers below must be present with their reasons,
and the declared N must re-derive from them.

`seeded` and `stochastic` both owe a repetition count, and **there is no rule that supplies
it**. It depends on the effect you care about, on the shape of your noise, and on what a
sample costs you — all three differ per question. What can be given is the sequence of
questions whose answers determine it, and a gate that refuses when they are unanswered.

**Answer these before freezing** (they go in `judgement-design.json` beside the
registration; the freeze pins it with the criteria):

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
their power there (measured: `references/cases.md`). Choosing the
statistic is not a matter of taste; it is the difference between decidable and not.

**Derive N by bootstrap power analysis, not by a formula.** `n = 2(z+z)²σ²/δ²` assumes
normality and equal variance and describes a t-test — three things that are typically false
here. Instead: take the pilot as an empirical distribution, shift it by the effect, and for
each candidate N run **the same test you will judge with**, counting how often it fires.
Take the smallest N that reaches your power. Multiple comparisons need no extra correction
because the real test already contains them.

**"Undecidable within this budget" is a correct answer.** It tells you what the question
would cost, which is more than a wrong N tells you (the first real use returned it:
`references/cases.md`).

**What this covers, and what it does not.** The derivation above is for **two groups
compared on a location statistic**. It does **not** cover monotone trends, more than two
groups, slopes, proportions, or variance itself. That boundary is not academic: the
milestone that produced this method had, as its own scientific question, whether a quantity
rises monotonically — **a shape this method cannot judge.** Forcing such a question into a
two-group derivation yields a number unrelated to what is being asked.

