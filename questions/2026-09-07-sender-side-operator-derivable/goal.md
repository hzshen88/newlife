# Goal — sender side operator derivable

**This file is red until you fill it in.** `newlife freeze` will refuse to run, and it is
supposed to: every anchor below covers a step that **leaves no trace when skipped**. Skip
the verdict runner and there is no `summary.json` — visible, no gate needed. Skip the
literature search and nothing is missing at all, which is why a gate has to carry it.

If this question genuinely has no goal stage — a toolchain smoke test, say — do not leave
the file half-filled. Add one anchor giving the reason, and the gate goes green:

    <!--@goal_gate: not_applicable — <your reason here>-->

**An anchor's body must not contain `>`** — the parser stops at the first one and the
anchor then silently does not exist. That is also why the line above is an example rather
than a working anchor: replace `<your reason here>`, angle brackets included.

---

<!--@evidence: literature_searched=TODO, sources=TODO, verdict=TODO-->
<!--@counterparty: TODO-->
<!--@attack_layer: TODO-->
<!--@decides: TODO-->
<!--@who_changes_behavior: TODO-->
<!--@size_estimate: impl_lines=TODO, criteria=TODO, failure_modes=TODO-->

| Anchor | What it must say | Why it is gated |
|---|---|---|
| `@evidence` | `literature_searched=yes, sources=N, verdict=known\|partly known\|unknown` — or `no` **with** `reason=` and `waived_by=` | A search that failed and was silently skipped looks exactly like one that found nothing |
| `@counterparty` | Who would bet the other way, and on what grounds | If nobody would, the result is already inside your expectations. **Seven H1 and zero H0 start here** |
| `@attack_layer` | `conclusion` \| `premise` \| `definition` | Under attack at the premise a simulation settles nothing — the output can only be a discriminating prediction. `definition` means do not simulate at all |
| `@decides` | `design` \| `run` | Confuse them and a tooling result gets reported as a conclusion about the world |
| `@who_changes_behavior` | A specific person **and** a specific decision | The "unimportant but decidable" bucket passes every later gate and is still not worth asking |
| `@size_estimate` | `impl_lines=N, criteria=N, failure_modes=1` | No estimate made in advance means nothing to calibrate against |

**`failure_modes` must be 1.** A failure A and a failure B you would want to report
separately are two questions, not one. To merge them anyway, add `split_waived=<reason>`.

## 1. What this buys

(Including anything cheap that already falsified part of it while you were drafting.
A draft that survived contact with no evidence at all is a draft, not a goal.)

## 2. Success criteria

(A conjunction, and **independent of H1** — these say whether the question was answered,
not whether the answer came out the way you wanted.)

## 3. Explicitly not doing

## 4. Risks declared in advance

(Including what this does **not** prove even if every criterion holds. At closeout,
"we showed A" and "we did not show B" must be two separate sentences.)

## 5. Closeout judgement

(Filled in afterwards: achieved / not_achieved / regressed / not_applicable.)
