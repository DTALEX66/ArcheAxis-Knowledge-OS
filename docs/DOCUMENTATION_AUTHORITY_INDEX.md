# Documentation Authority Index

> **2026-10-09 当前执行覆盖**：用户已选择新 UI 优先任务及 G01；规范活动指针为 [AAOS-ACTIVE-EXECUTION](current/AAOS-ACTIVE-EXECUTION.json)，当前任务来源为 [UI 优先 TaskPack](taskpacks/aaos-ui-first-20261009/TASKPACK.md)，实际进度只读 [UI 执行记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)。规划原文的 PLANNING_READY / NOT_EXECUTED 是规划时状态，激活与实际结果由当前覆盖记录，不改写不可变原包。AAOS-01 Q00–Q15 台账仅记录该继承工作流，不代表新 UI 全队列；旧 R6/M0 整包顺序冻结，有效合同、单一 Rust Core writer、内容先保存及历史证据保留。V01 继续暂停。
> 当前新布局、架构和其余产品界面按新任务执行；默认 `blueprint`，配套 `blueprint-light`，旧 `black` / `white` / `cosmic` 仅为额外配色主题。五主题共用新布局、组件状态及统一语义颜色；一个主题内部的按钮、菜单、侧栏与正文保持一致。主题不更改 Core 配置或知识数据。
> 平台指令优先；平台范围内用户当前明确决定优先于项目旧描述。此文档同步不授予 commit、push、merge、发布、私人账户/会话访问或恢复暂停的云端任务权限；本机资源索引不是云端权限。


> Single entry point for human and agent document lookup. This index classifies
> a document; it never promotes a plan, handoff, test fixture, release tag, or
> historical snapshot into live product evidence.

## Current read order (2026-10-09)

Start at the [root entry](../AUTHORITY.md) (`AUTHORITY.md`): it is the navigational document, not a
second source of truth, and it routes through the canonical active-execution pointer to the selected task source and its scoped progress record
and the audit index. The entries below are what it routes to, in order.

1. [AGENTS](../AGENTS.md), [project contract](../PROJECT_CONTRACT.yaml) and
   [decision supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml).
   `PROJECT_CONTRACT.content_policy` is the canonical normative content/save,
   recognition-fidelity/professional-support and AI-use policy, validated by
   [its Schema](../.project/schemas/project-contract.schema.json). Policy text
   does not establish implementation or acceptance status.
