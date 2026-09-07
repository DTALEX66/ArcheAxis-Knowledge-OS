# Overnight results (2026-09-07 -> 2026-09-08) - full-autonomy run

Branch `codex/full-loop-0906` (pushed to origin, synced). Head at summary time:
`bf6ab31`. `main` untouched (`4ca46ea`). This file is the consolidated
morning-facing summary; the live ledger with per-slice detail is
`docs/authority/taskpack-0907/EXECUTION.md`.

## Final verified baselines (round 239, at f1fd14c; doc-only commits since)
- Full Rust workspace `cargo test --workspace --offline`: exit 0, zero failures
  (rustc 1.97.1 stable-x86_64-pc-windows-msvc, MSVC 14.44 toolchain under
  `D:\All projects\OS External Configuration\10-toolchains\msvc`; reproducible
  wrapper `.project-local/runs/cargo-full-workspace.bat`).
- Full Python suite = `tests` + `knowledge_base/tests` + `integration-tests`:
  2394 passed / 7 skipped / 124 subtests, exit 0. Count reconciles exactly:
  tests/ 2316 + knowledge_base/tests 38 = 2354 (minus 7 skipped = 2347 passed)
  + integration-tests 47 passed = 2394.
- Architecture guard passed; repository conventions gate passed (worktree).
- Services healthy: DeepTutor backend :8001 (root + catalog 200), frontend
  :3782 (200), ollama :11434 (200). Left running for owner inspection.

## DeepTutor local host (X03/C08) - solved and stable all night
- Single-user no-auth mode; catalog configured to local ollama qwen3:8b.
  `doctor --online` PASS. Real Chinese content round-trip EXACT (0 U+FFFD;
  corruption was CLI-only, API/JSON is clean). Real local-model generations:
  doctor provider response, add_record auto-summaries (chat + question), a
  complete Chinese chat answer via capabilities/chat/execute-stream to "done",
  book draft bk_e00b5ff13d with model title/proposal, learning path generated
  from the Chinese notebook (module "Notebook Concepts" -> KP "Saving Personal
  Definitions and Hypotheses"; progress map next action "probe", stage
  diagnostic), mastery_path capability run to a terminal done event.
- Evidence (ignored): `.project-local/deeptutor-val/` server.log, start.log,
  chat-answer*.txt, book-export.md, ui-*.png, model_catalog.json.

## C-item board (final overnight state; per-item detail in EXECUTION.md and
C-FIX-STATUS-2026-09-08.md v6)
- C01 DONE. C02 DONE (session actor guard + real-process escalation test).
- C03 PARTIAL - large core landed: single-transaction review, anchor reverse
  lookup, supersedes chain, superseded-not-current, archive-safe. UI wiring open.
- C04 PARTIAL - demo migration strong: legal PERSONAL_DEFINITION type, hash +
  row verify before write, single atomic staging tx, inserted/reused counts,
  legacy-row id preserved, attachments/links explicit-loss rows, legacy bytes
  untouched. Real-DB snapshot open.
- C05 PARTIAL parts 1-3: idempotent client_event_id, history read, absolute UTC
  due; FSRS donor verified healthy (6 tests). Full trajectory + UI open.
- C06 PARTIAL parts 1-3: machine qualification consumers (qualification
  endpoint, search active flag, active_only filter). Tool-call -> feedback ->
  correction loop open.
- C07 PARTIAL: real public retrieval probe (Wikipedia, numeric grounding) +
  local-model verdict via chat API; single-pipeline worker registry open.
- C08 PARTIAL: host solved (above); Windows candidate package + Core <-> host
  adapter wiring open.
- C09 PARTIAL: locked CI + in-repo probes; candidate package hash + CI-on-push
  + independent GPT audit open.
- C10 PARTIAL (audit evidence added round 240): same-tool terminal census
  19.146 GiB logical / 112,675 files observed; largest residual dirs listed;
  rebuild retest done (root target/ rebuilt 5.603 GiB after X14 wave-2
  deletion); .hermes growth-stop double-proven (newest write 2026-09-06
  11:29:42; logical size 42.853 GiB / 718,077 files, unchanged vs the audit's
  42.855 GiB); D: free 235.98 GiB explained.

## Cleanup / growth-stop terminal state (round 240, commit bf6ab31)
- Census JSON: `.project-local/runs/c10-census-round240.json` (same tool,
  read-only, logical bytes; opaque .hermes/.git/.codex excluded and retained).
- Largest residual groups: .project-local 12.445 GiB, target 5.603 GiB, .venv
  0.858 GiB, frontend 0.099 GiB, data 0.094 GiB.
- Zero .hermes writes across the whole overnight (real starts/failures/
  restarts/concurrent runs). Git/source/real DB unchanged.

## Next (recommended in a fresh context, owner awake)
1. Finish the majors in dependency order: C07 single-pipeline worker registry,
   C08 Windows candidate package + Core<->host adapter, C05 FSRS adapter +
   real trajectory UI, C06 machine loop, C10 remaining entrypoint startup-rule
   checks, C09 candidate package hash + CI-on-push.
2. Return every fix to its original X task with regression evidence and
   checkpoint commits, then submit for the next independent GPT audit
   (Q00/Q01 verdicts are never self-signed).
