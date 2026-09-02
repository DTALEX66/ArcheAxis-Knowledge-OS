# AX-DIR-010 Directory Inventory Schema

> Status: **SCHEMA ONLY / NO MOVE OR DELETE AUTHORISED**. Populate this only
> from a frozen, reviewed tree. The schema makes a later move reviewable; it
> is not a command to consolidate directories now.

## One row per source path

| Field | Required value | Validation rule |
| --- | --- | --- |
| `source_path` | Repository-relative, case-preserving path | Must exist in the frozen snapshot. |
| `target_path` | Proposed repository-relative destination or `RETAIN` | No target may escape the repository. |
| `owner` | Current code/config/document owner | `UNRESOLVED` blocks movement. |
| `data_class` | `SOURCE`, `GENERATED_REBUILDABLE`, `PRESERVE_USER_DATA`, `COMPATIBILITY_SHIM`, `HISTORICAL_RECORD`, or `EXTERNAL_BOUNDARY` | `PRESERVE_USER_DATA` and `EXTERNAL_BOUNDARY` are never deletion candidates. |
| `sha256` | SHA-256 of file, or deterministic manifest hash for a directory | Must be read before and after a proposed copy. |
| `consumers` | Exact source/config/CI/document references or `NONE_FOUND` plus search command | Unverified consumers block movement. |
| `rollback` | Exact previous path plus restore/readback action | Must be possible without touching user data. |
| `verification` | Targeted test/build/readback command | Must run from the owning component. |
| `deletion_authorization` | `NOT_REQUESTED`, `APPROVED_FOR_EXACT_PATH`, or approval receipt | Absence is a hard no-delete gate. |

## Mandatory classifications for the current route

| Path / surface | Required classification | Reason |
| --- | --- | --- |
| `frontend/` and `src-tauri/` | `SOURCE` | Canonical primary Windows product chain. |
| `desktop/` and `desktop/bootstrap/` | `COMPATIBILITY_SHIM` until G1-001 and a production-use matrix close | Recovery shell is distinct from the primary host. |
| `ArcheAxis.Knowledge.Green-x64/data` | `PRESERVE_USER_DATA` | Out of repository scope; never inspect, copy, clear or delete for migration. |
| `.hermes/` runtime/evidence | `GENERATED_REBUILDABLE` only after exact target verification | Project-local runtime boundary; no broad cleanup. |
| Root `HANDOFF_*` and `SUMMARY_*` | `HISTORICAL_RECORD` | Require hash/reference-compatible archive migration. |
| Shared external tool/model libraries | `EXTERNAL_BOUNDARY` | May be consumed through declared paths; not moved into this repository. |

## Entry/exit conditions

Entry requires a clean frozen writer snapshot, inventory hash, consumer scan
and rollback path. Exit requires target hashes, owning tests, fresh-clone
readback, Windows product-path evidence and an explicit authorization for each
exact deletion target. Any mismatch restores the recorded source and leaves
the deletion state `NOT_REQUESTED`.