2. Resolve the [active execution pointer](current/AAOS-ACTIVE-EXECUTION.json) first: the selected task source is [UI-first](taskpacks/aaos-ui-first-20261009/TASKPACK.md), and its actual progress is [UI execution](current/AAOS-UI-FIRST-EXECUTION-20261009.md). The immutable AAOS-01 (2026-10-04) specification remains an inherited contract under SUP-022, not the active whole-package queue.
   [R6 executor](authority/taskpack-0919-r6/EXECUTOR-START.md),
   [immutable TASKS](authority/taskpack-0919-r6/TASKS.json),
   [R6-EXECUTION](current/R6-EXECUTION.md), [R6-STATE](current/R6-STATE.json)
   and [M0 direction override](current/M0-DIRECTION-OVERRIDE-20260920.md)
   retain inherited constraints and their own historical receipts; they do not
   establish a parallel AAOS-01 execution queue.
   SUP-022 applies the owner-selected Tauri 2 + React/TypeScript/Vite refactor
   through the immutable [AAOS-01 execution specification](authority/taskpack-1004-aaos01/01_完整执行任务书.md)
   and [joint architecture rules](authority/taskpack-1004-aaos01/00_两包共同架构与交接规则.md).
   It preserves Rust Core as sole writer, isolated Python workers and R6/M0
   evidence/no-release boundaries. The existing
   [AAOS-01 current ledger](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md)
   is the single live Q00–Q15 progress record; old planning registries and dated
   handoffs do not create parallel state truth or override current requirements.
   A recorded drift and branch/path audit is the dated
   [REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923](current/REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md)
   snapshot; it is not live Git truth after 2026-09-23. The older
   [DOCUMENTATION-DRIFT-AUDIT-20260923](current/DOCUMENTATION-DRIFT-AUDIT-20260923.md)
   is a frozen audit-time snapshot, not current Git truth.
   The [2026-09-23 branch table](current/BRANCH-DISPOSITION-CURRENT-20260923.md)
   and [2026-09-23 project-local volume inventory](current/PROJECT-LOCAL-VOLUME-AUDIT-20260923.md)
   are dated snapshots; re-read refs and filesystem metadata before making
   current claims or any cleanup decision.
   The [2026-09-27 backend integration](current/SEPTEMBER-BACKEND-INTEGRATION-20260927.md)
   and [consolidation readback](current/SEPTEMBER-CONSOLIDATION-READBACK-20260927.md)
   record this delivery and exact-SHA evidence; neither replaces R6/M0 or live Git.
   The [2026-09-25 lineage readback](current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md),
   [2026-09-26 cloud handoff](current/AAOS-CLOUD-AUDIT-HANDOFF-20260926.md) and
   [takeover checkpoint](current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md)
   are dated snapshots. Their branch counts, defects, known CI and permission
   limits describe those times, not the current repository. Preserve original SHAs.
   [Historical consolidation](history/branch-donors/README.md) and the
   [document migration manifest](history/DOCUMENT-CONSOLIDATION-20260927.json)
   retain recovery and exact-path disposition evidence. No record here grants
   a release, Green replacement or further deletion by itself.
   R5/R3/R2 handoffs and branch records are historical receipts only. Before
   using local resources, read the [shared resource path index](SHARED_RESOURCE_PATH_INDEX.md).
3. [Language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md),
   [directory authority](DIRECTORY_AUTHORITY_INDEX.md), and
   [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md).
4. Historical evidence below, bound to its original date and tested SHA.

The old G0 shadow-cutover, legacy React/Tauri default, R5 taskpacks and R2/R3 plans
are superseded by the R6 TaskPack and M0 overlay. Their evidence remains
historical and is never a current execution queue. SUP-022's formal Tauri/Core
refactor does not reactivate the legacy Python backend or the old G0 sequence.

## Five routing questions, one existing file each (2026-10-08)

This table adds no new authority: every answer is a file that already existed before this batch.
It exists so a reader can resolve the five standing questions from this index alone.

| Question | Resolves to | Why that file and no other |
| --- | --- | --- |
| What do we execute now? | [active execution pointer](current/AAOS-ACTIVE-EXECUTION.json) | Resolves the selected UI task source and current UI progress; AAOS-01/R6/M0 are inherited constraints and scoped evidence, not parallel queues. |
| What tasks are still open? | [UI progress](current/AAOS-UI-FIRST-EXECUTION-20261009.md) plus [inherited Q ledger](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md) | These records have distinct UI and Q00–Q15 scopes. Dated registers such as `current/AAOS-OPEN-WORK-REGISTER-20261001.md` give only their own day's view and now say so. |
| Where are implementation and evidence? | [coverage matrix](current/AAOS-COVERAGE-MATRIX-20261006.md) plus [audit snapshot](current/AAOS-AUDIT-SNAPSHOT-20261006.json) | The matrix maps CAP/Q/F/I to its landing point; the snapshot carries observed_at, SHA, command and exit code. Chain receipts live in [LIVE-CHAIN-RECEIPTS.json](current/receipts/LIVE-CHAIN-RECEIPTS.json). Status is read from tests and receipts, never from document wording. |
| Where do external tools and models resolve? | [shared resource path index](SHARED_RESOURCE_PATH_INDEX.md) plus [external dependency boundary](environment/EXTERNAL_DEPENDENCIES.md) | Machine tool/model roots resolve in the first, product-internal model and tool registries (`config/models.yaml`, `config/tools.yaml`) in [the configuration authority index](CONFIGURATION_AUTHORITY_INDEX.md). Neither is agent provider routing. |
| Which material is history only? | [docs/history/](history/) plus the section below | Anything dated and superseded lives here or is listed below; the [relocation manifest](history/DOCUMENT-CONSOLIDATION-20260927.json) gives the exact path, hashes and rollback for every moved record. |

