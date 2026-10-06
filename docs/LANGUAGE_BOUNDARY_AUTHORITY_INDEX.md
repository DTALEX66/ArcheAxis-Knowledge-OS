# Language Boundary Authority Index

Machine-local tool/model/material roots are resolved from the
[user-confirmed shared resource path index](SHARED_RESOURCE_PATH_INDEX.md),
never guessed from old taskpacks or PATH.

Current decisions: [project contract](../PROJECT_CONTRACT.yaml) and
[supersession ledger](../DECISION_SUPERSESSION_LEDGER.yaml), including SUP-020
and SUP-022 (the formal Tauri 2 + React/TypeScript/Vite host replaces SUP-021's
Avalonia shell priority; Rust Core and isolated Python boundaries are retained).
Execution: [R6 live ledger](current/R6-EXECUTION.md),
[R6 task package](authority/taskpack-0919-r6/EXECUTOR-START.md), with the
[M0 priority overlay](current/M0-DIRECTION-OVERRIDE-20260920.md).
R5 and earlier packs are historical evidence only.
The 0906/0908/0910 ledgers retain their original historical evidence.
Historical baseline: [2026-09-03 normalization record](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md).
Its old G0 cutover instructions are superseded; its recorded evidence is retained.

| Responsibility | Current implementation target | Boundary |
| --- | --- | --- |
| Formal Windows desktop | Rust/Tauri 2 in `src-tauri/`, React/TypeScript/Vite in `frontend/` | UI and Core lifecycle through finite authenticated host commands; no direct SQL or duplicated business rules; no arbitrary paths/Shell |
| Preserved Avalonia reference | C#/Avalonia in `apps/ArcheAxis.Desktop/` | Behavior and recovery donor; preservation does not create a second default shell |
| vNext domain, jobs, storage and API | Rust in `crates/` | Separate vNext database; one authoritative writer |
| Parsing, OCR, ASR, model computation | Python in `services/python-workers/` | Isolated capabilities; no main database handle or human approval |
| Protocol | `packages/contracts/` | Generated TypeScript DTOs and actual Rust/Python output must pass the same contract; preserved C# consumers retain their own validation |
| Existing Green v0.6.14 | Legacy Python, React/Tauri | Recovery and behavior reference; existing data is not migrated by declaration |

The old G0 shadow-writer cutover route is superseded by SUP-003/006.
Rust may own a separate vNext database immediately. It may not write to the
legacy database. Migration requires a consistent read-only export, validated
staging import and recoverable activation. No dual write or live synchronization.

A language decision, build, fixture or inventory is not proof of completed
capability absorption. Current migration acceptance is defined by R6 A13 and
M0 P5: nonempty legacy-copy export, staged import, semantic difference/loss
accounting, identity-preserving restart/readback, and the separate P6 owner gate
for Green replacement/rollback. Historical T13 evidence is not a current gate.
No directory move substitutes for migration. Legacy schemas and aliases remain
compatible until their own tested migration; do not rename user databases.

Development state uses `scripts/runtime/dev.py` and `.project-local/`.
Product workspace selection is separate. Legacy `ARCHEAXIS_DATA_DIR` and
compatibility `COGNITIVE_DATA_DIR` are not development-cache settings.

See [runtime delivery](RUNTIME_DELIVERY_AUTHORITY_INDEX.md),
[directory ownership](DIRECTORY_AUTHORITY_INDEX.md) and
[naming rules](NAMING_ENCODING_CONVENTIONS.md).
