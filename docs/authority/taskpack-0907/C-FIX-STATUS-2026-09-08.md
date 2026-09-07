# C-fix status v2 (2026-09-08 overnight) — for continuation / audit

Branch `codex/full-loop-0906`, latest `3d65609` (pushed). `main` untouched
`4ca46ea`. Full workspace cargo green; full Python 2394 passed (network test
passed once) at earlier refresh; DeepTutor local host fully running.

## C board summary
| C | Status | Evidence (SHAs) |
|---|---|---|
| C01 | DONE | 40f56fc, 9f3c360 (entry+encoding) |
| C02 | DONE | bb90422, 9e71c21 (session actor; real-process escalation) |
| C03 | PARTIAL → largely | e944a01 (tx review), 362545f (anchor<-knowledge), 49e1b72/3d65609 (supersedes chain + archive) |
| C04 | PARTIAL (demo layer done) | a382158 (legal type/verify/atomic/counts/id-preserve) |
| C05 | PARTIAL (parts 1-3) | aecdc1d/60b355a (idempotent), 6a12184 (history), 17fa158 (absolute due) |
| C06 | PARTIAL (part1) | 1375fee (qualification endpoint) |
| C07 | PARTIAL (X07 probe only) | f56b258 + probe runs (intermittent egress) |
| C08 | PARTIAL (host solved) | 980d1f4 (UI), d2b7da9 (chat), eb98b43 (learning path) |
| C09 | PARTIAL (locked CI + probes) | b80ec29, 2ab62b8 |
| C10 | PARTIAL (terminal census) | 7d1be96 |

## Open items with concrete next steps
1. C07: single-pipeline worker registry (OCR/PDF/Office under one executor
   profile) - new Rust executor profile + python worker adapters; needs a
   multi-day slice.
2. C08: Windows candidate shell/package + adapter wiring between ArcheAxis
   Core and the running DeepTutor host; UI already proven on host.
3. C05: FSRS adapter reuse + real trajectory UI (host available now).
4. C06: wire qualification into search/context consumers end-to-end.
5. C10: growth-stop checks across CODEX/DSH/HERMES entrypoints + ASR legacy
   model-dir read fallback clarification.
6. C09: candidate package hash + CI run on a pushed code commit; then new
   independent GPT audit.

## Servers left running for the owner
DeepTutor backend :8001 and frontend :3782 (kill anytime). Evidence under
`.project-local/deeptutor-val/` and `.project-local/runs/`.
