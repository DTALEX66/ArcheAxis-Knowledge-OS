# Language Boundary Authority Index

Machine-local tool/model/material roots are resolved from the
[user-confirmed shared resource path index](SHARED_RESOURCE_PATH_INDEX.md),
never guessed from old taskpacks or PATH.

Current decisions: [project contract](../PROJECT_CONTRACT.yaml) and
[supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml), SUP-001–010.
Execution: [2026-09-06 ledger](authority/taskpack-0906/EXECUTION.md).
Historical baseline: [2026-09-03 normalization record](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md).
Its old G0 cutover instructions are superseded; its recorded evidence is retained.

| Responsibility | Current implementation target | Boundary |
| --- | --- | --- |
| Formal Windows desktop | C#/Avalonia in `apps/ArcheAxis.Desktop/` | UI and Supervisor; no direct SQL or duplicated business rules |
| vNext domain, jobs, storage and API | Rust in `crates/` | Separate vNext database; one authoritative writer |
| Parsing, OCR, ASR, model computation | Python in `services/python-workers/` | Isolated capabilities; no main database handle or human approval |
| Protocol | `packages/contracts/` | Actual C#/Rust/Python output must pass the same contract |
| Existing Green v0.6.14 | Legacy Python, React/Tauri | Recovery and behavior reference; existing data is not migrated by declaration |

The old G0 shadow-writer cutover route is superseded by SUP-003/006.
Rust may own a separate vNext database immediately. It may not write to the
legacy database. Migration requires a consistent read-only export, validated
staging import and recoverable activation. No dual write or live synchronization.

A language decision, build, fixture or inventory is not proof of completed
capability absorption. T13 requires nonempty migration and behavior evidence.
No directory move substitutes for migration. Legacy schemas and aliases remain
compatible until their own tested migration; do not rename user databases.

Development state uses `scripts/runtime/dev.py` and `.project-local/`.
Product workspace selection is separate. Legacy `ARCHEAXIS_DATA_DIR` and
compatibility `COGNITIVE_DATA_DIR` are not development-cache settings.

See [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md),
[directory ownership](DIRECTORY_AUTHORITY_INDEX.md) and
[naming rules](NAMING_ENCODING_CONVENTIONS.md).
