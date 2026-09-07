# Overnight results (2026-09-07 鈫?08) 鈥?full-autonomy run

Branch `codex/full-loop-0906` (pushed to origin). Head SHAs progressed through
`3daeb2d -> 0672147 -> e9f43df -> 9abe382 -> db20593 -> 980d1f4 -> d2b7da9 ->
eb98b43`. `main` untouched. This file summarizes what ran while the owner slept.

## DeepTutor (X03/C08) host 鈥?now fully usable locally
- Provider config solved programmatically: `deeptutor serve` FastAPI settings
  catalog (no auth in single-user mode) + PUT local-ollama profile
  (qwen3:8b, base_url http://127.0.0.1:11434/v1). `doctor --online` PASS incl.
  real provider response.
- Full stack: `deeptutor start` runs backend (uvicorn :8001) + packaged
  Next.js frontend (:3782, "DeepTutor" title). Headless screenshots captured:
  `.project-local/deeptutor-val/ui-home.png` (~47 KB) and `ui-book.png`.
- Chinese content: notebook API round-trip is EXACT (0 U+FFFD); corruption was
  CLI-only. Real local-model generations verified: doctor provider response,
  add_record auto-summaries (chat + question), a complete Chinese chat answer
  ("闂撮殧閲嶅鈥﹀涔犳妧宸?, via capabilities/chat/execute-stream to "done"), a
  Book draft with model-generated title/proposal (bk_e00b5ff13d), and a
  learning path generated from our Chinese notebook (module "Notebook
  Concepts" -> knowledge point; map -> next action probe).
- Files (ignored): `.project-local/deeptutor-val/` server.log, start.log,
  chat-answer.txt / chat-answer2.txt, book-export.md, ui-*.png,
  data/user/settings/model_catalog.json (no real secrets).

## Baselines refreshed at C-fix HEAD (after C01-C04/C09/C10)
- Full cargo workspace `--locked --offline`: exit 0, zero failures.
- Full Python suite: 2394 passed / 7 skipped / 124 subtests, exit 0 鈥?the
  real-URL network test PASSED this time (egress intermittent), so no
  unexplained failure remains at that HEAD.

## C-item board (see docs/authority/taskpack-0907/EXECUTION.md for detail)
C01 done; C02/C03/C04 partial (real fixes + tests); C09 partial (CI --locked);
C10 partial (terminal census); C05/C06/C07/C08 host now unblocked (above) with
remaining wiring recorded in the audit board.

## Next (owner decides or a fresh session continues)
Finish C05-C09 wiring on top of the now-working local host: FSRS contract
adapter (C05), machine reuse-qualification consumers (C06), single-pipeline
worker + one real public check when egress allows (C07), Windows candidate
shell/package (C08), reproducible probe receipts + candidate hash (C09).
