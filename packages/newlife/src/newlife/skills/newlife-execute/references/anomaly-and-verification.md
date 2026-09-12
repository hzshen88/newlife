# Anomaly diagnosis and evidence verification

## Diagnose in four bounded passes

1. Reproduce with the same inputs, seed, environment and exact error/output. Record the
   first stage where observed behavior diverges.
2. Compare a working case, recent code/input/environment changes and a known reference.
3. State one causal hypothesis and run the smallest discriminating check. Do not stack
   adjustments.
4. Resolve according to evidence: fix a code defect at its source, handle invalid input by a
   declared rule, or preserve a real result. An unregistered handling choice makes the
   affected analysis exploratory.

After three failed adjustments that reveal different problems, treat the design as suspect
and request the concrete decision needed to reopen it. Keep working on independent branches.

## Verify before claiming

For each material claim identify the command, exit status and artifact that supports it.
Read the estimate/verdict and diagnostics; a successful process exit alone is insufficient.
A confirmatory label also requires the applicable freeze/audit and the registered
reproduction. Report effect size and uncertainty when the method supports them; a
non-significant value alone is not evidence of absence.

Store a verification identity over relevant code, inputs, environment and configuration.
Reuse the result while that identity is unchanged. After a change, rerun only the claims it
can affect and update the identity.

Never hide a failed run, select a favorable seed/specification, change a threshold after
seeing the result, or trust another agent's completion summary without inspecting its
artifacts.

## Provenance

This reference adapts anomaly and verification principles from K-Dense's
Science-Superpowers `investigating-anomalous-results` and
`verifying-results-before-claiming` at commit
`ccc1b2d41a389b2d6dadf1945603f81d66c5e85e` (MIT), with evidence reuse and scoped
continuation defined for NewLife.

