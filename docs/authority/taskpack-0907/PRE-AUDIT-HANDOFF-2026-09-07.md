# PRE-AUDIT HANDOFF (2026-09-07) — for independent GPT audit (Q00/Q01)

Executor: DSH/DeepSeek (selected_executor). Plan: AAK-REUSE-FIRST-20260907-R2.
All user-authorized runnable work has been executed to the reportable final
state; this file is the handoff for the independent GPT audit session (Q00/Q01
belong to that session, not to this executor).

## Candidate identity
- Branch `codex/full-loop-0906`, HEAD `65519ec`+docs (working tree clean at the
  last commit listed below; verify with `git status`/`git log` at audit time).
  33 commits ahead of origin; NOT pushed (by executor boundary). `main`
  untouched at `4ca46eaf…`.
- Baselines at final HEAD: full `cargo test --workspace --locked --offline`
  exit 0, zero failures; full Python suite 2393 passed / 7 skipped / 1 failure
  that is purely the sandbox child-egress restriction
  (`test_convert_newspaper4k_real_url_extracts_article`, https egress TLS EOF),
  not a code defect.

## Per-task final state (for the audit gate)
| Task | Final | Evidence index (repo) |
| --- | --- | --- |
| X00 | VERIFIED | docs/authority/taskpack-0907/ (15 files hash-verified) + DECISION_SUPERSESSION_LEDGER SUP-012..016 |
| X01 | PARTIAL | run 26510ae2b9d6 screenshot→OCR(eng+chi_sim); CI wiring audit in EXECUTION.md |
| X02 | PARTIAL | X02-REUSE-LEDGER.md waves 1-2 (8 workers + 6 donors) |
| X03 | PARTIAL/BLOCKED | DeepTutor probe + config attempts (4) in EXECUTION.md; upstream-interactive-bound |
| X04 | PARTIAL | quality alignment regression; API actor guard + tests (knowledge_actor_guard.rs) |
| X05 | PARTIAL | source_origins + HTTP origin + archive round trip (tests in domain/archive crates) |
| X06 | PARTIAL | OCR eng+chi_sim real runs; PDF/Office 10 passed (run 718c063f8a0e) |
| X07 | PARTIAL/BLOCKED | golden metrics real; public retrieval BLOCKED (egress evidence run 3855f5a1bd89) |
| X08 | PARTIAL | minimal review-event side (learning.rs + API) tests learning_events_api.rs |
| X09 | PARTIAL | machine reuse qualification (is_knowledge_active) test knowledge_active.rs |
| X10 | PARTIAL | legacy read-only export + demo semantic staging + loss ledger (stage_demo.rs) |
| X11 | PARTIAL | supervisor harness real journey green (C#→Core→Python→DB); packaging/GUI open |
| X14 | PARTIAL | wave-1 -10.77 GiB + wave-2 -6.03 GiB (root target) executed w/ manifests; .hermes NEVER |
| F01-F06 | DEFERRED_RETAINED | unchanged |
| Q00/Q01 | NOT RUN | this handoff is the input for the independent GPT audit |

## Evidence locations
- Authority/ledger: `docs/authority/taskpack-0907/` (EXECUTION.md has per-slice
  records incl commit SHAs and run ids).
- Ignored run/inventory evidence (private): `.project-local/runs/`,
  `.project-local/inventory/x14-wave1|wave2`, `.project-local/probes/`.
- Deletion manifests: `.project-local/inventory/x14-wave1/…-before/after.json`,
  `x14-wave2/before|after.json`; tracked summary in
  `X14-CLEANUP-MANIFEST-PREP.md`.

## What the audit should check
1. Re-run the Rust/python suites on a machine with working egress (the single
   network test should then pass) and confirm the recorded baselines.
2. Verify claim-vs-evidence for every PARTIAL row above (no DONE is claimed for
   incomplete tasks; statuses are honest).
3. Check the X04 actor guard, X08 event side, X09 qualification gate and X10
   demo staging behavior against the listed tests.
4. Confirm boundaries: no E-drive/private .hermes/real-library content access;
   deletion limited to recorded rebuildable caches.

## Open items after audit (in plan order)
Role-scope per-request actor; X07 real public check (needs egress);
DeepTutor default host (interactive UI); FSRS adapter wiring + learning export/
restore; machine asset registry + MCP trace loop; full legacy->vNext semantic
map + real-DB snapshot qualification; Windows installable candidate + GUI
journey; then X12/X13 (M1) per the frozen TASKS.json.
