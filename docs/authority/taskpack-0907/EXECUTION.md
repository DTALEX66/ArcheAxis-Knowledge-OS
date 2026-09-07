# 2026-09-07 Full Loop execution (AAK-REUSE-FIRST-20260907-R2)

This ledger is the live execution state for the REUSE-FIRST taskpack. It was
re-encoded to strict UTF-8 after the independent GPT audit (C01). Historical
per-slice detail lives in the git commits referenced below; audit record:
`Q00-Q01-AUDIT-2026-09-07.md`. Do not treat frozen `TASKS.json` TODO states as
completion; current status is this file.

## Plan and package identity

- Package: ARCHEAXIS-REUSE-FIRST-FULL-TASKPACK-2026-09-07 (R2), 15 files,
  MANIFEST hash-verified; TASKPACK.md sha256 `a9093a72...`; audit base
  `4ca46eaf...` (= origin/main). Frozen plan: docs/authority/taskpack-0907/
  TASKS.json (`plan_only`, 23 tasks X00-X14, Q00/Q01, F01-F06).
- Decisions D01-D16 recorded as SUP-012..SUP-016 in
  DECISION_SUPERSESSION_LEDGER.yaml.

## Repository state

- Branch `codex/full-loop-0906`; work pushed to origin at `74720bf6c7...`
  (33 commits ahead of the intake baseline `2daf8d7c`; same-name remote ref).
  `main` untouched at `4ca46eaf...`. Working tree clean unless noted.
- Baselines at `74720bf` + audit follow-ups: full `cargo test --workspace
  --locked --offline` green; full Python suite 2393 passed / 7 skipped / 1
  failure = sandbox child-egress TLS restriction on a real-URL test (not code).

## Independent GPT audit (Q00/Q01, 2026-09-07)

Verdict: Q00 not passed; Q01 pre-audited, conditions not met. Findings
C01-C10 assigned back to the original X tasks; recommended single queue
C01 -> C02 -> C03 -> C04 -> C07 -> C08 -> C05 -> C06 -> C10 -> C09.
G01-G14 conclusions and fix criteria: see `Q00-Q01-AUDIT-2026-09-07.md`.

### C-item status board (updated as fixes land)

| Item | Fix status | Notes |
| --- | --- | --- |
| C01 entry/encoding | DONE | AGENTS/indexes point to R2 + live ledger + audit board; ledger/audit/X14 re-encoded strict UTF-8 |
| C02 server-side identity | PARTIAL | launch middleware overwrites actor header from session claim; machine restricted in create/review/learning (unit tests green); real-process escalation scenario pending |
| C03 review txn + revisions + anchors | PARTIAL | knowledge::review is one transaction (status+event commit/rollback together; modified creates candidate AND records event); supersedes relations & bidirectional anchors open |
| C04 migration semantics/idempotency | PARTIAL | demo staging: legal PERSONAL_DEFINITION type, manifest hash+row verify before write, single atomic staging tx, inserted/reused counts, legacy-row id preserved; tamper rejected (tests); broader type map open |
| C05 learning schedule/contract | OPEN | reuse FSRS adapter; event contract; idempotent; absolute due |
| C06 knowledge qualification in consumers | OPEN | wire active check into context/get/results |
| C07 same pipeline converters + public check | OPEN | controlled capability registry; one product path |
| C08 host + Windows candidate | OPEN | target host config; shell/UI; candidate package |
| C09 same-commit qualification + locked CI | PARTIAL | vNext CI cargo test now --locked; reproducible probe receipts + candidate-hash gate open |
| C10 cleanup terminal state + growth-stop | PARTIAL | same-tool terminal census 57.241 GiB (805,837 files, 129 pre-existing errors) recorded + D: free ~240.7 GiB; growth-stop entrypoint checks partly covered by dev.py tests; ASR legacy model-dir read fallback still open |

## Slices landed before this re-encode (commit -> evidence)

- `976eea7` X00 intake + decisions (SUP-012..016), EXECUTION ledgers.
- `fd5182c`,`31b028c` X01 run-root doc + dev.py run evidence (14 passed,
  run be268a2d33/ea458cee118a).
- `bfb2c37` X01 real screenshot->OCR eng (run 26510ae2b9d6); CI wiring audit.
- `76a3680` X02 wave-1 ledger (8 vNext workers, X02-REUSE-LEDGER.md).
- `f5cfa5b` X02 wave-2 (6 learning/knowledge donors).
- `d2f6516`,`637daa3`,`079da71`,`6b30203` X03 DeepTutor probes: local notebook
  ASCII ok; Chinese-import gap; LLM config interactive-bound (BLOCKED).
- `76f59a6`,`08debe0` X04 worker_quality dual-schema alignment (37 passed).
- `cecf4b8` worker CLI stdout UTF-8 hardening (full cargo green).
- `18f5c06` X04 identity analysis; X06 OCR engine tests real (run
  ce16a8410c76).
- `30ca5f4` X04 API actor guard (machine candidate-only; tests
  knowledge_actor_guard.rs). Audit C02 requires replacing body actor with a
  trusted principal - tracked above.
- `968c479`,`a2dbef5`,`3fdd32b` X05 provenance: source_origins table/domain,
  HTTP origin metadata, archive EXPORT_TABLES + round-trip test.
- `f803bfe` X06 chi_sim real OCR.
- `2bccf90` X06 PDF/Office reconfirmed (10 passed, run 718c063f8a0e).
- `cd450ae` X10 demo semantic staging + loss ledger (stage_demo.rs, 4 tests).
- `80bfed6` X10 migration recon; full cargo workspace green.
- `040e9a3` X08 minimal human review-event side (learning.rs + API + tests).
- `b4f37b9` X09 knowledge active-qualification gate (test knowledge_active.rs).
- `65519ec` X11 supervisor harness real journey green (C#->Core->Python->DB).
- `acdaa1c`,`24b8f7d`,`74720bf` baseline/status records.
- X14: census 66.625 GiB; wave-1 deletion -10.77 GiB; wave-2 (root target)
  -6.03 GiB; manifests under .project-local/inventory/x14-wave1|2;
  summary tracked in X14-CLEANUP-MANIFEST-PREP.md. No .hermes deletion.

## Per-task final status (2026-09-07 pre-fix)

X00 VERIFIED. X01/X02/X04/X05/X06/X08/X09/X10/X11/X14 PARTIAL with real
slices. X03/X07 BLOCKED (config-surface / egress) with evidence. F01-F06
DEFERRED_RETAINED. Q00/Q01 = audit above (not passed).

## Boundaries and rollback

- No E-drive access, no private .hermes reads/writes, no real-library content,
  no release/tag/version, no main merge. Deletions limited to recorded
  rebuildable caches.
- Rollback per commit (one checkpoint each); run evidence private under
  .project-local/runs|inventory (not uploaded).
