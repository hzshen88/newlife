---
name: newlife-execute
description: Use when a NewLife question already exists and the person asks to run, resume, check status, audit, diagnose, verify, report, archive, or close it, especially when a run is partial, failed, or anomalous. Not for open exploration, goal framing, or freeze preparation.
---

# NewLife execution, verification and closeout

Carry an existing question from its real repository state to the requested deliverable. A
progress report is not a request to stop. Continue until the work is complete or a concrete
scientific, authorization or external-action gate blocks the dependent branch.

Read [the workflow contract](../newlife/references/workflow-contract.md). For a surprising
or failed result read [anomaly and verification](references/anomaly-and-verification.md).
Before a scientific report or closeout read [review and closeout](references/review-and-closeout.md).

## 1. Recover state before asking

Run `newlife status <question>` and inspect `goal.md`, `prereg.md`, `verdict.py`, the latest
pilot/results and available audit evidence. Check Git status and preserve unrelated staged,
modified and untracked work. State the stage, what is already valid, and what the request
authorizes.

- If the question is not frozen, return to `newlife-prereg`; execution cannot silently
  create or approve a freeze.
- If it is frozen under an older protocol/path, use that record in place. Do not migrate,
  refreeze or rewrite it to match today's skill layout.
- Reuse an earlier approval only when object, version, scope and action are unchanged.

## 2. Execute the authorized scope

Follow the frozen implementation and decision rule exactly. Validate nontrivial measurement
code on known/synthetic data before trusting it. Keep raw inputs immutable, write new
artifacts, and record source/environment/seed/model identity required by the registration.

Work through the requested run without waiting after routine groups of steps. Report useful
progress while continuing. Ask only when an unresolved choice would materially change the
registered analysis or the authorized scope; continue independent work.

For long runs record the launch command, PID or task identifier, log and output paths,
expected exit, and recovery/check command. Launching a detached process is not completion.
Track it to checked artifacts, or establish a truthful host-supported monitoring/handoff if
the task cannot remain active.

Do not commit each step automatically. Never use `git add -A`, stash, reset or include
unrelated work. The freeze has its own approval in `newlife-prereg`; `results/` has the
separate approval below.

## 3. Diagnose before changing

On an anomaly, reproduce and localize it before an adjustment. Decide from evidence whether
it is a code defect, input/environment problem or real finding. A code fix may proceed when
authorized and when it does not alter frozen scientific commitments; rerun affected checks.

A change to a frozen hypothesis, threshold, expected direction, blind unit, decision rule
or registered implementation is a deviation. Preserve the current record and report the
affected result as exploratory/invalid as appropriate; a new confirmatory attempt gets a
new registration. Do not change a seed or drop a case to obtain a preferred outcome.

## 4. Verify the evidence that changed

Run the verdict and required reproduction, then `newlife audit` as applicable. Readiness
checks run inside `newlife freeze`, and unit alignment runs inside `newlife run`; there is no
separate advisory CLI step.
Read the actual output and confirm artifact existence, shape, ranges, units and provenance.
Apply the frozen rule mechanically. A platform failure is not H0, and a pre-reproduction
summary is not the final verdict.

Record the code, inputs, environment and configuration that bound the check. Reuse this
evidence for the same unchanged claim. If one component changes, rerun the affected evidence;
do not rerun unrelated expensive work merely to repeat a status sentence.

## 5. Review, report and archive

For a confirmatory finding or materially consequential conclusion, perform skeptical review
of confounds, leakage, assumptions, researcher choices, provenance and overclaiming. Use an
independent reviewer when the host and authorization allow it; otherwise perform and record
the bounded review directly. Resolve critical issues before a confirmatory claim.

Deliver the report even when a separate repository action remains. Distinguish confirmatory
results, exploratory observations, invalid/platform failures, limitations and missing
evidence. Record execution/reproduction, verdict/audit, report/archive, result commit and
external publication separately.

## 6. Results commit gate

Before committing `results/`, show the exact paths and current verification/audit status and
ask for that concrete commit unless it was already authorized for the same result set. No
reply is not approval. While it is pending, finish every report and archive artifact that
does not depend on the commit. Do not replace this gate with a generic merge/share/discard
menu. If the current request does not include a commit or repository finalization, record
`results/` as uncommitted and finish without opening an approval prompt merely because the
report is done.

Merging, publishing, sending externally and destructive cleanup follow their existing
authorization rules. A request to finish the research run does not silently authorize any
of them.
