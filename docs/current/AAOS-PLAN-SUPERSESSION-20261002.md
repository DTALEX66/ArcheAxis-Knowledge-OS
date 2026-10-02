# Plan supersession — 2026-10-02

## What changed

| | Previous | Now |
| --- | --- | --- |
| Driving document | the DSH backend closed-loop prompt (`DSH-DEEPSEEK-BACKEND-CLOSED-LOOP.md`) | the 2026-10-02 plan *全历史恢复 + 云端分支收敛 + 快速闭环最终执行任务包* |
| Objective | finish the AAOS backend P0–P6 real multiformat loop and publish the UI contract | restore full project truth, converge the October cloud branches, then compress to one runnable daily loop |

## What is preserved, not superseded

* **R6** remains the authority and engineering baseline; **M0** remains the shortest-complete-loop
  overlay. **R7 is an execution layer**, and the plan says explicitly that it replaces neither.
* Every artifact produced under the previous plan stays authoritative for what it measures. The
  production HTTP contract, the acceptance runbook, the P0–P6 evidence, the key disposition and the
  M0 chain receipts are inputs to G0–G5, not waste.
* No history was removed. The append/supersede rule is satisfied by this record plus the archive
  verification in `AAOS-FULL-HISTORY-RECOVERY-20261002.json`.

## What genuinely changes in method

| Previous practice | Now required |
| --- | --- |
| advance the backend, then reconcile | **reconcile first** — G0 precedes all development |
| one long branch with many commits | converge #156/#157/#158 in a defined order |
| acceptance recorded as status strings | acceptance recorded on the eight-level ladder, with the forbidden inferences stated |
| capability added where useful | one vertical golden loop first; everything else stays in the Atlas/Donor pool |

## What the previous plan achieved that this one inherits

* the production HTTP contract (`AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md`) with its route
  inventory, authentication model, constant fields, error shapes and request bodies
* the acceptance runbook with one command per verification side
* the measured format reachability: readiness 9 of 9, real material 9 of 9
* the M0 chain re-run: 27 of 27 stages, empty validation errors, restart readback identical
* the local model runtime finding: LM Studio serving six models, a real caption and a real
  completion produced, and the H3 stack resolvable through ComfyUI
* the key disposition covering the 58 owned keys

## Rollback

This record is additive. Nothing from the previous plan was reverted, and the previous plan's
documents remain in place, so reverting this supersession is a matter of ignoring this file.
