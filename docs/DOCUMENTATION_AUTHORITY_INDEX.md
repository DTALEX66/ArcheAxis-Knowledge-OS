# Documentation Authority Index

> Single entry point for human and agent document lookup. This index classifies
> a document; it never promotes a plan, handoff, test fixture, release tag, or
> historical snapshot into live product evidence.

## Current read order (2026-09-25)

1. [AGENTS](../AGENTS.md), [project contract](../PROJECT_CONTRACT.yaml) and
   [decision supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml).
2. [R6 executor](authority/taskpack-0919-r6/EXECUTOR-START.md) and
   [immutable TASKS](authority/taskpack-0919-r6/TASKS.json) — the single active
   package, `AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6`. Live progress is
   [R6-EXECUTION](current/R6-EXECUTION.md) and [R6-STATE](current/R6-STATE.json).
   The current priority overlay is
   [M0 direction override](current/M0-DIRECTION-OVERRIDE-20260920.md).
   The latest recorded drift and branch/path audit is the dated
   [REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923](current/REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md)
   snapshot; it is not live Git truth after 2026-09-23. The older
   [DOCUMENTATION-DRIFT-AUDIT-20260923](current/DOCUMENTATION-DRIFT-AUDIT-20260923.md)
   is a frozen audit-time snapshot, not current Git truth.
   The [2026-09-23 branch table](current/BRANCH-DISPOSITION-CURRENT-20260923.md)
   and [2026-09-23 project-local volume inventory](current/PROJECT-LOCAL-VOLUME-AUDIT-20260923.md)
   are dated snapshots; re-read refs and filesystem metadata before making
   current claims or any cleanup decision.
  The [2026-09-25 local repository/data-lineage readback](current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md)
  is an append-only dated audit with a 2026-09-26 follow-up: use its latest
  section for the seven live remote heads, PR readback, current branch cleanup
  findings and visible spill lower bound. Earlier embedded snapshots retain
  their historical values. The readback does not authorize remote deletion,
  merge, or data movement.
  The [2026-09-26 cloud audit handoff](current/AAOS-CLOUD-AUDIT-HANDOFF-20260926.md)
  is the entry point for an external auditor with GitHub access only: it lists
  the exact head SHA, the exact-SHA CI runs and which jobs were skipped, each
  change and how to verify it, and the known defects left unfixed. Its session
  log is [AAOS-DSH-TAKEOVER-CHECKPOINT-20260926](current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md)
  and the branch-consolidation record with recovery tips is
  `docs/history/branch-donors/README.md` (outside this index's link scope).
  These are working records for this session, not current authority: they do not
  authorize a release, a Green replacement, or a `main` merge.
   R5/R3/R2 handoffs and branch records are historical receipts only. Before
   using local resources, read the [shared resource path index](SHARED_RESOURCE_PATH_INDEX.md).
3. [Language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md),
   [directory authority](DIRECTORY_AUTHORITY_INDEX.md), and
   [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md).
4. Historical evidence below, bound to its original date and tested SHA.

The old G0 shadow-cutover, React/Tauri default, R5 taskpacks and R2/R3 plans
are superseded by the R6 TaskPack and M0 overlay. Their evidence remains
historical and is never a current execution queue.

## Historical read order and evidence map

1. [Project operating boundary](../AGENTS.md) and the
   [configuration authority index](CONFIGURATION_AUTHORITY_INDEX.md).
2. [R6 direction reconciliation](current/R6-DIRECTION-RECONCILIATION-20260920.md),
   [R6 execution](current/R6-EXECUTION.md), and
   [M0 direction override](current/M0-DIRECTION-OVERRIDE-20260920.md) for the
   current baseline and forward execution.
3. Historical snapshots only for dated evidence: [Current Reality](current/CURRENT_REALITY_2026-09-01.md),
   [Project Status](PROJECT_STATUS.md), and frozen frontend/cloud audit records.
   They do not define the current shell, routes, live Git state or execution order.
4. The [migration freeze rules](current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md),
   [first-wave ownership map](current/AXM_G0_OWNER_MAP_2026-09-02.md), and
   [G0 evidence gap register](current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md)
   are dated historical evidence; their old G0 cutover sequence is superseded
   by R6/M0 and the language-boundary authority. For a present exact-path move
   or deletion, use the [AX-DIR-010 inventory schema](current/AX_DIR_010_INVENTORY_SCHEMA.md)
   together with current directory authority and the applicable Owner Gate.
5. [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
   before changing a Windows UI build, executable, Green deployment or GUI
   launcher.
6. [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) before
   changing a language boundary, a test/runtime environment variable, sidecar
   role or any writer.
7. [Directory authority](DIRECTORY_AUTHORITY_INDEX.md) before normalizing,
   archiving, moving or cleaning a repository path.
8. [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
   as a frozen 2026-09-03 snapshot only; its old shell and G0 queue are
   superseded by R6/M0 and current authority indexes.
9. [Operational issue archive](current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md)
   as a dated diagnostic snapshot only. Its issue statuses and G0 gates are
   historical; use R6/M0 and current authority for present triage.
10. [Truth spine](truth/README.md) for frozen baselines and append-only evidence.

User instructions and the project `AGENTS.md` override every repository
document. A current-state record does not prove an installed runtime, exact-SHA
CI, release, or user-data migration unless it names that evidence layer.

## Authority map

| Need | Canonical record | Classification |
| --- | --- | --- |
| Product identity and naming | [Naming contract](truth/NAMING_CONTRACT_V2.md) | Binding |
| Runtime/default configuration | [Configuration authority index](CONFIGURATION_AUTHORITY_INDEX.md) | Binding |
| Windows UI build and Green deployment | [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md) | Binding delivery map; live state still needs readback |
| Live/current reconciliation | Live Git/runtime readback; [2026-09-23 repository drift receipt](current/REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md) is dated evidence | The receipt is stale for current facts; re-read live values |
| Historical capability model and current execution state | [historical capability snapshot](truth/CURRENT_STATE_TRUTH.md) + [R6 state](current/R6-STATE.json) + [R6 execution](current/R6-EXECUTION.md) + [M0 priority](current/M0-DIRECTION-OVERRIDE-20260920.md) | `CURRENT_STATE_TRUTH.md` is the 2026-08-09 historical model only; its execution claims are superseded. R6/M0 are the current execution authorities. |
| Frozen task baseline | [Frozen execution baseline](truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md) | Frozen; do not rewrite |
| Active forward work | [R6 executor](authority/taskpack-0919-r6/EXECUTOR-START.md) + [R6 execution](current/R6-EXECUTION.md) + [M0 overlay](current/M0-DIRECTION-OVERRIDE-20260920.md) | Current task pack and priority overlay |
| Drift / branch / output audit | [2026-09-23 receipt](current/REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md) + [frozen audit](current/DOCUMENTATION-DRIFT-AUDIT-20260923.md) | Dated evidence only; neither authorizes deletion or merge |
| Branch disposition | [2026-09-23 branch table](current/BRANCH-DISPOSITION-CURRENT-20260923.md) | Dated read-only snapshot; refresh from live refs. Merge/delete requires separate owner gate |
| Latest local branch/worktree/data-lineage snapshot | [2026-09-25 readback](current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md) | Cached refs and metadata only; remote/content provenance unknown; no cleanup/merge authorization |
| Project-local volume | [2026-09-23 volume audit](current/PROJECT-LOCAL-VOLUME-AUDIT-20260923.md) | Dated size classification only; refresh before cleanup; no bulk cleanup authorization |
| Language migration | [Language-audit adoption](current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md) | Historical map; React/TypeScript product-surface target superseded by R6/M0; dated G0 evidence only |
| Language ownership and compatibility naming | [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) | Binding migration boundary |
| Directory migration and cleanup | [Directory-migration adoption](current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md) | Historical proposal; output-root and UI-host targets superseded; existing-data migration and deletion remain blocked pending manifests and Owner Gates |
| Directory topology and classification | [Directory authority](DIRECTORY_AUTHORITY_INDEX.md) | Binding path classification |
| Historical cleanup/index/language snapshot | [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md) | 2026-09-03 evidence only; old product-shell and G0 queue superseded by R6/M0 |
| Historical recurring-failure diagnostics | [Operational issue archive](current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md) | Dated diagnostic archive (2026-09-04); statuses/G0 gates are historical; use R6/M0 for current execution |
| Evidence chronology | [Execution status log](truth/EXECUTION_STATUS_LOG.md) | Append-only evidence log |
| Release facts | [Release ledger](RELEASE_LEDGER.md) | Historical/public receipt index |
| Verification policy | [Verification policy](VERIFICATION_POLICY.md) | Binding policy |

## Reference and archive classes

| Location | Meaning | Citation rule |
| --- | --- | --- |
| [architecture/](architecture/) | Current architecture plus imported capability analysis | Cite only as design/reference, not live behavior |
| [architecture/imported-designs/](architecture/imported-designs/) | Preserved upstream/reference inputs | Cite source and absorption status; do not copy claims into current truth |
| [taskpacks/](taskpacks/) | Current and historical instructions | R6 under `authority/taskpack-0919-r6/` is current; older packs retain historical constraints only |
| [current/](current/) | Reconciliations, G0 gates and active maintenance handoffs | Check date and status before using |
| [history/](history/) | Historical snapshots | Never cite as current state |
| Root `HANDOFF_*` and `SUMMARY_*` records | Legacy historical records awaiting a hash/reference-bound archive move | History only; do not use as task authority |
| [2026-09-03 G0 implementation plan](superpowers/plans/2026-09-03-runtime-authority-and-language-g0.md) | Dated superseded implementation plan | React/Tauri shell and pre-R6 gate sequence are historical; do not execute it |

## Explicitly superseded current-path documents

The following files remain in `current/` only because they are dated evidence or
because historical plans still link to them. They are not part of the current
authority chain and must not be used to infer the desktop shell, Green target,
release status, or task order:

- `current/AXR_060_COMPLETION_AUDIT_2026-08-23.md`
- `current/AXR_060_401_UNIFIED_CLIENT_HANDOFF_2026-08-24.md`
- `current/CURRENT_PRODUCT_PLAN_V2.md`
- `current/CONTINUATION_HANDOFF_2026-09-03.md`
- `current/CURRENT_REALITY_2026-09-01.md`
- `current/FRONTEND_CONSOLIDATION_V1_2026-08-28.md`
- `current/UI_PRODUCTION_ADOPTION_V3_2026-08-27.md`
- `current/AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md`
- `current/UI_V3_PRODUCT_ROADMAP.md` (mixed dated record: its opening current visual-authority statements align with C#/Avalonia; React/Tauri page inventory and P0R/P0.5/P1/P2 execution plans are historical snapshots, not current Avalonia implementation status)
- `truth/ARCHITECTURE_FINAL.md` (2026-08 architecture proposal; its Tauri/React shell diagram is historical and superseded by current C#/Avalonia authority)
- `truth/AUTHORITY_CONTRACT.md` (2026-08 authority-order snapshot; its frozen-baseline task-source rule is superseded by R6/M0)
- `current/DSH-COMPLETION-REPORT-20260918.md`
- `current/HERMES-FULL-AUDIT-PROMPT-20260918.md`
- `current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md` (historical task map; product-surface target superseded by R6/M0)
- `current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md` (historical proposal; output-root and UI-host target superseded by current project authority)
- `ABSORPTION_EXECUTION_MATRIX.md` (2026-08-11 frozen snapshot)
- `PROJECT_STATUS.md`
- `../HERMES_HANDOFF.md`
- `superpowers/specs/2026-08-23-six-space-closed-loop-design.md`

Their status banners are intentional. Physical relocation or deletion requires a
separate path/hash/reference manifest and compatibility-link update; until then,
preserve them as evidence and follow the R6/M0 files above.

## Cleanup and migration safety

- Tracked historical documents may be moved only after a path/hash/reference
  manifest, compatibility-link update and regression check. They are not
  disposable merely because their date is old.
- The formal route is Avalonia/C#, a separate Rust-owned vNext database, and
  isolated Python workers. Legacy data retains its existing writer until
  validated migration; no shared database or dual write.
- No Green `data`, runtime database, ignored evidence, compatibility shim,
  frontend tree or desktop tree may be deleted under documentation cleanup.
- New development files belong under ignored `.project-local/`; `.hermes` is
  preserved mixed legacy material. Git-object cleanup
  waits for all Git writers to stop and for reachable/unreachable object review.

## Operational links

- [Documentation navigation](README.md)
- [Current architecture](architecture/CURRENT_ARCHITECTURE.md)
- [External dependency boundary](environment/EXTERNAL_DEPENDENCIES.md)
- [Imported-design reference index](architecture/imported-designs/README.md)
- [Historical snapshot index](history/pre-v0.6.7-current-snapshots/README.md)
