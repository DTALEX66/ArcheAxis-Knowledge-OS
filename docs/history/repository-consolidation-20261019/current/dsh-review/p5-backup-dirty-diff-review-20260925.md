# DP-NF-06 · P5 backup/migration dirty-diff review

- task_id: `DP-NF-06` (P5 half)
- baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
- baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
- branch: `codex/dp-nf-06-20260925`
- scope: **read-only review of the root checkout's uncommitted P5 diff**
- evidence class: `STRUCTURAL / READ-ONLY` — **no test was run** (see §6)

## 0. What was reviewed, and what was not touched

The mainline has **678 insertions / 100 deletions across six P5 files uncommitted** in the root
checkout. This report reviews that actual working-tree diff — not an old HEAD standing in for it —
and changes nothing.

| Path | Dirty diff |
| --- | --- |
| `crates/archeaxis-domain/src/backup.rs` | +169/−… (largest hunk) |
| `crates/archeaxis-domain/tests/backup_safety.rs` | +268/−… |
| `crates/archeaxis-migration/src/lib.rs` | +92/−32 |
| `crates/archeaxis-migration/tests/legacy_nonempty_migration.rs` | +49/−… |
| `crates/archeaxis-migration/tests/migration_dry_run.rs` | +8/−… |
| `crates/archeaxis-migration/tests/stage_demo.rs` | +160/−… |

All six are ` M` (modified, unstaged). The review read the diff with `git diff -- <path>` from the
root checkout; **no** build, test, format or write was performed against those files, and no shared
Cargo target was used.

## 1. backup.rs — what the dirty diff actually changes

**Before:** `verify_counts` compared only `count(*)` for five hard-coded tables
(`sources`, `transforms`, `anchors`, `knowledge`, `learning_events`) after validating the workspace
and source objects.

**After (read from the diff):**

1. **Schema catalog equality.** New `schema_objects()` reads
   `SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name`
   and requires the two databases' catalogs to be equal — so a schema change with identical row
   counts is now caught.
2. **Table-set equality over the whole schema.** New `table_names()` enumerates every table,
   explicitly including `sqlite_sequence`, instead of five hard-coded names.
3. **Per-table content digests.** New `table_content_digest()` builds a typed SHA-256 over every row
   (`SELECT * FROM "<table>" ORDER BY 1,2,…`): a per-value type tag (Null/Integer/Real/Text/Blob),
   little-endian numerics, length-prefixed text/blob, row separators `0xA1`/`0xAF`, and a trailing row
   count. This replaces count-only equality, so "same count, different content" is now a mismatch.
4. **Stable read view.** `verify_counts` wraps both connections in `unchecked_transaction()` for the
   whole comparison and commits only afterwards, so a concurrent writer cannot commit between table
   digests and make one database look internally inconsistent.
5. **Stronger integrity check.** `validate_workspace` now collects **all** rows of
   `PRAGMA integrity_check` and requires the result to be exactly `["ok"]`, instead of taking only
   the first row. Schema-version and `PRAGMA foreign_key_check` requirements are retained.
6. `backup()`/`restore()`/`Publication::drop` are otherwise **formatting-only** changes in this diff,
   plus the bring-in of `sha2::{Digest, Sha256}` for the digest work.

**Assessment:** this is a real integrity upgrade, not churn. It directly addresses three of the
items this card was asked to verify — schema, source-object hash, and logical row content.

## 2. migration/src/lib.rs — what the dirty diff actually changes

1. **SQL-identifier hardening.** New `quote_identifier()` (`"` doubled) replaces direct
   `format!("\"{name}\"")` interpolation, and `pragma_table_info('{name}')` was replaced by a
   **parameterised** `pragma_table_info(?1)`. This closes an injection/quoting gap for hostile table
   names.
2. **Filesystem-safe export names.** New `export_filename()` emits `{name}.jsonl` only for a plain
   `[A-Za-z0-9_-]+` name and otherwise `__table_{hex(name)}.jsonl`, so a pathological table name can
   no longer drive path construction.
3. **No-overwrite export.** Export now opens files with `create_new(true)` instead of `File::create`,
   so an existing snapshot file causes an error instead of being silently truncated.
4. **Zero-row tables are no longer skipped.** The old `if t.row_count == 0 { continue; }` is gone, so
   an empty table is still declared in the manifest — closing a "missing table looks like an absent
   table" ambiguity.
5. **Manifest digest extracted** into `manifest_digest(&BTreeMap<String, TableExport>)`, now computed
   over `manifest.tables` (including zero-row tables) rather than over a locally built map. The
   manifest file is also written through an `OpenOptions` handle rather than `fs::write`.

## 3. Test coverage in the dirty diff (mapped to the required items)