## Historical read order and evidence map

1. [Project operating boundary](../AGENTS.md) and the
   [configuration authority index](CONFIGURATION_AUTHORITY_INDEX.md).
2. [R6 direction reconciliation](current/R6-DIRECTION-RECONCILIATION-20260920.md),
   [R6 execution](current/R6-EXECUTION.md), and
   [M0 direction override](current/M0-DIRECTION-OVERRIDE-20260920.md) for their
   historical baseline and inherited constraints only; their whole-package execution sequence is frozen.
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
   historical; use the active-execution pointer and current authority for present triage.
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
| Historical capability model and current execution state | [historical capability snapshot](truth/CURRENT_STATE_TRUTH.md) + [R6 state](current/R6-STATE.json) + [R6 execution](current/R6-EXECUTION.md) + [M0 priority](current/M0-DIRECTION-OVERRIDE-20260920.md) | `CURRENT_STATE_TRUTH.md` is the 2026-08-09 historical model only; its execution claims are superseded. R6/M0 retain inherited contracts and historical receipts; the active-execution pointer resolves the current queue. |
| Frozen task baseline | [Frozen execution baseline](truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md) | Frozen; do not rewrite |
| Active forward work | [active pointer](current/AAOS-ACTIVE-EXECUTION.json) + [UI-first task source](taskpacks/aaos-ui-first-20261009/TASKPACK.md) + [UI progress](current/AAOS-UI-FIRST-EXECUTION-20261009.md) | Owner activation overlay; planning text is preserved and is not implementation evidence |
| Preceding pack (constraints and receipts inherited) | [R6 executor](authority/taskpack-0919-r6/EXECUTOR-START.md) + [R6 execution](current/R6-EXECUTION.md) + [M0 overlay](current/M0-DIRECTION-OVERRIDE-20260920.md) | R6 is the preceding pack, not the current one; its contracts, evidence rules and the M0 priority overlay remain in force as inherited constraints |
| Current formal host and inherited AAOS-01 increment | [SUP-022](../DECISION_SUPERSESSION_LEDGER.yaml) + [1004 specification](authority/taskpack-1004-aaos01/01_完整执行任务书.md) + [existing AAOS-01 ledger](current/AAOS01-Q00-Q15-LEDGER-FINAL-20261005.md) | Formal Tauri/React host and Rust Core; inherited specification is not a completion receipt |
| Content/save and AI-use policy | [Project contract](../PROJECT_CONTRACT.yaml) `content_policy` + [architecture explanation](architecture/CURRENT_ARCHITECTURE.md) | Normative; actual implementation and tests remain separately evidenced |
| Drift / branch / output audit | [2026-09-23 receipt](current/REPOSITORY-DRIFT-CURRENT-RECEIPT-20260923.md) + [frozen audit](current/DOCUMENTATION-DRIFT-AUDIT-20260923.md) | Dated evidence only; neither authorizes deletion or merge |
| Branch disposition | [2026-09-23 branch table](current/BRANCH-DISPOSITION-CURRENT-20260923.md) | Dated read-only snapshot; refresh from live refs. Merge/delete requires separate owner gate |
| Dated local branch/worktree/data-lineage snapshot | [2026-09-25 readback](current/AAOS-LOCAL-REPOSITORY-LINEAGE-READBACK-20260925.md) | Cached refs and metadata only; remote/content provenance unknown; no cleanup/merge authorization |
| Project-local volume | [2026-09-23 volume audit](current/PROJECT-LOCAL-VOLUME-AUDIT-20260923.md) | Dated size classification only; refresh before cleanup; no bulk cleanup authorization |
| Language migration | [Language-audit adoption](current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md) | Historical map; React/TypeScript product-surface target superseded by R6/M0; dated G0 evidence only |
| Language ownership and compatibility naming | [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) | Binding migration boundary |
| Directory migration and cleanup | [Directory-migration adoption](current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md) | Historical proposal; output-root and UI-host targets superseded; existing-data migration and deletion remain blocked pending manifests and Owner Gates |
| Directory topology and classification | [Directory authority](DIRECTORY_AUTHORITY_INDEX.md) | Binding path classification |
| Historical cleanup/index/language snapshot | [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md) | 2026-09-03 evidence only; old product-shell and G0 queue superseded by R6/M0 |
| Historical recurring-failure diagnostics | [Operational issue archive](current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md) | Dated diagnostic archive (2026-09-04); statuses/G0 gates are historical; use the active-execution pointer for current execution |
| Evidence chronology | [Execution status log](truth/EXECUTION_STATUS_LOG.md) | Append-only evidence log |
| Release facts | [Release ledger](RELEASE_LEDGER.md) | Historical/public receipt index |
| Verification policy | [Verification policy](VERIFICATION_POLICY.md) | Binding policy |

