# AXM 语言架构审计任务包纳入清单

> Source examined: `ARCHEAXIS-CLEAN-SHEET-LANGUAGE-AUDIT-MIGRATION-TASKPACK-2026-09-01.md`.
>
> Status: ACTIVE TASK MAP. The source document is an audit/task proposal, not
> execution authority by itself. This map records the project decisions and
> current evidence that govern subsequent work.

## Adopted direction and non-negotiable boundary

The task pack's target composition is adopted as the long-horizon route:
Rust eventually owns authoritative domain truth, TypeScript/React remains the
product surface, and Python remains a replaceable parsing/AI sidecar. SQLite
and raw-first archive semantics remain in place. This is a staged migration,
not an all-Rust rewrite or a new product.

The active constraints remain unchanged:

- Windows and the existing Green distribution are the current product target.
  No version, tag, installer or GitHub Release is created by this migration.
- A domain aggregate has one writer at a time. Read shadows and differential
  reports are allowed; Python/Rust dual writes are forbidden.
- Python sidecars can emit only candidate/result artifacts and cannot decide
  verified truth, mastery, machine competence, approval, migration ownership
  or rollback.
- User-owned, private, or unlicensed material does not enter a repository
  golden corpus. Generated evidence remains under ignored `.hermes/`.

These constraints are already enforced by the active
[G0 migration freeze rules](AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md).

## Reconciled baseline

| Task-pack claim | Current project evidence | Task status |
| --- | --- | --- |
| `main@db13d0564ac2971d4b1eb3e3a5bff9c9256af313` is the migration source baseline | Git readback recorded in [Current Reality](CURRENT_REALITY_2026-09-01.md) | CONFIRMED |
| The public release is distinct from the current main tree | Public stable is `v0.6.14`; it remains immutable while maintenance stays on `main` | CONFIRMED |
| Current exact-SHA CI was unproved on 2026-09-01 | Run `33521144084` is now read back: `gateplan`, `lint`, `a0-gates` passed; 11 qualification jobs were skipped | PARTIAL — not full qualification |
| The Git-Bash-only `pwd -W` test entrypoint is a cross-platform defect | The direct `pwd -W` use was removed and its contract test passes locally | IMPLEMENTED_LOCAL; three-platform execution still unproved |
| Batch file intake has duplicated write orchestration | Batch routing now delegates to `app.workspace.service.ingest_local_file()` | IMPLEMENTED_LOCAL; the repository-wide ownership inventory remains incomplete |

## Incorporated task chain

### G0 — evidence gates before any new writer

| ID | Incorporated task | Current state / next exit evidence |
| --- | --- | --- |
| AXM-G0-001 | Bind a machine-readable baseline receipt to source/tree/locks, exact-SHA CI jobs, runtime and tests. | Receipt exists under ignored project evidence and documents partial CI. A 2026-09-02 force-full dispatch attempt returned GitHub Actions HTTP 403 because the configured PAT lacks workflow-dispatch access; the available in-app browser is signed out and no Chrome session is connected. Obtain a full-qualification exact-SHA run through an authorised GitHub session, plus a controlled Green product-path result; do not infer skipped jobs. |
| AXM-G0-002 | Maintain one non-contradictory current-state entry and link handoff/history to it. | Current Reality, Project Status and handoff top section were reconciled. The current-report generator and Golden Journey receipt default to no Release evidence, preventing v0.6.9 from being silently promoted; the separately read-back `reports/release/v0.6.14/release-evidence.json` is now the explicit current stable receipt. Related receipt/report/version/document regressions are `21 passed`. A repeatable document-to-live readback drift scan remains required before this gate can close. |
| AXM-G0-003 | Complete a rights-bound, raw-hash golden corpus plus fresh/existing workspace snapshots. | Project-authored TXT/HTML/DOCX/PPTX/XLSX/PDF/Canvas, screenshot OCR, WAV and MP4 fixtures are recorded. Fresh/existing workspace journey receipts that bind those hashes to schema/API/failure/performance readback remain required. |
| AXM-G0-004 | Keep the single-writer, rollback-first migration freeze. | ACTIVE. Green maintenance is a narrow exception only when it preserves the current writer and records targeted evidence. |

