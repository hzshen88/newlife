---
name: newlife
description: Use when the person asks how NewLife or exloop works, where an existing research question stands, what happens next, or which NewLife stage owns a request. Not for doing a stage's work, and not a universal gate for direct answers, reviews, programming, or collaboration tasks.
---

# NewLife — explain and route the research workflow

The person says what they want to understand or finish. You inspect the available context
and state, explain the next meaningful decision in ordinary language, and do the command or
stage work for them. Do not make them choose a skill name or print a command menu.

Read [the workflow contract](references/workflow-contract.md) when routing, resuming a
question, or deciding whether a pause is a real gate. It is the shared source for approval,
clarification, evidence reuse and completion behavior.

## Route the request that actually exists

1. **Direct answer, review, implementation, debugging, programming or collaboration:** do
   that task with its normal workflow. Research subject matter alone does not require an
   exploration or a NewLife question.
2. **“Where are we?” or work in a repository with `questions/`:** run `newlife status` on
   the relevant question folders and read their files. Resume the stage the state shows. Do
   not ask the person to reconstruct the history or repeat an approved goal.
3. **Open curiosity with no decidable boundary:** use `exloop`. When several explanations
   are live, use Idea Lab inside the same exploration. A source check returns to that
   exploration; it does not automatically start formal design.
4. **A new formal question that is not mechanically decidable yet:** use `newlife-goal`.
5. **A clear goal that still needs design, pilot classification or freeze preparation:**
   use `newlife-prereg`.
6. **An existing question that must run, resume, diagnose, verify, audit, report or close:**
   use `newlife-execute`.

If a requested confirmatory analysis would expose outcomes before its prediction and
decision rule are fixed, say what would become exploratory and route to preparation. An
explicitly exploratory task may proceed with that label; do not pretend later that it was
confirmatory.

## What the person decides

The person owns these consequential transitions:

- whether an exploration becomes a formal question;
- whether to enter or leave feasibility mode, its compute envelope and its abandonment
  condition;
- the concrete question/version to freeze;
- whether to commit a concrete `results/` set;
- any merge, publication, external send or destructive discard not already authorized.

For the same object, version, scope and action, an approval already given remains valid.
Do not ask twice. Silence is not approval, and approval of one item does not expand its
scope. Prepare and deliver every independent artifact before asking for a remaining gate.

Two NewLife repository actions are always called out: **ask before freezing, and ask before
committing `results/`.** A freeze is immutable evidence; a result commit makes its chronology
part of that evidence. Routine status checks, inspection, drafting, isolated setup,
authorized execution and reporting do not each need another confirmation.

## What the stages look like to the person

- During exploration they discuss one useful distinction or discriminator at a time. A
  persistent map is kept only when requested.
- At goal preparation they see the question, counterparty, decision, scope and what could
  falsify it. Existing answers are reused.
- During preregistration they see what was already observed, what remains blind, how each
  criterion can fail and the exact freeze candidate.
- During execution they receive progress while work continues, then verified artifacts,
  the NewLife verdict/audit status, limitations and the concrete result-commit state.

No stage creates a second scientific status system. The question directory and `newlife
status` remain authoritative for formal work; an exloop map remains the exploratory record.

## Local checkouts used by a question

An editable local package can run correctly while `env.lock` records only a version string.
For each such dependency, put the source digest and dirty-worktree state inside the verdict's
mechanical conjunction, because a fact that appears only in prose cannot change the verdict:

```text
<name>_source_sha256    provenance.package_digest(module)
<name>_git_dirty        git status --porcelain is empty
code_retrievable_from   URL or archive identity plus the date checked
```

Record data retrieval separately. A reachable code commit does not make restricted or
unpublished data retrievable. Git submodules need an explicit recursive-fetch instruction
or vendoring; a clean parent checkout with an empty submodule can otherwise pass superficial
source checks and still fail to run.

## Setup when requested or required

Install NewLife, then run `newlife start .` in the research repository. The assistant runs
these commands. `start` initializes the repository if needed, writes its guidance and
installs the NewLife and exloop skills into detected hosts. If exloop is missing, install a
compatible exloop package and rerun. Report exactly what changed and where; do not install
unrelated tools on the strength of this setup request.

Methods adapted during the Science-Superpowers consolidation are recorded in
[method provenance](references/method-provenance.md).