## Reference and archive classes

| Location | Meaning | Citation rule |
| --- | --- | --- |
| [architecture/](architecture/) | Current architecture plus imported capability analysis | Cite only as design/reference, not live behavior |
| [architecture/imported-designs/](architecture/imported-designs/) | Preserved upstream/reference inputs | Cite source and absorption status; do not copy claims into current truth |
| [taskpacks/](taskpacks/) | Current and historical instructions | The selected UI task source is resolved by the active-execution pointer; immutable older packs retain inherited contracts and historical evidence |
| [current/](current/) | Scoped current UI progress alongside inherited Q records and explicitly dated historical snapshots | Check date and status before using |
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
- `current/TASK_GRAPH_V2.yaml` and `current/SCOPE_LEDGER_V2.yaml` (historical execution fields, not the active queue)
- `current/SESSION-RESTART-2026-09-12.md` (retired R3.1 handoff; retained for existing historical links)
- `current/CONTINUATION_HANDOFF_2026-09-03.md`
- `current/CURRENT_REALITY_2026-09-01.md`
- `current/FRONTEND_CONSOLIDATION_V1_2026-08-28.md`
- `current/UI_PRODUCTION_ADOPTION_V3_2026-08-27.md`
- `current/AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md`
- `current/UI_V3_PRODUCT_ROADMAP.md` (mixed dated record: its current overlay resolves the new UI design and themes; its B10/Avalonia and P0R/P0.5/P1/P2 statements are explicitly retained historical snapshots)
- `truth/ARCHITECTURE_FINAL.md` (2026-08 architecture proposal; its shell diagram is historical, not the SUP-022 formal Tauri/Core implementation)
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
preserve them as evidence and follow the active-execution pointer above.

The three superseded AAOS-01 ledgers `AAOS01-Q00-Q15-LEDGER-20261005.md`,
`AAOS01-Q00-Q15-LEDGER-DELTA-20261005-R216.md` and `AAOS01-FIRST-PACKAGE-LEDGER.md`
have been archived byte-for-byte under `history/aaos01-20261005/`; their original
`current/` paths retain compatibility entries pointing to the originals and the
single current FINAL ledger. Exact source/target hashes, consumers and recovery
are appended to the existing [consolidation manifest](history/DOCUMENT-CONSOLIDATION-20260927.json)
with execution date 2026-10-05. Earlier manifest rows and the existing Q02
supersession headers remain unchanged. No immutable package or raw receipt was deleted.

### 2026-10-08 relocation batch

