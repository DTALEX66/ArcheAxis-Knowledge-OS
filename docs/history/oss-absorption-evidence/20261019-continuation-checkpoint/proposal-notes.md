# Review title Core proposal

Status: NOT_EXECUTED. This is an unapplied proposal; no product source, contract,
existing test, generated DTO, database, service, or model was changed/run.
Root remains sole product writer. Apply only after the bound native run finishes.

Scope: 4 files, domain read-only display title helper, API projection, optional
LearningItemsDto.display_title (1..80 Unicode scalars), two API regression cases.
No DB schema migration and no frontend changes. Course title is the stored
canonical general_courses.title projection; artifact membership must match both IDs.
Fallback is the fixed assessment.content first nonempty line, then 学习项目.
All item_key, queue ordering, count, and deadlines are preserved.

Evidence: proposed tests use only tempfile synthetic stored rows. They exercise real
HTTP route projection and reopen, not course worker generation or native UI.
GET no-write check uses an independent connection PRAGMA data_version, plus a
strict SQLite read-only connection for the new helper. Real DB errors propagate.

Compatibility: display_title deliberately remains optional in schema.required so
old Core responses remain accepted. Old UI permits added properties. After applying,
root must regenerate frontend/src/api/generated/core-contract.ts with:

```powershell
& .\.venv\Scripts\python.exe -B scripts/contracts/generate_core_document.py
& .\.venv\Scripts\python.exe scripts/runtime/dev.py --run-id review-title-core -- cmd /d /c scripts\ci\cargo_test.bat test -p archeaxis-api --test learning_state_api --offline --locked learning_items_
```

Both commands above are NOT_EXECUTED. Proposed test names:
- learning_items_display_title_requires_exact_course_artifact_membership
- learning_items_display_title_preserves_snapshot_unicode_fallback_and_read_only_reopen

Frontend remains a separate root write set, including native probe key selectors.
Review formatting/type checks before applying; no Rust compiler or test was run.

Base source SHA-256 (on-disk bytes at proposal generation):
- `crates/archeaxis-domain/src/learning.rs`: `abdbce086cefade4447ccf38fbee0437114589da7c5e37ada9b44f422fa753f7`
- `crates/archeaxis-api/src/lib.rs`: `e293f5ec9e26a4386482917a47f756d6badfd119cb391d3b764b76d8f7f5e945`
- `packages/contracts/v1/core-document.schema.json`: `ea9aabb03dbe92f7d472b1c09e415ea915292718f3a334985babc58bdab8c32b`
- `crates/archeaxis-api/tests/learning_state_api.rs`: `b4371562f54983dfbf19e49d51e8fba28829e35485af3976d1e7fc3debdf217c`

Proposal SHA-256: `d591607ce31fad56405da0f1007512ca4c0ffda7d89d34d16cdaf949a361ee55`
