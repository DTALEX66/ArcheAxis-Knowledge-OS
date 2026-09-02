# Directory Authority Index

> Canonical directory classification for maintenance and future normalization.
> It names what a path is; it does not authorize a move, cleanup or deletion.

## Authoritative topology

| Path / surface | Class | Canonical role | Normalization rule |
| --- | --- | --- | --- |
| `app/`, `shared/`, `knowledge_base/`, `inspiration_research/` | `SOURCE` | Current Python product/domain and adapter implementation | Inventory consumers before changing a module boundary. |
| `frontend/` | `SOURCE` | Canonical React product UI | Build feeds the root primary Tauri host. |
| `src-tauri/` | `SOURCE` | Canonical primary Windows desktop host | Product-window repairs follow the runtime delivery chain. |
| `desktop/`, `desktop/bootstrap/` | `COMPATIBILITY_SHIM` | Separate recovery shell/fallback | Preserve until its production-use matrix and G1 gate close. |
| `docs/current/`, `docs/truth/`, `docs/taskpacks/`, `docs/history/` | `CURRENT_RECORD`, `TRUTH_RECORD`, `PLAN`, `HISTORY` | Evidence, current records, plans and historical snapshots | Classify and link before archival; history is not deletion evidence. |
| `.hermes/` | `GENERATED_REBUILDABLE` | Ignored test/runtime evidence | Cleanup only exact verified targets; never a broad deletion shortcut. |
| `.playwright-cli/` | `TRANSIENT_AUTOMATION` | Ignored browser-session residue | Remove only after exact content/path verification; it must never be staged. |
| Green `data/` | `PRESERVE_USER_DATA` | Out-of-repository runtime data | Never inspect, copy, clear, rename or delete for a repository repair. |
| Shared tool/model libraries | `EXTERNAL_BOUNDARY` | Reusable machine-local dependencies | May be consumed by declared path; never absorbed or reorganized by this repository. |

## Required records before a move

Every proposed relocation or archival action must first have one row compliant
with the [AX-DIR-010 inventory schema](current/AX_DIR_010_INVENTORY_SCHEMA.md):
source and target path, owner, data class, hashes, consumer scan, rollback,
verification and an exact deletion-authorization state.

The [directory-migration adoption map](current/AX_DIRECTORY_MIGRATION_TASK_ADOPTION_2026-09-02.md)
sets the current preconditions. A dirty tree, unresolved consumer, missing
rollback receipt or `NOT_REQUESTED` deletion state stops the operation.

## Relationship to other authority records

- [Documentation authority](DOCUMENTATION_AUTHORITY_INDEX.md) classifies
  document truth/current/history status.
- [Runtime and delivery authority](RUNTIME_DELIVERY_AUTHORITY_INDEX.md)
  governs the Windows executable chain.
- [Language boundary authority](LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md)
  governs implementation ownership; a directory name cannot change it.
- [Repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
  records the active cleanup and convergence queue; it does not authorize a
  move or deletion by itself.