| This card's required item | Covering dirty test | Verdict |
| --- | --- | --- |
| machine receipt restore | `backup_restore_preserves_machine_failure_retest_and_knowledge_binding` (`backup_safety.rs:10`) — creates accepted Knowledge, records a **failed** synthetic machine task with `knowledge_version: Some(&accepted)` and `retest_of: None`, then backs up/restores and re-checks the binding | **covered** (synthetic) |
| schema drift | `verify_counts_rejects_schema_catalog_change_even_when_counts_match` | **covered** |
| schema/catalog + workspace metadata | `verify_counts_covers_workspace_metadata_and_schema_drift` | **covered** |
| logical row content | `verify_counts_rejects_same_count_different_row_content` | **covered** |
| SQLite snapshot stability under concurrency | `verify_counts_uses_a_stable_read_snapshot_during_concurrent_source_writes` (`backup_safety.rs:299`) — uses a custom `verification_gate` collation on `a_blocker` to rendezvous with the verifying thread, then mutates `z_mutated` from another thread, with WAL enabled on both databases | **covered** (deterministic, not a sleep race) |
| source-object hash | pre-existing `verify_source_objects` path, retained; not newly extended in this diff | **retained, unchanged** |
| migration: manifest removal rejected before writes | `manifest_table_removal_is_rejected_before_any_write` | **covered** |
| migration: hostile table name | `hostile_table_name_is_exported_inside_destination_without_sql_damage` | **covered** |
| migration: no overwrite | `export_refuses_to_overwrite_existing_snapshot` | **covered** |
| migration: unlisted JSONL rejected pre-staging | `unlisted_jsonl_is_rejected_before_any_staging_write` | **covered** |

## 4. Gaps this review found (not covered by the dirty diff)

1. **Workspace identity is still absent.** Nothing in the diff assigns, persists or compares a
   workspace identity/generation across backup→restore→restart. R6 A13 records this as an open
   **Owner** decision, so it is correctly out of a code card's scope — but it remains the single
   largest P5 gap. **Recommended as a separate owner-decision item, not a test card.**
2. **Real Legacy semantic diff/loss closure is not addressed.** The migration tests use synthetic
   fixtures. `migration_dry_run.rs` changed by only +8. No evidence here for a non-empty *real*
   Legacy copy export → staging import → semantic diff → loss report. R6 A13/P5 continues to require
   an isolated non-empty legacy fixture; that exists only in synthetic form. **Blocked on authorized
   input, not on code.**
3. **`verify_counts` remains a comparison, not a restore receipt.** It returns `bool`; the caller must
   record the outcome. There is no content-hash receipt emitted per restore, so "restore verified"
   is not independently auditable from the database alone. **Suggested separate test card** (small,
   local, no owner input needed).
4. **Foreign keys: `PRAGMA foreign_key_check` presence-only.** `validate_workspace` fails if
   `foreign_key_check` returns any row (existing behaviour, retained). That is correct, but there is
   no test in this diff that constructs an FK-violating snapshot and asserts rejection. **Suggested
   separate test card.**
5. **Digest covers `sqlite_sequence`.** `table_names()` deliberately includes it, which is right for
   AUTOINCREMENT tables, but note this makes the digest sensitive to sequence state. That is a
   *feature* for exactness and a *risk* for cross-machine comparison; worth an explicit comment or an
   owner statement. Minor.

## 5. Status statement

- P5 remains **`TESTED_LOCAL_PARTIAL`** and this review **does not change it**.
- Nothing here is `TESTED_LOCAL` from *this* task: the tests were read, not executed (§6).
- Owner workspace-identity decision remains **open**; Green remained untouched and was not read.

## 6. Commands, and what was NOT run

Executed (all read-only, no build):

| Command | Result |
| --- | --- |
| `git diff --stat -- <6 P5 paths>` | `6 files changed, 678 insertions(+), 100 deletions(-)` |
| `git status --porcelain -- <6 P5 paths>` | six ` M` entries |
| `git diff -- crates/archeaxis-domain/src/backup.rs` | full hunk review |
| `git diff -U0 -- crates/archeaxis-migration/src/lib.rs` | function-level review |
| `git diff -U0 -- <4 test files>` | added test-name inventory |
| `Select-String` on `backup_safety.rs` | read two test bodies in full line-numbered context |

**NOT run, deliberately:** `cargo test`, `cargo check`, `cargo fmt`, any build — the task forbids
running anything that could share a Cargo target with the concurrently active mainline, and these
files are still uncommitted mainline work. Therefore every "covered" claim in §3 means **a test
exists that asserts this**, not **the test passes**. That distinction is the main limitation of this
report. A follow-up card may run the focused suite once the mainline commits and an isolated target
is confirmed.