A second batch moved 63 dated records out of `current/` into `history/`: the 48 records that
already carried `historical: true` plus `superseded-by:` (the AAOS-01 per-step narrative series,
into `history/aaos01-20261005/`), and the superseded members of the UI handoff, goal/state,
cloud-audit, UI asset-audit, R5 handoff, R5 audit-delta and DSH backend audit groups. Each moved
markdown record carries one dated archival marker line naming the surviving current entry; JSON
records moved byte-for-byte with no content change. Nothing was deleted and no record was rewritten.
Source path, target path, byte counts, pre-move and post-move SHA-256, rollback and verification
are 63 rows appended to the same [consolidation manifest](history/DOCUMENT-CONSOLIDATION-20260927.json)
with `execution_date: 2026-10-08`; the 20 rows from earlier rounds keep their own dates and SHAs.
`current/` therefore holds 342 tracked files instead of 405, and `history/` 230 instead of 167.

### Duplicate groups that could not be collapsed by relocation at this baseline

Relocating these would break a citation inside a surface this batch is not permitted to edit, so
they stay in `current/` as dated records rather than being rewritten or left dangling:

| Record or group | Held in place by |
| --- | --- |
| `current/AXR_060_*` (11 files) | `LEGACY_MANIFEST.yaml` and `docs/authority/legacy/T17-inventory-audit-2026-09-05.json`, plus `tests/test_axr060_completion_audit.py` |
| `current/AAOS-UI-COVERAGE-MATRIX-20261001.md`, `current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md` | Root `AUTHORITY.md` routes to both and declares them measured-at-the-time records to preserve verbatim |
| `current/AAOS-VISUAL-QA-20261001.md`, `current/AAOS-UI-MASTER-ASSET-AUDIT-20261001.md` | `current/AAOS-ALL-TASKS-DISPOSITION-20261001.csv` |
| `current/AAOS-UI-COMMERCIAL-AUDIT-20260923.md`, `current/AAOS-UI-SUITE-COVERAGE-20260923.md`, `current/AAOS-UI-SUITE-ABSORPTION-AUDIT-20260922.md`, `current/AAOS-P3-UI-PUSH-SUMMARY-20260922.md`, `current/BRANCH-DISPOSITION-CURRENT-20260923.md`, `current/AAOS-BRANCH-DISPOSITION-REVIEW-20260925.json` | `current/AAOS-BRANCH-COMMIT-PATH-AUDIT-20260925.json`, and for two of them `current/R6-EXECUTION.md` |
| `current/AAOS-UI-ASSET-MANIFEST-20261001.json` | `current/AAOS-UI-COVERAGE-MATRIX-20261001.md`, whose root-declared preservation forbids rewriting its citation |
| `current/DSH-DP-TASK-ASSIGNMENTS-20260925.md` | `current/dsh-review/` records |
| `current/AAOS-CLOUD-AUDIT-RECONCILIATION-20260923.md` | `tests/test_axr060_completion_audit.py` |
| `current/AAOS-CLOUD-AUDIT-HANDOFF-20260926.md`, `current/AAOS-DSH-TAKEOVER-CHECKPOINT-20260926.md` | `tests/test_ci_classifier.py` and `.worklab/project-validation.v1.yaml` |
| `current/AAOS_VISUAL_QA.md`, `current/DSH-GOVERNANCE-ALIGNMENT-20260927.md` | `workspace/intake/` notes, outside any path this batch may edit |
| `current/BRANCH-DISPOSITION-20260918.md`, `current/R5-VERIFICATION-SUMMARY-20260914.md` | `current/R5-EXECUTION.md` and `current/R5-STATE.json` |
| `current/DSH-BACKEND-HANDOFF-20260927.md` | `current/R6-EXECUTION.md` |
| `current/DSH-BACKEND-CONTRACT-20260927.md` | Rust contract tests under `crates/archeaxis-api/tests/` |
| `current/DSH-BACKEND-EVIDENCE-20260927.json` | `current/DSH-BACKEND-GAP-MAP-20260927.md` |

