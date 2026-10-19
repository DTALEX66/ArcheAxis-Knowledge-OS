# Research contract gap analysis (R6 A06 / M0 P2)

> **STATUS: PROPOSAL / OWNER REVIEW REQUIRED.**
> This is a read-only design note. It is **not** an adopted contract, not an implementation
> authorization, and not an R6/M0 state change. No source, schema, route or UI is modified by it.
>
> - task_id: `DP-A11`
> - baseline: `a5de4b13474c217e7a9dd34b8cbfa402e8297780` (tree `a4156ed65d50675822321b9d63eec932b1e76af3`)
> - evidence class: `STRUCTURAL / READ-ONLY` (no runtime executed; every claim below is a file/line read of the current tree)
> - author: DSH DP run (independent read-only analysis), branch `codex/dp-a11-20260925`

## 1. Problem statement

Research is intentionally unavailable in the product. The reason is contract-shaped, not cosmetic:

- the derived-projection contract requires an authoritative **source revision** on every item;
- the canonical transform record that a research/retrieval projection would cite **does not carry a revision**;
- and no current Rust read route exposes a revision-bound, provider-versioned, quality-annotated projection at all.

Until those are resolved by an owner decision, Research controls must stay unavailable and no UI may be enabled for them. This note enumerates the exact gap so the decision can be made against real code rather than a summary.

## 2. Current authoritative facts (read-only citations)

### 2.1 The derived projection contract requires a revision per item

`app/contracts/derived_projection_v1.py:9-16` — `ProjectionItemV1` requires `source_id: str (min_length 1)` and `source_revision: str (min_length 1)`; `score` is `0..1`; the file is `extra="forbid"`.

`app/contracts/derived_projection_v1.py:18-45` — `DerivedProjectionReceiptV1` fixes `schema = "archeaxis.derived-projection/v1"`, `projection_kind ∈ {fts, embedding, reranked, graph, hybrid, research}`, plus `algorithm`, `algorithm_version`, `canonical_source_ids` (non-empty, unique), `items`, `generated_at`, and the hard flags `rebuildable: true` / `writes_canonical: false`. Every item's `source_id` must be a member of `canonical_source_ids`.

**Consequence:** a Research projection cannot be honestly emitted unless each result item can name the revision of the canonical source it was derived from.

### 2.2 The canonical transform record has no revision field

`crates/archeaxis-store-sqlite/src/lib.rs:31-37`:

