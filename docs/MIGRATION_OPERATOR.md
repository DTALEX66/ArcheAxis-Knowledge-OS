# Unified Migration Operator

The production migration boundary is `shared.migration_runner.MigrationOperator`. It reuses the TaskPack SQLite ledger, verified backup manifest, idempotency, collision checks, and offline rollback implementation in `shared/migration.py`; it does not execute migration SQL from runtime directories.

## Registered owners

The deterministic built-in registry owns these targets:

| Owner | Version | Target | Kind |
| --- | ---: | --- | --- |
| `core.sqlite` | 1 | `core_schema_v1` | backed-up baseline SQLite schema owner |
| `fts.cards` | 1 | `kb_cards_fts` | verified FTS shadow candidate |
| `fts.documents` | 1 | `kb_documents_fts` | verified FTS shadow candidate |
| `knowledge-governance.sqlite` | 1 | `knowledge_candidate_promotions_v1` | exact-owned Knowledge governance SQLite schema |
| `research.sqlite` | 1 | `research_packages_v1` | operator-only Phase 4 Research SQLite schema |
| `taskpack.sqlite` | 3 | `kb_taskpacks` | backed-up SQLite schema migration |
| `vector.cards` | 1 | `vec_kb_cards` | verified vector shadow candidate |
| `vector.documents` | 1 | `vec_kb_documents` | verified vector shadow candidate |
| `workspace.sqlite` | 1 | `workspace_jobs_v1` | Workspace Job/Outbox/Receipt SQLite schema |

Duplicate owner names, identity tuples, or target ownership fail closed. Shadow activation always verifies candidate identity and content before switching. The operator records applied, failed, and rolled-back provenance in the target SQLite database. A failed rollback remains retryable and blocks a new apply until resolved.

FTS candidate code is side-effect-free and accepts only an explicit SQLite target; importing the operator cannot initialize configured storage. Vector verification binds IDs to embedding-byte fingerprints and the current canonical source snapshot. Vector/FTS active switching, rollback-handle creation, and applied provenance commit in one SQLite transaction, so termination or provenance failure cannot publish an unattributed candidate. A per-owner SQLite lease serializes apply/rollback across operator processes, so concurrent switches cannot replace the original rollback lineage.

For Core baseline, TaskPack, Research, Knowledge Governance, and Workspace SQLite changes, schema DDL or ledger rows and the operator record are inserted on the same migration connection before commit. If provenance insertion fails, the schema transaction rolls back and no applied state without a backup handle can be published. The `core.sqlite` owner applies both storage and memory baseline DDL, verifies the canonical table/constraint/index contract, and records a verified pre-apply backup before either later SQLite owner runs. Research exact-schema validation rejects missing, drifted, or extra owned indexes/triggers. Each SQLite backup manifest is bound to the independently stored applied `run_id`, so editing provenance path/hash cannot redirect rollback to an older same-owner backup.

An initialized fresh TaskPack table with the current schema still receives a verified backup before ledger-only migration records are applied, so rollback can remove those records without changing current rows. A completely empty SQLite file has no applied provenance: `core.sqlite` is pending until applied. The one-shot migration entry point creates only that empty file, then applies the five registered SQLite owners in deterministic registry order; runtime storage initialization is not a prerequisite and cannot create schema outside the operator. The four Vector/FTS owners remain pending until their explicit candidate build, verification, and activation flows run; the one-shot SQLite migration command does not claim to apply them.

## Non-interactive CLI

Every command requires an explicit database and backup directory:

```text
cognitive-os migrate status --db <sqlite-path> --backup-dir <directory>
cognitive-os migrate apply --owner <owner> --db <sqlite-path> --backup-dir <directory>
cognitive-os migrate rollback --owner <owner> --db <sqlite-path> --backup-dir <directory>
```

Output is JSON. `status` is read-only and reports `pending`, `applied`, `failed`, or `rolled_back` with provenance. `apply` and `rollback` hold the same explicit target runtime lease as Core for the complete operator action and fail nonzero on collisions, candidate drift, missing rollback provenance, busy/offline violations, or replacement errors. The command does not persist `--db` into process-global environment state.

## Operational safety

- Stop runtime writers before SQLite rollback. WAL must checkpoint cleanly and leave no active WAL/SHM sidecars.
- Use the production storage SSOT to obtain the intended database path; do not guess a filename.
- Do not edit operator or schema ledgers manually.
- Owner leases live in a dedicated hidden SQLite sidecar adjacent to the explicit target database (`.<database-name>.<path-digest>.migration_operator_locks.lockdb`), not in the target database replaced by offline rollback. The path digest is the first 16 hexadecimal characters of SHA-256 over the case-folded resolved database path. The explicit backup directory stores verified backups and manifests, not lease state. Lease release is token-scoped. Treat a lease left by an interrupted process as a fail-closed recovery condition; never delete it while a writer may still be active.
- TaskPack rollback compares a logical post-apply schema/data fingerprint before whole-file restoration. Runtime data or later schema/index drift blocks rollback. The replacement copy receives the complete current operator provenance before atomic replace, so later failed or rolled-back owner evidence is retained.
- Vector rollback restores the old active rows and drops candidate/backup tables in one SQLite transaction; cleanup failure rolls the entire operation back and leaves the candidate active for a safe retry.
- Preserve each verified backup and its manifest until rollback is no longer required.
- Phase 3 cross-owner integration, Phase 4 `research.sqlite`, Phase 5 `knowledge-governance.sqlite`, and Workspace Job/Outbox ownership are implemented. Dispatcher, Worker, SSE, and user-level Job Center remain later product work; they are not implied by schema ownership.
