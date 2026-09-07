# REUSE-FIRST-20260907-R2 — Final unified result report (2026-09-07)

Executor: DSH/DeepSeek session (selected_executor). Scope: run every runnable
task of AAK-REUSE-FIRST-20260907-R2 to an M0-candidate reportable state; full
authorization given by the user; final result below is honest about what is
VERIFIED vs PARTIAL vs BLOCKED. Independent GPT audits Q00/Q01 were NOT run by
this executor (by plan they belong to an independent GPT session) - this
report does not claim them.

Branch: `codex/full-loop-0906`, working tree clean at HEAD (26+ commits ahead
of origin; NOT pushed). Baselines: full Python suite 2394 passed / 7 skipped
(run e31758dd7698 @ f803bfe); full `cargo test --workspace --locked --offline`
green at multiple HEADs incl. post-X05 (exit 0). Boundaries respected
throughout: no E-drive access, no `.hermes` private reads/writes, no real
library (资料库/五库) content access, no release/tag/version, no main merge,
no push.

## Per-task result

| Task | Result | Evidence / notes |
| --- | --- | --- |
| X00 摄入+记录 | VERIFIED | 15 files hash-verified in `docs/authority/taskpack-0907/`; SUP-012..016 in DECISION_SUPERSESSION_LEDGER.yaml; intake note added (commit 976eea7) |
| X01 运行根/浏览器/CI | PARTIAL | real screenshot→OCR (eng) run 26510ae2b9d6 + chi_sim run; CI wiring audited; a code-triggering live CI dispatch not run (no push by constraint) |
| X02 复用登记 | PARTIAL (waves 1-2) | X02-REUSE-LEDGER.md: 8 vNext workers + 6 learning/knowledge donors with hashes + test evidence |
| X03 DeepTutor 宿主 | PARTIAL/BLOCKED | local probe, ASCII import ok, Chinese-import gap evidenced; LLM provider config interactive-bound (4 attempts recorded, incl piped-stdin hang); default-host decision requires upstream UI |
| X04 契约/身份 | PARTIAL | worker_quality schema alignment locked (37 passed); create-path protections verified; actor-model design recorded (X04-IDENTITY-DESIGN.md); code landing needs role-scope authority (open) |
| X05 Rust 原件/恢复 | PARTIAL (A/B/C landed) | source_origins table+domain, HTTP origin metadata, archive EXPORT_TABLES incl provenance, export/restore round-trip test; 2 real bugs found+fixed; executor/restart deep slices remain open |
| X06 workers 格式 | PARTIAL | text/HTML/OCR(eng+chi_sim)/PDF/Office real evidence; scanned-page→OCR routing, media ASR (profile), dynamic-webpage open |
| X07 质量/公开核查 | PARTIAL/BLOCKED | offline golden metrics real (worker_quality); public retrieval BLOCKED_RESOURCE: sandbox child egress fails TLS EOF / HTTP 502 (evidence run 3855f5a1bd89) |
| X08 人类学习侧 | BLOCKED | depends on X03 default host + X07; donors registered (X02 wave 2) |
| X09 机器侧 | BLOCKED | depends on X07 + identity; donors registered |
| X10 迁移 | PARTIAL | legacy read-only inventory/export proven; demo semantic staging (notes→knowledge) with loss ledger, idempotent, 4 tests green (cd450ae); full legacy→vNext mapping + real DB qualification open |
| X11 同候选打包/旅程 | PARTIAL/BLOCKED | headless real-process chain evidenced across api/application/archive suites incl real Python worker (job_rejections, executor, attempts); Windows candidate packaging/install and GUI-visible journey NOT produced (Avalonia starter content; no installed-qualification) - honestly not claimed |
| X14 清理 | PARTIAL (wave-1 EXECUTED) | real census 66.6 GiB; deletion wave-1 freed 11,561,655,398 logical bytes (~10.77 GiB) w/ before/after manifests; post-delete regression 35 passed; retained root target/, .project-local caches (HOLD reasons recorded), .hermes NEVER |
| F01-F06 | DEFERRED_RETAINED | unchanged (frozen) |
| Q00/Q01 | NOT RUN | independent GPT audit per plan |

## Headless real-process journey chain (X11-adjacent evidence)

End-to-end real-process links verified at test level on this host: launch
auth (private stdin credential) -> Core HTTP -> durable job claim/attempt ->
real Python worker (UTF-8 hardened) -> loss receipts persisted -> archive
export/restore (incl source provenance). C# supervisor harness and C# silent
client -> Rust -> Python -> DB readback runs were recorded earlier on this
branch (0906 receipts: 30646350a2bb etc. under .project-local/runs). A
human-visible Windows packaged journey remains open and is not claimed.

## Known gaps / how to continue

1. Independent GPT audit (Q00/Q01) of the same candidate bytes.
2. Role-scope authority (X04/X05 open) -> then X08/X09 with DeepTutor host
   decision (needs upstream interactive UI on a machine with one) and an
   authorized cloud egress for X07's single real fact-check.
3. Full X10 semantic table map with real-user-DB consistent snapshot.
4. X11 packaging/install with the GUI once desktop is real product content.

## Rollback / reversal

- Each slice is a small commit on `codex/full-loop-0906`; revert per-commit
  (list in EXECUTION.md). No data deletion beyond the authorized X14 wave-1
  (rebuildable caches; manifest + rebuild commands recorded).
- `.hermes` and user data untouched and preserved.
