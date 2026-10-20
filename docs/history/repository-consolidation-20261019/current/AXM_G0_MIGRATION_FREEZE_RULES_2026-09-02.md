# AXM G0 Migration Freeze Rules

> **Frozen historical rule set (2026-09-25).** This G0 shadow-cutover route is
> superseded by R6/M0 and the current [language-boundary authority](../LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md).
> Do not apply the old React/Tauri target or the prohibitions on an independent
> Rust vNext database/writer to current work. Its historical safety evidence
> remains useful for legacy-database migration, no-dual-write, Green-data
> protection, and exact-path cleanup boundaries; it does not replace current
> authority or authorize migration/deletion.

## Scope

The migration starts from the source baseline recorded in the project-local
`migration-baseline` receipt. The target architecture is Rust as the eventual
authoritative core, TypeScript/React as the product surface, and Python as the
replaceable AI and parsing sidecar. Until a named aggregate crosses a verified
cutover gate, the current implementation remains its sole writer.

## Freeze rules

1. Do not add a domain table, public route, or independent database merely to
   make a Rust rewrite easier. Extend an existing owner only when its current
   evidence and migration path are recorded.
2. A `Source`, `Anchor`, `Evidence`, `Claim`, `Human Learning Event`, or
   `Machine Competence` aggregate has exactly one authoritative writer at a
   time. Python and Rust may read the same exported snapshot and compare their
   outputs, but may not dual-write the aggregate.
3. Sidecars may receive only explicit, read-only job inputs and may return
   candidate/result artifacts. They may not decide `verified`, human mastery,
   machine level, migration ownership, or approval.
4. Every prospective writer cutover requires a verified backup, schema
   manifest, logical fingerprint, rollback instruction, command/revision
   receipt, and a rejection path before the writer changes.
5. Indexes, vectors, statistics, UI projections, and sidecar artifacts are
   rebuildable projections. They cannot be used as an alternate source of
   truth or as a reason to skip a rollback.

## Narrow exception path

An urgent production or Green repair may cross this freeze only when it is
bounded to the defect, preserves the existing authoritative writer, and stores
a project-local exception receipt under
`.hermes/task-artifacts/migration-exceptions/`. The receipt must identify the
affected aggregate, why the existing boundary could not be used, the rollback,
and the targeted verification. An exception does not approve a later broad
migration.

## Entry gates for G1

- The exact source SHA, tree and dependency-lock hashes are present in the G0
  baseline receipt.
- Current-state documentation distinguishes selected CI success from full
  qualification and does not promote historical release/runtime evidence.
- A public or project-owned golden corpus plan identifies every file's license,
  hash, expected conversion/anchor result, and privacy classification.
- An owner map names the sole current writer for each first-wave aggregate.

## Exit condition

G1 may create contracts and read-only Rust skeletons only after the entry gates
are evidenced. Production writes remain in their existing owner until the
later read-shadow, differential and rollback gates pass.
