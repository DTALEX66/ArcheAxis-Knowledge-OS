# C-fix status v4 (2026-09-08 overnight, HEAD be4cdae)

Branch `codex/full-loop-0906` (pushed). `main` untouched (4ca46ea). Full cargo
workspace green at b1e4c98; python 2394 at earlier refresh; DeepTutor local
host running (backend :8001, frontend :3782).

## C board
| C | Status | Evidence (SHAs) |
|---|---|---|
| C01 | DONE | 40f56fc, 9f3c360 |
| C02 | DONE | bb90422, 9e71c21 (session actor + real-process escalation) |
| C03 | PARTIAL (large core) | e944a01 (tx review), 362545f (anchor<-knowledge), 49e1b72/3d65609 (supersedes chain+archive), be4cdae (superseded not current) |
| C04 | PARTIAL (demo done + legacy untouched) | a382158, b1e4c98 |
| C05 | PARTIAL (parts 1-3) | aecdc1d/60b355a (idempotent+archive), 6a12184 (history), 17fa158 (absolute due) |
| C06 | PARTIAL (parts 1-2) | 1375fee (qualification endpoint), 77b6457 (search active flag) |
| C07 | PARTIAL (X07 real retrieval probe) | f56b258 + probes (intermittent egress) |
| C08 | PARTIAL (host solved) | 980d1f4/d2b7da9/eb98b43 (UI/chat/learning path) |
| C09 | PARTIAL (locked CI + in-repo probes) | b80ec29, 2ab62b8 |
| C10 | PARTIAL (terminal census + ASR clarification) | 7d1be96, 8c9c768 |

## Remaining (each needs a dedicated multi-hour slice or external resource)
- C03: full bidirectional navigation UI + invalidation semantics wiring.
- C04: attachments/links/learning-record fixture breadth + real-DB snapshot.
- C05: FSRS adapter reuse + complete trajectory over the running host.
- C06: end-to-end machine loop (tool call -> feedback -> correction).
- C07: single-pipeline worker registry (PDF/OCR/Office under one executor).
- C08: Windows candidate package + Core<->host adapter wiring.
- C10: growth-stop checks across CODEX/DSH/HERMES entrypoints.
- C09: candidate package hash + CI on a code push; then independent GPT audit.
