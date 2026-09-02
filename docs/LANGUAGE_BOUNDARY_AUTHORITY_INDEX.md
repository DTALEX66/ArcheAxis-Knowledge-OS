# Language Boundary Authority Index

> The canonical decision record for language ownership. It prevents a local
> compile, a sidecar, or a new crate from being mistaken for a production
> domain-writer migration.

## Current authority by responsibility

| Responsibility | Authoritative implementation today | Change rule |
| --- | --- | --- |
| Product surface | `frontend/` TypeScript/React and the primary `src-tauri/` host | Keep the API contract truthful; target frontend tests/build and root Tauri tests. |
| Windows host, launch and recovery boundary | Rust/Tauri in `src-tauri/`; separate recovery shell in `desktop/src-tauri/` | The recovery shell is not a substitute product host or domain core. |
| Product-domain persistence and current writers | Python command paths under `app/` and their SQLite stores | One aggregate has one writer. No Rust/Python dual write. |
| Parsing, OCR, ASR and model-assisted conversion | Python adapters/sidecars under `app/ingestion/` and declared optional engines | Emit candidate artifacts only; never decide verified truth, mastery, approval or rollback. |
| Static ownership evidence | `scripts/ci/audit_first_wave_owners.py` and `current/AXM_G0_OWNER_MAP_2026-09-02.md` | Source-only output is not runtime reachability or cutover evidence. |

## Canonical migration order

1. Close every row in the [G0 evidence gap register](current/AXM_G0_EVIDENCE_GAP_REGISTER_2026-09-03.md), including exact-SHA qualification, corpus journey receipts, and writer/consumer/rejection evidence.
2. Implement G1 contracts and Rust read-only differential reports only.
3. Select one aggregate, retain the current Python writer, and prove two zero-semantic-difference shadow receipts before proposing any cutover.
4. Cut over one named aggregate with backup, rollback, exact-SHA CI and a Windows product-path result. All other writers remain unchanged.

The staged route, delayed platform work and explicit non-goals are maintained
by the [language-audit adoption map](current/AXM_LANGUAGE_AUDIT_TASK_ADOPTION_2026-09-02.md).
The runtime executable chain is governed separately by the
[runtime and delivery authority index](RUNTIME_DELIVERY_AUTHORITY_INDEX.md).

## Acceleration control point

The active [repository normalization state](current/REPOSITORY_NORMALIZATION_STATE_2026-09-03.md)
orders the shortest safe path to a language transition: close G0 evidence,
then introduce a named Rust read-only differential consumer, then consider one
aggregate cutover. Directory cleanup, a compile and a local test do not bypass
the single-writer or exact-SHA requirements.

## Naming and compatibility boundary

- New runtime/test/process isolation uses `ARCHEAXIS_DATA_DIR` only.
- `COGNITIVE_DATA_DIR` is a compatibility fallback in the runtime resolver;
  it is not a canonical test or launcher setting and must be cleared in an
  isolated child process before import.
- Existing persistence names such as `cognitive_os.sqlite` are compatibility
  data formats, not authorization to rename or migrate user data. A database
  rename needs its own reversible data-migration receipt.
- Naming syntax, aliases and text encoding remain governed by
  [NAMING_ENCODING_CONVENTIONS.md](NAMING_ENCODING_CONVENTIONS.md) and
  `config/naming-registry.yaml`.

## Hard no-go rules

- No production Rust SQLite writer, schema, route or table for a first-wave
  aggregate before G0 closes.
- No directory move used as a proxy for language migration.
- No claim of a language cutover from a compile, unit test, source scan or
  Green executable replacement alone.