```sql
CREATE TABLE IF NOT EXISTS transforms (
    transform_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    engine TEXT NOT NULL,
    text TEXT NOT NULL,
    loss_note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

There is no revision column. Note that the transform is written by `archeaxis-application`'s job path, not by a second writer:

`crates/archeaxis-application/src/jobs.rs:114-117` inserts the transform and then `crates/archeaxis-application/src/jobs.rs:119-124` updates the job with `state`, `engine`, `loss_receipt`, `completion_digest`, `transform_id`, `completed_at`.

**Consequence:** any "revision" of a transform must be *derived*, and the derivation must be named by authority rather than invented by a caller.

### 2.3 A revision IS derivable from an existing authoritative column

`crates/archeaxis-store-sqlite/src/lib.rs:13-19` → `sources` is declared at `crates/archeaxis-store-sqlite/src/lib.rs:15`, carrying `source_id`, `sha256 TEXT NOT NULL UNIQUE`, `original_name`, `raw_path`, `imported_at`.

The Rust Core already treats that content hash as the revision for the one place where a revision is persisted:

`crates/archeaxis-domain/src/knowledge.rs:216` — `let anchor_id = crate::anchor::insert_anchor(&tx, source_id, &raw_sha256, &position)?;`

Here `raw_sha256` was read at `crates/archeaxis-domain/src/knowledge.rs:189-196` by joining `jobs → sources → transforms`. So for source-bound human Candidates the Core itself sets `anchors.source_revision` to the **source content hash**, never to a caller-supplied string.

By contrast, the direct anchor route takes the revision from the request body: `crates/archeaxis-api/src/lib.rs:768-771` (`AnchorBody { revision, position }`) → `crates/archeaxis-api/src/lib.rs:779` (`anchor::add_anchor(conn, &source_id, &body.revision, &body.position)`). No current Desktop code calls that route (`grep` for `sources/.*/anchors` in `apps/ArcheAxis.Desktop` returns no matches).

`crates/archeaxis-store-sqlite/src/lib.rs:39-45`:

```sql
CREATE TABLE IF NOT EXISTS anchors (
    anchor_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_revision TEXT NOT NULL,
    position TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 2.4 The existing read routes do not carry a revision

`crates/archeaxis-api/src/lib.rs:796-812` (`GET /api/v1/sources/:source_id/jobs/:job_id/transform`) selects `t.transform_id, s.sha256, t.text` and returns `source_id`, `job_id`, `transform_id`, `raw_sha256`, `content`. It **does** expose the source hash, but only for a single job/transform pair — it is a single-record read, not a projection over a result set.

`crates/archeaxis-api/src/lib.rs:1430-1449` (`/api/v1/search`) returns, for transforms, only `transform_id`, `source_id`, `engine`, `head` — **no revision and no anchors**. `crates/archeaxis-domain/src/search.rs:76-91` (`search_transforms`) returns `(transform_id, source_id, engine, snippet-head)`; the FTS index at `crates/archeaxis-domain/src/search.rs:65` is built from `rowid, text, transform_id, source_id, engine`.

`crates/archeaxis-api/src/lib.rs:826-841` (`/api/v1/evidence/anchors`) returns `anchor_id`, `source_id`, `raw_sha256`, `source_revision`, `position`, `created_at` — the only route that exposes `source_revision`, and it does so per anchor, not per retrieval result.

`crates/archeaxis-api/src/lib.rs:969-984` (`/api/v1/knowledge-items/:id/qualification`) returns only `knowledge_id`, `exists`, `active`.

### 2.5 Quality / provider facts exist but are not projected

`crates/archeaxis-store-sqlite/src/lib.rs:88-98` → `jobs` is declared at `crates/archeaxis-store-sqlite/src/lib.rs:88`, carrying `job_id`, `kind`, `state`, `input_ref`, `engine`, `loss_receipt`, `created_at`, `completed_at`. `crates/archeaxis-application/src/jobs.rs:100-102` validates that a loss receipt is non-empty on engine, parses, and requires `loss.engine == engine`, then serializes it into `loss_receipt`.

**Consequence:** for a transform-completion job the Core already persists the producing `engine` and a structured `loss_receipt`. Neither is currently exposed through any search/projection route.

### 2.6 There is no Research route at all

`crates/archeaxis-api/src/lib.rs:40-77` (the `pub fn router` table) contains no Research endpoint; the only "research" surfaces in the Rust tree are vocabulary values: `research_result` as a V3 `source_type` (`crates/archeaxis-store-sqlite/src/lib.rs:62`, `crates/archeaxis-api/src/lib.rs:999`, `crates/archeaxis-domain/src/knowledge.rs:26`) and `RESEARCH_VERDICT_VALUES` in `crates/archeaxis-contracts/src/generated/vocabulary.rs:10`.

`config/desktop/routes-v1.json` contains no `research` entry (grep returns nothing).

## 3. Gap enumeration (exact fields)

The table below states what a Research-capable read projection would need, what exists today, and the authoritative writer for each element. "Derivable" means the value exists in canonical storage or a canonical join and does not require a new store.

| # | Required element | Contract that demands it | Current availability | Authoritative writer |
| --- | --- | --- | --- | --- |
| G1 | `source_revision` per result item | `ProjectionItemV1.source_revision` (derived_projection_v1.py:13) | **Derivable** from `sources.sha256` via `transforms.source_id`; already used as the anchor revision at knowledge.rs:216 | Rust Core import path (`sources.sha256`), written at import; never caller-supplied |
| G2 | `source_id` per item | same | Present in `transforms.source_id` and in `/api/v1/search` transform items | Rust Core |
| G3 | `anchor_id` per item (optional) | `ProjectionItemV1.anchor_id` | Present in `anchors` and in `/api/v1/evidence/anchors`; **not** joined into search results | Rust Core (`anchor::insert_anchor`) |
| G4 | `algorithm` + `algorithm_version` | `DerivedProjectionReceiptV1` | Transform engine exists (`transforms.engine`, `jobs.engine`); there is **no version column** anywhere | Rust Core job completion |
| G5 | provider/engine identity per item | "provider/version" requirement of the Research gate | `engine` is a free-text producing-engine name; no provider registry binding, no model identity, no digest | Capability/provider registry — **still `BLOCKED_BY_AUTHORITY_DECISION` per R6 P0-H01** |
| G6 | quality / loss facts per item | M0 requires loss and quality to be explicit | Persisted as `jobs.loss_receipt` JSON; not projected by any route | Rust Core job completion |
| G7 | fallback state per item | explicit-fallback requirement (R6 A05 receipts) | Only partially recoverable from `loss_receipt` JSON; there is no projection | Rust Core job completion |
| G8 | stale / superseded state | consumers must not silently use a superseded revision | No revision history exists for transforms (append-only rows; `transforms` has no supersede relation) | would need an owner decision (§5.3) |
| G9 | empty vs error vs unsupported state | M0 "explicit unsupported" rule | No Research route exists at all | n/a — proposal |
| G10 | rebuildable / non-canonical flag | `rebuildable: true`, `writes_canonical: false` | No projection exists | n/a — proposal |

**The single hard blocker is G1 + G4/G5 combined:** the receipt contract needs a revision *and* algorithm/provider identity, the revision is derivable but unexposed, and the provider identity is an unresolved authority question rather than a code question.

## 4. Proposed contract (for owner review — not adopted)

A minimal, additive, read-only projection. Nothing here is implemented.

### 4.1 Route shape

```
GET /api/v1/sources/:source_id/transforms/projection?q=<non-empty>&limit=<n>
```

Read-only. No table, no migration, no write route, no change to `sources`, `transforms`, `anchors` or `knowledge`.

### 4.2 Proposed response projection

```
schema            = "archeaxis.derived-projection/v1"   (reuse the existing contract; do not fork a second one)
projection_kind   = "research" | "fts"
projection_id     = deterministic, derived from (kind, query, sorted source ids, revision set)
query             = the caller query (non-blank; the existing contract already rejects blank)
algorithm         = "core-transform-fts" (proposal; exact string is an owner-visible decision)
algorithm_version = a version string owned by the Core, bumped when the projection logic changes
generated_at      = Core clock
rebuildable       = true
writes_canonical  = false
canonical_source_ids = the distinct source ids in the result set
items[] = {
  source_id,                  // from transforms.source_id
  source_revision,            // derived: sources.sha256 (authoritative content hash)
  transform_id,               // the concrete immutable transform row the item came from
  engine,                     // producing engine, from jobs.engine / transforms.engine
  score,                      // measured match predicate only; must NOT be presented as semantic quality
  anchor_id,                  // optional; null when no anchor is bound
  quality: { loss_receipt_ref or explicit null, measured: false|true },
  stale: false | { reason, current_revision }
}
```

### 4.3 Revision derivation rule (proposal)

- `source_revision` = `sources.sha256` for the row joined through `transforms.source_id`.
- It is **derived, never supplied by the caller**. The direct anchor route's caller-supplied `revision` field must not be reused as the authority for a projection.
- Rationale: this mirrors the already-shipped behaviour of source-bound Candidate creation (`knowledge.rs:216`), so the product would have exactly one revision semantics rather than two.
- The transform's own identity is the immutable `(transform_id, sources.sha256)` pair. A transform row is never rewritten; a new extraction creates a new row (see `jobs.rs:104-114`, which inserts a fresh row and rebinds the job).

### 4.4 Authoritative writer

Only the Rust Core writes canonical storage (`AGENTS.md` §6; R6 A12 contract `archeaxis-core-rust-sqlite`). The projection is a read; it must not create tables, must not write revisions, and must not be produced by the Desktop, by a worker, or by a Python sidecar.

### 4.5 Stale / error / empty semantics (proposal)

| Condition | Required honest result |
| --- | --- |
| No matching transform rows | `items: []`, HTTP 200, with an explicit empty marker. Empty is not an error. |
| Unknown `source_id` | HTTP 404 with a Core message; do not synthesize an empty projection for a source that does not exist |
| Blank/whitespace `q` | HTTP 400, consistent with the existing `query must not be blank` rule in the receipt contract |
| Transform exists with no successful job completion | The item must not appear; a transform only ever exists through a successful completion (`jobs.rs:104`) |
| Revision cannot be derived (no `sources` row — FK makes this unreachable today) | Fail closed (500), never emit `source_revision: "unknown"` |
| Provider identity unavailable | `engine` may be reported as the free-text engine, but any provider/model/version claim must be `null` with an explicit `unavailable` reason, not a guessed value (this is the current state per G5) |
| Core offline / DB unavailable | Error state, no cached or reconstructed projection |

### 4.6 Migration compatibility

- No new column, no new table, no schema-version bump (`SCHEMA_VERSION = 6`, `crates/archeaxis-store-sqlite/src/lib.rs:8`).
- Existing routes and their JSON shapes stay unchanged; the projection is a strictly additional read route.
- Existing anchors keep their stored `source_revision`; the projection does not reinterpret them. For anchors created by source-bound Candidate creation the stored value already equals the source content hash, so the two semantics agree by construction.
- Any future reranker/embedding provider must attach its identity through the (still blocked) P0-H01 provider-authority decision; until then `projection_kind` should stay `fts`/`research`-over-FTS only.

## 5. Explicit non-claims

1. This note does **not** propose new revision semantics. It proposes deriving the revision from an existing authoritative column that the Core already uses for exactly this purpose.
2. It does **not** authorize enabling Research UI. The Research surface stays unavailable until an owner adopts a contract and a Rust route exists.
3. It does **not** claim a transform has an independent revision history. No such history exists today; whether one is needed is an owner question (G8).
4. It does **not** claim provider/model quality can be projected today. `config/models.yaml` remains `stub/local-stub` and P0-H01 provider lifecycle is `BLOCKED_BY_AUTHORITY_DECISION`.
5. It does **not** propose that retrieval results are knowledge. `search_transforms` is a transform-text projection; the existing Core comment at `crates/archeaxis-api/src/lib.rs:1428-1429` ("… without claiming the text is knowledge (see domain::search::search_transforms)") already states this.
6. No test was executed for this note. It is a citation-only read of the current tree; runtime behaviour of any proposed route is `NOT_EXECUTED`.

## 6. Owner decisions requested

1. **D1 — revision authority.** Confirm `source_revision := sources.sha256` (derived) as the single revision semantics for retrieval/research projections, matching source-bound Candidate anchors. *(Recommended, and matches shipped behaviour.)*
2. **D2 — projection contract reuse.** Confirm the new route emits the existing `archeaxis.derived-projection/v1` receipt rather than a second Research-specific schema.
3. **D3 — provider identity boundary.** Decide whether Research may ship FTS-only with an explicit `provider: unavailable` marker before the P0-H01 provider-authority decision, or whether Research must stay fully blocked until provider identity exists.
4. **D4 — stale semantics.** Decide whether `transforms` need any revision history at all (G8), or whether append-only rows plus the source content hash are sufficient.
5. **D5 — score honesty.** Confirm the projected `score` must be labelled as a measured match predicate and must never be surfaced as relevance/quality, consistent with the existing Vault FTS receipt comment (`app/workspace/vault.py:112-114`).

Until D1–D5 are decided, this document is `PROPOSAL / OWNER REVIEW REQUIRED` and Research remains unavailable.
