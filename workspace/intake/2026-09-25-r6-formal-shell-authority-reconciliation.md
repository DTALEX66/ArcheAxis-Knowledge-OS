# R6 formal-shell authority reconciliation (2026-09-25)

## Decision

The R6 formal vNext product shell is C#/Avalonia at
`apps/ArcheAxis.Desktop/`, connected through the loopback HTTP contract to the
Rust Core and WriterActor. Python remains limited to isolated capability
workers. Legacy React/Tauri and Web surfaces remain recovery, migration,
behavior and capability donors; they are not the default product shell.

Reuse of existing TypeScript/JavaScript assets remains possible only for
bounded R6-registered capability integrations behind the formal shell. This
does not create a second default shell or prohibit TypeScript/JavaScript
generally. Historical assets and evidence remain preserved. The M0 release
freeze and A16 Owner Gate are unchanged.

## Authority basis

- Immutable `docs/authority/taskpack-0919-r6/TASKPACK.md`, especially sections
  5 and 19.
- `PROJECT_CONTRACT.yaml` `language_authority`.
- `config/product/UI_CONTRACT_V2.json` `productShell`.
- `AGENTS.md` section 6 and `docs/current/M0-DIRECTION-OVERRIDE-20260920.md`.

`SUP-021` supersedes only the first-release Web-priority and
"Avalonia does not block first release" clauses from `SUP-013`. It preserves
the bounded TypeScript/JavaScript reuse intent and leaves earlier records
available as historical evidence.

## Scope and evidence boundary

This reconciles authority wording only. It does not claim UI completion, alter
R6 task status, qualify a Candidate, migrate data, change the installed Green
runtime, or reopen release. UI/runtime acceptance remains governed by the
current R6 state and execution receipts.
