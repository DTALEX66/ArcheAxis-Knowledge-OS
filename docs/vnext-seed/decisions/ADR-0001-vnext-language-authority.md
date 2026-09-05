# ADR-0001: vNext language and authority

Status: proposed for Owner acceptance in PR-00.

## Decision

ArcheAxis Knowledge vNext uses Avalonia for the desktop product, Rust for the authoritative Core/BFF/store/migration/recovery and Python for replaceable capability workers. Rust is the only business writer to the new vNext SQLite database from the first day.

## Supersession

This narrows the former G0 rule that prohibited an additional Rust database. G0 continues to protect the legacy database: Rust does not take it over, Python and Rust do not dual-write, and build success is not migration evidence. The exception applies only to a separate vNext workspace and database.

## Consequences

- Current Python/React/Tauri code is a behavior and fixture source, not the new authority.
- Cross-language behavior is defined in OpenAPI and JSON Schema before implementation.
- The first milestone includes contract, process and packaging cost; it is not hidden.
- A future language change requires an Owner ADR and removes the old core. Dual cores are never accepted.

## Reopen gate

Do not reopen the decision before v0.1 and one legacy import dry-run. Reopen only if, after one bounded repair:

1. the minimum owner loop is still impossible by the tenth working day; or
2. cross-language build/package work exceeds 30 percent of two consecutive iterations; and
3. evidence shows the runtime boundary, rather than requirements, domain design or missing tests, is the cause.

If the gate is met, the only fallback considered is a complete Owner-approved switch to C# Core. Rust and C# may not remain co-authoritative.

