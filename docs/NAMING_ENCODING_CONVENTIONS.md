# Naming and Encoding Conventions

`config/naming-registry.yaml` is the only machine-readable authority for service identity. Code,
reports, API contracts, CI checks, and user interfaces must not create independent service-name
mappings.

## Identity model

A service has three separate concepts:

1. `service_id`: stable ASCII machine identity (`core`, `knowledge-base`,
   `inspiration-research`).
2. `python_package`: import identity (`app`, `knowledge_base`,
   `inspiration_research`).
3. `display`: localized user-facing labels (`en-US`, `zh-CN`).

Display labels must never be persisted as service IDs. New API and database fields must carry the
canonical `service_id`; UIs translate it at the presentation boundary. Existing spellings such as
`Inspiration-Research`, `Inspiration_Research`, and `knowledge_base` are explicit deprecated aliases,
not additional canonical names.

Use `shared.naming.load_naming_registry()` and `NamingRegistry.resolve_service()` at compatibility
boundaries. Unknown names fail closed. An alias resolves to the canonical identity with
`deprecated_alias=True`, so callers can emit telemetry or a deprecation warning before the alias is
removed in a versioned migration.

The physical `Inspiration-Research/` directory remains a compatibility path until its import and
container consumers have migrated. Do not infer a service ID from a filesystem spelling.

## Identifier rules

| Surface | Rule | Example |
| --- | --- | --- |
| Service ID and API path segment | ASCII `kebab-case` | `knowledge-base` |
| Python package/module/field | ASCII `lower_snake_case` | `knowledge_base` |
| Python class | `PascalCase` | `KnowledgeBaseService` |
| Environment variable | `UPPER_SNAKE_CASE` | `ARCHEAXIS_DATA_DIR` (`COGNITIVE_DATA_DIR` is legacy fallback only) |
| Database table/column | ASCII `lower_snake_case` | `research_projects` |
| User-facing label | locale catalog or registry display value | `知识库` |

Chinese text is welcome in documentation and UI content. It must not be used as a machine identity,
configuration key, route identifier, database enum, or cross-service contract key.

## Text and path contract

All tracked text must be:

- valid UTF-8 without BOM;
- Unicode NFC;
- LF-terminated, including the final line;
- free of trailing spaces/tabs and prohibited zero-width characters.

Tracked paths must be Unicode NFC, avoid Windows reserved/invalid names, and have no
case-insensitive collision. `.gitattributes` is authoritative for Git blob line endings;
`.editorconfig` configures editors. Windows command files are the only CRLF exception. Declared
binary formats are not decoded or rewritten.

## Enforcement

Run the same scanner against the source being validated:

```bash
# Local working files
env -u PYTHONPATH python scripts/check_repository_conventions.py --source worktree

# Staged snapshot (pre-commit)
env -u PYTHONPATH python scripts/check_repository_conventions.py --source index

# Committed snapshot (CI)
env -u PYTHONPATH python scripts/check_repository_conventions.py --source head
```

The local pre-commit hook scans the index, while GitHub Actions scans HEAD. This separation prevents
Windows checkout bytes, unstaged edits, or later report generation from being mistaken for the
committed baseline.

## Change policy

1. Add or change canonical identities only in `config/naming-registry.yaml`.
2. Add a deprecated alias when an old external spelling must remain readable.
3. Normalize at the input boundary and propagate only the canonical `service_id` internally.
4. Migrate persisted values and clients before removing an alias.
5. Never silently reinterpret an unknown service name.
6. Any registry/API route service-set mismatch, encoding violation, or cross-platform path collision
   blocks CI.
