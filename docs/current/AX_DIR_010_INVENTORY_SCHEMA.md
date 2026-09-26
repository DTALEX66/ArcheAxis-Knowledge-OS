# AX-DIR-010 Directory Inventory Schema

> Status: **SCHEMA ONLY / NO MOVE OR DELETE AUTHORISED**. Populate this only
> from a frozen, reviewed tree. The schema makes a later move reviewable; it
> is not a command to consolidate directories now.
>
> **Authority clarification (2026-09-25):** The dated mandatory classifications
> below are historical and superseded where they conflict with
> [Directory Authority](../DIRECTORY_AUTHORITY_INDEX.md) and R6/M0. In
> particular, `apps/ArcheAxis.Desktop/` is the formal desktop; `frontend/` and
> `src-tauri/` are legacy compatibility/recovery surfaces. This schema remains
> usable only for a specifically authorized, exact-path inventory; it does not
> define the current product topology or authorize a move/delete.

## One row per source path

| Field | Required value | Validation rule |
| --- | --- | --- |
| `source_path` | Repository-relative, case-preserving path | Must exist in the frozen snapshot. |
| `target_path` | Proposed repository-relative destination or `RETAIN` | No target may escape the repository. |
| `owner` | Current code/config/document owner | `UNRESOLVED` blocks movement. |
| `data_class` | `SOURCE`, `LEGACY_SOURCE`, `GENERATED_REBUILDABLE`, `IGNORED_DEVELOPMENT`, `LEGACY_MIXED_PRESERVE`, `PRESERVE_USER_DATA`, `COMPATIBILITY_SHIM`, `HISTORICAL_RECORD`, or `EXTERNAL_BOUNDARY` | `PRESERVE_USER_DATA`, `LEGACY_MIXED_PRESERVE` and `EXTERNAL_BOUNDARY` are never deletion candidates. |
| `sha256` | SHA-256 of file, or deterministic manifest hash for a directory | Must be read before and after a proposed copy. |
| `consumers` | Exact source/config/CI/document references or `NONE_FOUND` plus search command | Unverified consumers block movement. |
| `rollback` | Exact previous path plus restore/readback action | Must be possible without touching user data. |
| `verification` | Targeted test/build/readback command | Must run from the owning component. |
| `deletion_authorization` | `NOT_REQUESTED`, `APPROVED_FOR_EXACT_PATH`, or approval receipt | Absence is a hard no-delete gate. |

## Historical classifications reconciled to current directory authority

| Path / surface | Required classification | Reason |
| --- | --- | --- |
| `frontend/` and `src-tauri/` | `LEGACY_SOURCE` | Historical classification only; current role is preserved React UI / Green recovery host, not the formal vNext shell. |
| `desktop/` and `desktop/bootstrap/` | `COMPATIBILITY_SHIM` | Recovery shell is distinct from the formal host; reassess only through a production-use/retirement record. |
| `ArcheAxis.Knowledge.Green-x64/data` | `PRESERVE_USER_DATA` | Out of repository scope; never inspect, copy, clear or delete for migration. |
| `.hermes/` runtime/evidence | `LEGACY_MIXED_PRESERVE` | Historical mixed material; no new development writes and no broad cleanup. |
| `.project-local/` development outputs | `IGNORED_DEVELOPMENT` | Current development output root through `scripts/runtime/dev.py`; retained evidence is not automatically disposable. |
| Root `HANDOFF_*` and `SUMMARY_*` | `HISTORICAL_RECORD` | Require hash/reference-compatible archive migration. |
| Shared external tool/model libraries | `EXTERNAL_BOUNDARY` | May be consumed through declared paths; not moved into this repository. |

## Entry/exit conditions

Entry requires a clean frozen writer snapshot, inventory hash, consumer scan
and rollback path. Exit requires target hashes, owning tests, fresh-clone
readback, Windows product-path evidence and an explicit authorization for each
exact deletion target. Any mismatch restores the recorded source and leaves
the deletion state `NOT_REQUESTED`.