**G0 exit rule:** G1 may not introduce a production Rust writer until all four
G0 entry gates have evidence. Present local tests, partial CI, a fixture, or a
Green component smoke cannot be substituted for the missing gate.

### G1 — contracts and read-only skeleton, after G0 exit

| ID | Incorporated task | State and bounded deliverable |
| --- | --- | --- |
| AXM-G1-001 | Create a normal Rust workspace and eliminate cross-directory `#[path]` sharing through a shared crate. | PENDING. A 2026-09-02 diagnostic proves the current root shell (edition 2021) formats desktop-shell source reached through `#[path]`, while that shell is edition 2024; their Rustfmt import ordering conflicts. Resolve this through the shared-crate boundary, not by alternately reformatting the same files. It must leave current Windows behaviour unchanged and start with no production DB write path. |
| AXM-G1-002 | Freeze Contract v2 for Source, Anchor, Evidence, Claim, Learning Event, Machine Competence, Receipt and Error. | PENDING. Start from current Pydantic/OpenAPI objects and golden JSON fixtures; require strict unknown-field rejection and bidirectional round trips. |
| AXM-G1-003 | Define platform-neutral ports and isolate Windows implementations. | PENDING. The current Rust/Tauri shells are not domain writers; recovery I/O stays outside the domain core. |
| AXM-G1-004 | Use one cross-platform test launcher. | PARTIAL. The `pwd -W` repair is locally tested; prove the same selected command on Windows, Linux and macOS before closure. |

### G2–G7 — retain the DAG, do not start out of order

| Phase | Included scope | Start condition |
| --- | --- | --- |
| G2 | Rust read-only store, pure state-machine differential, diagnostic-only shadow projections. | G1 contracts and snapshot corpus are accepted. |
| G3 | Rust RawAsset/Source writer and OCFL export, with backup and rollback cutover. | Two candidate versions of zero-semantic-difference shadow evidence. |
| G4 | Standard anchors, evidence review state machine, provenance/receipts. | G3 source writer cutover and recovery prove safe. |
| G5 | Append-only human learning events, machine-competence firewall and explainable learning projections. | G4 evidence authority is proven. |
| G6 | Rust `/api/v2` BFF, versioned Python-sidecar protocol, removal of Python DB authority and route classification. | G5 is stable; old `/api/v1` remains rollback-compatible. |
| G7 | UI Contract v3, generated TS client, Windows DPI/accessibility matrix, offline fonts and one production Tauri host. | G6 public contract is stable. |

For every phase, the common Truth, Data, Contract, Security, Product,
Accessibility, Performance, Supply-chain and Release gates from the source
task pack apply. A failed gate keeps the old writer active and the new one
read-only; it never lowers truth semantics merely to advance the migration.

## Explicitly deferred, not silently dropped

- **G8:** macOS/Linux are technical-preview work only after Core stability;
  current work must not promote a successful compile to a supported product.
- **G9:** retirement of Python authority waits for at least two candidate
  releases after every relevant aggregate has a verified replacement.
- **GF:** WASI plugins, spatial-memory 2D-to-3D, Web and mobile companions
  remain future capability tracks. They do not compete with Windows pipeline,
  evidence and learning-loop qualification.

## Immediate execution order

1. Finish the remaining G0 evidence obligations, beginning with exact-SHA
   full qualification, a controlled Green launch/product-path smoke, and the
   missing rights-bound corpus inputs.
2. Complete the first-wave current-writer inventory beyond batch file intake;
   record consumer maps and rejection receipts for Evidence, Learning and
   Machine Competence before selecting any cutover target.
3. Only after the G0 exit rule, design and implement G1 as contracts plus
   read-only differential code; no Rust production writer is in scope then.
4. Advance one aggregate through G2–G7 at a time, retaining backups,
   fingerprints, rollback proof and an independently verified Windows path.

The binding lookup for current language ownership and legacy-name handling is
[`../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md`](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).

## Out of scope for this incorporation

This task-map update does not create crates, move Tauri code, add a database,
modify the release identity, publish an artifact, access user data, or trigger
cross-platform/mobile delivery. Those require the stated predecessor gates
and their own implementation changes.
