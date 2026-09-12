# Analysis design before freeze

Use only the checks that can change this question. The purpose is an executable,
discriminating design, not a second plan document.

## Define the comparison

- Name the unit being judged and the population/system it represents.
- State the one primary contrast or mechanism and the counter-result that would make it
  lose. Separate secondary and exploratory questions.
- Identify confounds, selection effects, leakage, scale effects and measurement artifacts
  that could produce the same observation. Handle each materially plausible one by design,
  a registered covariate/control, an invalidation rule or an explicit limitation.
- Fix train/test or discovery/confirmation boundaries before using the protected outcomes.
- Name every input, transform, model/test and output needed to apply the decision rule.

Use an effect size, interval, power calculation or multiplicity correction when the claim
and data require them. Do not force these onto a deterministic invariant or formal
counterexample. For seeded/stochastic two-group comparisons, the existing M1-M6 design in
`design.md` remains the required NewLife mechanism for choosing repeats.

## Prove the pipeline before freezing it

Break implementation into steps whose outputs can be checked. Validate a nontrivial
estimator or measurement on synthetic/known data. Record row counts, ranges, units and
silent drops at boundaries. Pilot every quantity in a criterion on values that do not
consume its blind test. Preserve the distinction already enforced by this skill: the pilot
may change how a fixed quantity is measured, not what is measured or the expected direction.

Do not embed automatic commits in the plan. Code and intermediate artifacts may be committed
when authorized by the repository task; freezing and committing `results/` keep their
separate person-owned gates.

## Feasibility branch

Offer this only when the ability to run is itself unknown and determines the design. Before
any probe, obtain the person's explicit choice plus:

- a measurable feasibility question;
- a compute/time/memory envelope with enforcement that has been observed firing;
- a specific abandonment condition;
- the separation between structural/resource measurements and protected scientific
  outcomes.

Within that envelope, build a minimal end-to-end runner, measure a scaling ladder near the
largest affordable cases, test obvious mitigations and run at most the agreed exploratory
campaign. Persist every probe with environment, seed, code identity and exit status. Report
extrapolation and uncertainty. Do not call the campaign confirmatory or automatically leave
the mode. The person chooses whether to abandon, explore again or return to formal design.

## Ready-to-freeze check

The design is ready only when paths and variable/unit names agree; the primary decision
rule is computable; each criterion can go red; invalidation is separate from H0; protected
outcomes remain blind; environment/data/model identities are recordable; and the full
concrete freeze object can be shown for approval.

## Provenance

This reference restates useful design and feasibility checks from K-Dense's
Science-Superpowers `designing-the-analysis`, `setting-up-reproducible-analysis` and
`establishing-feasibility-first` at commit
`ccc1b2d41a389b2d6dadf1945603f81d66c5e85e` (MIT). It is rewritten around NewLife's
existing goal, pilot, freeze and mechanical-verdict model.

