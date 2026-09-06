# Documentation Authority Index

> Single entry point for human and agent document lookup. This index classifies
> a document; it never promotes a plan, handoff, test fixture, release tag, or
> historical snapshot into live product evidence.

## Current read order (2026-09-06)

1. [AGENTS](../AGENTS.md), [project contract](../PROJECT_CONTRACT.yaml) and
   [decision supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml).
2. [Full Loop execution](authority/taskpack-0906/EXECUTION.md).
3. [Language authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md),
   [directory authority](DIRECTORY_AUTHORITY_INDEX.md), and
   [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md).
4. Historical evidence below, bound to its original date and tested SHA.

The old G0 shadow-cutover and React default are superseded by SUP-003/006/007.
The 2026-09-04 Current Reality record and R2 plan below are historical, not the
current vNext task queue. Keep their evidence intact.

## Historical read order and evidence map

1. [Project operating boundary](../AGENTS.md) and the
   [configuration authority index](CONFIGURATION_AUTHORITY_INDEX.md).
2. [Current Reality](current/CURRENT_REALITY_2026-09-01.md) for the reconciled
   current baseline, then [Project Status](PROJECT_STATUS.md) for the product
   capability and verification summary.
3. [Current task pack](taskpacks/AXR-FINAL-20260826-R2-OSS-FAST-TRACK.md) for
   forward execution only.
4. [Migration freeze rules](current/AXM_G0_MIGRATION_FREEZE_RULES_2026-09-02.md)
   and the [first-wave ownership map](current/AXM_G0_OWNER_MAP_2026-09-02.md)
   before changing a writer, language boundary, directory, runtime data, or
   desktop host.
   Consult the [G0 evidence gap register](current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md)
   for the remaining no-go gates and the [AX-DIR-010 inventory schema](current/AX_DIR_010_INVENTORY_SCHEMA.md)
   before proposing a directory move or deletion.
5. [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
   before changing a Windows UI build, executable, Green deployment or GUI
   launcher.
6. [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) before
   changing a language boundary, a test/runtime environment variable, sidecar
   role or any writer.
7. [Directory authority](DIRECTORY_AUTHORITY_INDEX.md) before normalizing,
   archiving, moving or cleaning a repository path.
8. [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
   for the current, evidence-bound cleanup, index and language-boundary queue.
9. [Operational issue archive](current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md)
   for recurring failure triage, confirmed root causes and the first safe
   diagnostic command. It is a navigation aid, not a substitute for the
   evidence records it links.
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
| Live/current reconciliation | [Current Reality](current/CURRENT_REALITY_2026-09-01.md) | Current, evidence-bound |
| Product capability and debt | [Project Status](PROJECT_STATUS.md) | Current summary |
| Frozen task baseline | [Frozen execution baseline](truth/FROZEN_EXECUTION_BASELINE_v1_2026-08-09.md) | Frozen; do not rewrite |
| Active forward work | [R2 OSS fast-track](taskpacks/AXR-FINAL-20260826-R2-OSS-FAST-TRACK.md) | Current task pack |
| Language migration | [Language-audit adoption](current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md) | Planned; G0-gated |
| Language ownership and compatibility naming | [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md) | Binding migration boundary |
| Directory migration and cleanup | [Directory-migration adoption](current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md) | Planned; delete gate blocked |
| Directory topology and classification | [Directory authority](DIRECTORY_AUTHORITY_INDEX.md) | Binding path classification |
| Current cleanup/index/language queue | [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md) | Current, evidence-bound |
| Recurring operational failures and first-response diagnostics | [Operational issue archive](current/OPERATIONAL_ISSUE_ARCHIVE_2026-09-04.md) | Current triage index; follow linked evidence for claims |
| Evidence chronology | [Execution status log](truth/EXECUTION_STATUS_LOG.md) | Append-only evidence log |
| Release facts | [Release ledger](RELEASE_LEDGER.md) | Historical/public receipt index |
| Verification policy | [Verification policy](VERIFICATION_POLICY.md) | Binding policy |

## Reference and archive classes

| Location | Meaning | Citation rule |
| --- | --- | --- |
| [architecture/](architecture/) | Current architecture plus imported capability analysis | Cite only as design/reference, not live behavior |
| [architecture/imported-designs/](architecture/imported-designs/) | Preserved upstream/reference inputs | Cite source and absorption status; do not copy claims into current truth |
| [taskpacks/](taskpacks/) | Current and historical instructions | Only the R2 pack is current; frozen addenda retain capability constraints |
| [current/](current/) | Reconciliations, G0 gates and active maintenance handoffs | Check date and status before using |
| [history/](history/) | Historical snapshots | Never cite as current state |
| Root `HANDOFF_*` and `SUMMARY_*` records | Legacy historical records awaiting a hash/reference-bound archive move | History only; do not use as task authority |

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
