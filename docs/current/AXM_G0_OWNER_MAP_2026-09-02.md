# AXM G0 First-Wave Aggregate Owner Map

> Status: STRUCTURAL AUDIT, not a cutover claim. Call-site results below are
> static repository evidence with definitions, tests and documents excluded.
> They must be rechecked against a clean current tree before any writer moves.

## Findings

`app/`, `shared/`, `knowledge_base/` and `inspiration_research/` contain 58
files with direct `sqlite3.connect` calls. Therefore the repository does not
yet have a globally enforced database write boundary.

The count is now reproducible by the source-only
[`audit_first_wave_owners.py`](../../scripts/ci/audit_first_wave_owners.py)
contract. Its 2026-09-03 local run returned 58 paths, including
`app/workspace/service.py` and `app/learning/event_store.py`. It opens no
database and proves neither runtime reachability nor a writer cutover.

Candidate API consumers are separately reproducible by the source-only
[`audit_first_wave_consumers.py`](../../scripts/ci/audit_first_wave_consumers.py)
contract. Its 2026-09-03 local run finds only
`app/integrations/deeptutor_bridge.py` calling `append_event()` outside the
defining module; it finds no non-definition consumers for `SourceStoreV2`,
`store_bundle()`, `review_bundle()` or `record_machine_receipt()`. This is a
static absence/presence result, not a runtime trace or an ownership change.

| Aggregate / concern | Current product-path writer or projection | Structural evidence | Migration interpretation |
| --- | --- | --- | --- |
| Raw original bytes | `app.ingestion.raw_asset.RawAssetStore`, called from `app.workspace.service`; additional callers include import and web ingestion | Content-addressed store; batch routing now delegates its file write to `service.ingest_local_file()` | First-wave target. File intake has a service command boundary, but the repository does not yet enforce one globally. |
| Intake, conversion and library projection | `app.workspace.service` orchestrates `RawAssetStore`, `ConversionRun` and the caller-owned SQLite transaction | `intake_upload()` owns the interactive transaction; `ingest_local_file()` owns batch raw/conversion/anchor retention | Product-path owner for the current vertical slice; preserve it during read shadow. |
| Conversion-derived anchor | `app.evidence.anchor` (`evidence_anchors`) persists through `workspace.service` for upload and batch file intake; other router evidence actions remain separately audited | Batch router now delegates to `service.ingest_local_file()`; legacy schema can still be created by its own module | File intake P0 conflict is reduced, not eliminated. Do not migrate this table as though `anchors_v2` already owns it. |
| Source / Anchor / Provenance V2 | `app.evidence.source_store_v2.SourceStoreV2`; migration 17 owns `source_objects_v2`, `anchors_v2`, `provenance_activities_v2` | No non-definition production call site found for `SourceStoreV2` | A contract/storage candidate, not current product writer. G2 must begin read-only and differential. |
| Evidence Bundle / review | `app.evidence.ledger` owns `evidence_bundles_v1` and reviews | No non-definition production call site found for `store_bundle()` or `review_bundle()` | Candidate ledger; must not be promoted to authoritative evidence owner without a product-path adoption receipt. |
| Human learning event | `app.learning.event_store.append_event()` stores `learning_events_v2`; `app.integrations.deeptutor_bridge` is the detected non-definition caller | Append-only schema exists; one integration call site detected | Candidate event writer, but not yet a universal learning command boundary. |
| Machine competence receipt | `app.learning.event_store.record_machine_receipt()` and `machine_competence_receipts_v2` | No non-definition production call site found | Contract/storage candidate, not a demonstrated product writer. |
| Machine knowledge candidate | `app.knowledge.machine_knowledge` targets legacy V1 tables | No non-definition production call site found for candidate creation | Keep as a separate legacy compatibility surface until a consumer and cutover plan are evidenced. |
| Index / vector projection | `app.evidence.anchor.index_revisions`, FTS/vector modules | Direct SQLite writers are distributed | Rebuildable projection only; never a truth owner or migration shortcut. |
| Rust/Tauri desktop shell | `src-tauri/` and `desktop/src-tauri/` manage backend process launch and recovery-file handling | No `rusqlite`/`sqlx` dependency or direct current-domain SQLite writer found in the Rust audit | Not a Source/Anchor/Evidence/Learning writer. G1 may add read-only contract/differential code only; recovery I/O must remain separate from domain ownership. |

## Mandatory implications

1. The initial Rust work may read exported snapshots and emit a differential
   report, but it may not write `source_objects_v2`, `anchors_v2`, legacy
   `evidence_anchors`, learning events, machine receipts or raw originals.
2. Before any Source/Anchor cutover, complete consolidation of the current
   product path behind explicit Python commands, then compare those commands
   with a Rust read shadow. `ingest_local_file()` now owns the batch file write
   route, but interactive upload and other evidence actions still require the
   same inventory discipline. Replacing only dormant V2 modules would not
   migrate the user-facing pipeline.
3. Evidence, human learning and machine competence each need a consumer map
   and command/rejection receipt before their existing V1/V2 tables can be
   selected as an aggregate owner.
4. The 58 direct connection sites require a staged ownership inventory; this
   document deliberately maps only the first migration wave and does not
   authorize broad refactoring.

## Evidence commands

```text
python scripts/ci/audit_first_wave_owners.py --project-root .
python scripts/ci/audit_first_wave_consumers.py --project-root .
rg -l "sqlite3\.connect" app shared knowledge_base inspiration_research
rg -n -F --glob '!tests/**' --glob '!docs/**' SourceStoreV2 app shared knowledge_base inspiration_research
rg -n -F --glob '!tests/**' --glob '!docs/**' store_bundle( app shared knowledge_base inspiration_research
rg -n -F --glob '!tests/**' --glob '!docs/**' append_event( app shared knowledge_base inspiration_research
```

The commands describe a static audit only. Runtime traces and a clean-tree
exact-SHA qualification remain required before an ownership change.
