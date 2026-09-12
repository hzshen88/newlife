# Skeptical review and closeout

Review the actual question, frozen rule, code diff and artifacts. Attack the strongest
claim through alternative explanations, confounds, leakage, assumptions, multiplicity,
researcher degrees of freedom, reproducibility, provenance and generalization. Classify
findings by whether they can change the conclusion, block reporting, or improve clarity.

Verify a review finding before acting. Clarify only an ambiguous finding; resolve clear
independent findings without suspending everything. A suggestion that changes a frozen
analysis is a disclosed deviation, not a routine improvement.

The report must state:

- what was run and reproduced;
- the final NewLife verdict and audit status;
- confirmatory findings supported by the frozen rule;
- exploratory observations in a separate section;
- deviations, limitations and threats to validity;
- exact rerun inputs/commands and provenance;
- archive status, result-commit status and any external-publication status.

If a full reproduction is missing, report the work as partial and name the missing check;
do not suppress an otherwise useful report. If an audit fails, do not use a confirmatory
label. The frozen record remains evidence of what happened.

Branch merge, sharing, retention and discard are repository actions after the report. Ask
for one only when it is actually needed and not already authorized. Destructive discard
requires explicit confirmation under the host's safety rules.

## Provenance

This reference adapts review, critique-handling and reporting principles from K-Dense's
Science-Superpowers `requesting-red-team-review`, `receiving-critical-review`, and
`reporting-and-archiving-findings` at commit
`ccc1b2d41a389b2d6dadf1945603f81d66c5e85e` (MIT). It removes the mandatory generic
end-menu while retaining evidence and authorization gates.