Closing these needs a batch authorised to edit the citing surfaces first; it is not a reason to
rewrite the cited records. The 100 further unreferenced AAOS-01 step records that carry no
`historical: true` marker were also left in place: relocating them would mean declaring a
supersession the repository has not yet stated, which is an Owner decision, not a consolidation.

## Cleanup and migration safety

- Tracked historical documents may be moved only after a path/hash/reference
  manifest, compatibility-link update and regression check. They are not
  disposable merely because their date is old.
- The formal route under SUP-022 is Tauri 2/React with finite host commands, a separate Rust-owned vNext database, and
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

## 2026-09-29 planning / cloud comparison snapshot

The full source package, its unpacked contents, and the two supplied reports are archived at [planning-blueprint-absorption/2026-09-29](history/planning-blueprint-absorption/2026-09-29/README.md). This is a dated historical/reference snapshot, not a new task authority: use the active-execution pointer for present work; R6/M0 retain inherited contracts and historical receipts. The archive includes a source/hash manifest, an authority crosswalk, and an exact superseded-document cleanup audit. Its GitHub/CI/branch facts are time-bound and must be re-read before use.

## H01 独立来源派生追溯

[H01 来源追溯](current/AAOS-H01-SOURCE-TRACE-20261009.md)与[机器投影](current/AAOS-H01-SOURCE-TRACE-20261009.json)保留426个来源定位键及真实源字节绑定。它们不是Authority或第二进度数据库；本地结构检查不证明186细项语义覆盖或产品资格。未核实的语义保持UNVERIFIED，执行结果仍读当前UI记录。

## UI深化设计增量 · 2026-10-10

[设计吸收与原任务验收增量](current/AAOS-UI-DESIGN-INCREMENT-20261010.md)：用户指定两份TXT与后续ZIP/10成员已按字节归档，107条原规格有逐记录任务映射，新设计沿当前权威链进入既有UI切片；不可变TaskPack和产品实现资格分开。

[CB02/UF07本地阶段源码与证据](current/receipts/AAOS-TEACHING-STAGE-20261010.json)归当前UI执行记录，区分Core集成、模拟host视觉、旧版本独立回归与未执行安装/真人资格；不是第二进度库或云端发布证明。

[UF12画布本地源码与证据](current/receipts/AAOS-CANVAS-STAGE-20261010.json)归当前UI执行记录：表达修订/媒体引用/真实Core重启与模拟浏览器分账；不授予高级引擎、安装/真人或发布资格。


[CB03/UF08集合与研究本地源码和证据](current/receipts/AAOS-RESEARCH-STAGE-20261010.json)归UI执行记录，限定本地交付子项；未实施F02细项/来源平台等价、安装/真人/云端分别列明。当前产品代码只在指定writer，主根治理资料不证明代码合并。

## 资源与模板资格登记 · 2026-10-10

[本页供体资格登记](current/AAOS-RESOURCE-QUALIFICATION-20261010.json)覆盖既有68个稳定身份与115条原冲突，列出本页所选9项及其版本、许可、权限、运行、实测与冻结条件。历史交叉登记保留原始结论；当前宿主握手、锁文件与官方许可证HEAD读回分别记账，不互相推导installed或发布资格。递归来源指纹在当前执行记录指定的唯一产品writer运行 `scripts/contracts/generate_resource_catalog.py --check` 核验。主根镜像登记与资料入口，不作为产品源码资格检出；页面投影不是第二权威或第二状态库。

执行状态仍读[当前UI记录](current/AAOS-UI-FIRST-EXECUTION-20261009.md)与活动指针；TaskPack原规划状态不改写。SBOM/NOTICE生成及模板回归属于本地工程证据，升级、退出、混合导入取消、正式旧库迁移和安装态验收依各自合同另验；未核实项保留明确缺口。
