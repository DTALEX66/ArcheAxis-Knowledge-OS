# Directory Authority Index

> Canonical directory classification for maintenance and future normalization.
> It names what a path is; it does not authorize a move, cleanup or deletion.

本机具体资源根以 [共享资源路径索引](SHARED_RESOURCE_PATH_INDEX.md) 为准：共用模型、外置工具、绿色软件、绿色版真实资料库、项目测试资料库分属不同职责。不得把真实资料库当测试目录或把共享库当本项目清理对象。

## Authoritative topology

| Path / surface | Class | Canonical role | Normalization rule |
| --- | --- | --- | --- |
| `app/`, `shared/`, `knowledge_base/`, `inspiration_research/` | `SOURCE` | Current Python product/domain and adapter implementation | Inventory consumers before changing a module boundary. |
| `apps/ArcheAxis.Desktop/` | `SOURCE` | Formal Avalonia desktop | UI and Supervisor; no direct main database access. |
| `crates/`, `services/python-workers/`, `packages/contracts/` | `SOURCE` | Rust Core, isolated capabilities, shared contracts | One vNext writer; actual protocol output must be validated. |
| `frontend/` | `LEGACY_SOURCE` | Preserved React UI | Behavior/design reference and bounded Green maintenance. |
| `src-tauri/` | `LEGACY_SOURCE` | Preserved Green host | Existing installation and recovery, not the vNext default. |
| `desktop/`, `desktop/bootstrap/` | `COMPATIBILITY_SHIM` | Separate recovery shell/fallback | Preserve until its production-use matrix and G1 gate close. |
| `docs/current/`, `docs/truth/`, `docs/taskpacks/`, `docs/history/` | `CURRENT_RECORD`, `TRUTH_RECORD`, `PLAN`, `HISTORY` | Evidence, current records, plans and historical snapshots | Classify and link before archival; history is not deletion evidence. |
| `.hermes/` | `LEGACY_MIXED_PRESERVE` | Historical mixed assets; regenerability unverified | No new development writes; no blanket deletion. |
| `.project-local/` | `IGNORED_DEVELOPMENT` | Per-worktree/run state, caches and builds | Use `scripts/runtime/dev.py`; retained evidence is not disposable cache. |
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
