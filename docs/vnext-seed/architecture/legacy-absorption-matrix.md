# Original-project absorption matrix

The original project is not discarded and is not copied wholesale. Its assets
enter vNext only through an explicit decision, a target boundary and a test or
migration receipt.

| Original area | Decision | What is preserved | vNext destination | Retirement gate |
|---|---|---|---|---|
| `shared/processing_manifest.py` | wrap + semantic port | deterministic job/loss receipt behavior | Python worker emits candidate result; Rust creates authoritative JobReceipt | worker protocol and differential fixtures pass |
| `shared/safe_writer.py` | limited reuse | safe temporary-file pattern | worker job scratch only | no DB/CAS/general workspace writes |
| `shared/stable_hash.py` | oracle | fixture vectors and intended normalization | RFC 8785 JCS + SHA-256 implementations in Rust/C#/Python | cross-language vectors agree |
| text/quality/evaluation pure functions | reuse or wrap | measured transformation behavior | Python evaluation capability | exact fixture, rights and dependency profile accepted |
| `app/ingestion/**`, OCR/ASR/format handlers | wrap | parser capability and loss behavior | one pack per capability under `services/python-workers/` | timeout/crash/schema/hash tests pass |
| `app/evidence/**` | port | domain rules proven by fixtures | Rust Domain/Application | no Python DB or authoritative state remains |
| `app/knowledge/**`, `app/learning/**` | port | commands, rejections and user journey | Rust aggregates/commands/events | v0.1 review/search/learning journey passes |
| `app/memory/**`, `app/workspace/**` | port | workspace/job semantics | Rust Store/Application | restart/backup/restore pass |
| `shared/storage.py`, legacy migrations/backups | oracle then retire | schema meanings and differential cases | Rust SQLite store and legacy importer | real-copy migration and rollback drill pass |
| `app/archive/ocfl.py` | oracle/port | content-addressed archive intent | Rust CAS/archive | byte round-trip and export/restore hash pass |
| `app/rag/**`, vector code | partial oracle/wrap | query fixtures; optional embedding capability | Rust FTS5 first, Python embedding later | measured retrieval gain justifies vector projection |
| `app/api/**`, FastAPI and facades | oracle then retire | externally visible behavior/error cases | Rust local HTTP service from new contract | OpenAPI and owner journey replace routes |
| old `contracts/**`, `shared-contracts/**`, `app/contracts/**` | port | only proven examples and semantics | new `packages/contracts/` source of truth | three-language contract tests pass |
| `frontend/**` | oracle | labels, tokens, accessibility intent, screenshots | `apps/desktop/` Avalonia | matching journey and accessibility checks pass |
| `OSUI/**` | oracle | visual experiments if rights are clear | design fixtures only | no mock adapter/runtime reference remains |
| `desktop/**`, `src-tauri/**` | oracle | lifecycle, packaging and recovery cases | Avalonia Supervisor + Rust service packaging | clean Windows Green and process cleanup pass |
| `knowledge_base/**` | mostly oracle/retire | lawful project-owned fixtures; selected pure rendering | fixtures or isolated capability | privacy/rights review and fixed expected output |
| `inspiration_research/**` | deferred oracle | research prompts/ideas only | v0.2 backlog | explicit owner decision; no runtime dependency |
| `tests/**`, `integration-tests/**` | split | deterministic fixtures and domain invariants | vNext contract/integration/journey/migration suites | implementation-coupled/mock-only tests replaced |
| `docs/**`, `reports/**`, `migrations/reports/**` | history/oracle | decisions and exact evidence | curated `docs/history/`; live status from CI receipts | no manual Current file claims mutable SHA |
| `.worklab/**`, `.codex.example/**`, `codex-taskpacks/**` | oracle then retire | useful generic task semantics | vendor-neutral AGENTS/task schema/adapters | no vendor state is tracked |
| `.github/**`, `scripts/**`, `packaging/**` | selective port/rewrite | checksum, SBOM and architecture-gate intent | small vNext workflows and packaging scripts | exact-SHA Windows release qualification |

## What “port” means

Porting retains observable invariants, fixtures, rejected cases and migration
meaning. It does not mechanically translate function bodies or preserve old
module boundaries. A Rust command may intentionally have no one-to-one Python
function equivalent.

## What “wrap” means

A wrapped capability receives only immutable job-local inputs and options. It
writes only job scratch, emits versioned outputs and measurements, and has no
main database path, CAS authority, accepted/verified status or durable ID
authority. Rust revalidates everything before one authoritative transaction.

## What is absorbed first

1. Behavior and fixture inventory: lock exact source SHA, rights and known loss.
2. Contract semantics: name commands, DTOs, errors and rejection paths.
3. One narrow vertical slice: TXT/Markdown/native-text PDF import and anchors.
4. Personal knowledge, candidate review, FTS and one learning event.
5. Recovery/export/restore and Windows Green.
6. Only then: legacy exporter/importer, real database copy and cutover rehearsal.
7. After two qualified candidates and 14 days of owner use: retire-ready review.

This order keeps the user-visible vNext loop independent of the old migration
while ensuring the original project's useful behavior and data are not lost.
