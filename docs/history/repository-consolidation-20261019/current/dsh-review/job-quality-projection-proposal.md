# Job quality / loss-receipt read projection — contract proposal

> **STATUS: PROPOSAL / OWNER REVIEW REQUIRED.**
> Read-only design note. **Not** an adopted contract and **not** an implementation authorization.
> No Rust production code, route, schema or UI is changed by this document.
>
> - task_id: continuation of `DP-F01` (contract-gap follow-up requested by the user)
> - baseline: `a5de4b13474c217e7a9dd34b8cbfa402e8297780` (tree `a4156ed65d50675822321b9d63eec932b1e76af3`)
> - branch: `codex/dp-f01-20260925`
> - evidence class: `STRUCTURAL / READ-ONLY` (no new test executed for this note; every claim is a file/line read)
> - correction notice: an earlier DP-F01 summary described this gap with a **wrong citation** (`lib.rs:291-306`) and a **wrong route name** (`/outputs/loss_report` under a nonexistent projections router). This note states the verified facts; the earlier description must not be relied on. See §6.

## 1. The gap, stated exactly

The Core persists a complete, validated loss receipt for every terminal text job, and it **is**
reachable — but only through a generic byte-output route, in a shape that makes the receipt's
contents awkward to consume and impossible to schema-validate on the wire:

| Consumer need | `GET /api/v1/jobs/:job_id/quality` | `GET /api/v1/jobs/:job_id/outputs/:kind` |
| --- | --- | --- |
| job state / engine / engine version | yes | only inside the string |
| coverage, covered, total, loss_count, region_count, pages | yes (top level) | only inside the string |
| `params.decode` (e.g. `utf-8-sig`, `gbk`) | **no** | yes, but only after parsing `content` |
| `params.media_type` | **no** | yes, after parsing |
| `params.format.*` (headings, links, CSV shape, JSON depth…) | **no** | yes, after parsing |
| `losses[]` entries (named losses) | count only (`loss_count`) | yes, after parsing |
| machine-readable receipt object | **no** | **no** — `content` is a JSON **string** |

So the honest summary is: **the receipt is durable and reachable, but there is no route that
projects it as a typed receipt, and the quality projection drops every `params` fact.**

## 2. Verified current facts

### 2.1 The quality projection intentionally projects only summary facts

`crates/archeaxis-api/src/lib.rs:1457-1512` — `job_quality` is documented "Facts only: no accuracy
figure is produced, and a recogniser's confidence is never presented as accuracy." It selects
`state, engine, loss_receipt FROM jobs` (line 1464), parses the receipt, then reads
`receipt["params"]["regions"]` and `receipt["losses"]` **only to count them** (lines 1485-1495) and
returns a fixed JSON object (lines 1496-1508): `job_id`, `state`, `engine`, `engine_version`,
`coverage`, `covered`, `total`, `loss_count`, `region_count`, `pages`, and the note
"facts only; model or recogniser confidence is not accuracy". `params` itself is never returned.

### 2.2 The full receipt is reachable through a generic output route

`crates/archeaxis-api/src/runtime/mod.rs:36` — `.route("/api/v1/jobs/:job_id/outputs/:kind", get(output))`.

`crates/archeaxis-api/src/runtime/mod.rs:291-306` — `output` selects
`metadata_json, content FROM job_outputs WHERE job_id=?1 AND kind=?2 AND attempt=(SELECT MAX(attempt) FROM job_attempts WHERE job_id=?1)`,
returns `Json({"metadata": <parsed metadata>, "content": <raw string>})` on success, `404 AAK-VAL-004 "output not found"` when absent, and `unavailable()` on store/parse failure.

`crates/archeaxis-api/src/runtime/mod.rs:27-43` — this router is **merged with** the base
projections: `let projections = crate::projections(executor.store().clone(), false); … .merge(projections)`.

`crates/archeaxis-api/src/main.rs:37` — the shipped binary constructs exactly that router:
`archeaxis_api::runtime::router(executor)`. So the route is **available in the real Core process**,
not only in tests. Note `manual_receipts=false` there, which only removes
`POST /api/v1/jobs/:job_id/receipts` (`crates/archeaxis-api/src/lib.rs:75`).

**Consequence:** assigning `kind = loss_report` returns the persisted receipt, but as a JSON
**string** in `content` (`crates/archeaxis-api/src/runtime/mod.rs:300`). A consumer must parse twice,
and the `archeaxis.loss-receipt/v1` schema is not applied at the API boundary.

### 2.3 The persisted receipt type is already strict

`crates/archeaxis-contracts/src/loss_receipt.rs:5-21` — `LossReceipt` with
`#[serde(deny_unknown_fields)]`: `engine`, `engine_version`, `params` (object), `loss_note`
(required, nullable), and optional `losses`, `covered`, `total`, `coverage`.

`crates/archeaxis-contracts/src/loss_receipt.rs:47-75` — `validate()` requires non-empty
engine/version, an object `params`, non-empty loss entries, and the invariant that
`covered`/`total`/`coverage` are supplied together with `coverage == covered/total` (with
`total == 0 → 1.0`), inside the exact-integer range. It states explicitly that coverage is
"a ratio of declared units, NOT a claim about extraction accuracy".

`crates/archeaxis-application/src/jobs.rs:98-102` — `complete_tx` rejects an empty engine, validates
the receipt, and rejects an engine mismatch, before serializing into `jobs.loss_receipt`.

### 2.4 There is no explicit fallback or unsupported field anywhere

Core models no `fallback` / `unsupported` flag on jobs, transforms or receipts. The text worker
records a decode fallback as a **named loss entry** plus a `params` value (DP-F01 asserts
`params.decode == "gbk"` and a human-readable loss entry for the GBK fixture). Any proposal that
promises a Core-level fallback boolean would invent semantics that do not exist.

### 2.5 Job outputs are per-attempt and attempt-fenced

`crates/archeaxis-store-sqlite/src/lib.rs:140` — `job_outputs` table (used by
`crates/archeaxis-application/src/attempts.rs:309` on insert, and read with a `MAX(attempt)`
subquery). The outputs route therefore always reads the latest attempt; earlier attempts are not
addressable through the API.

## 3. Proposal (for owner review — nothing implemented)

### 3.1 Option A (recommended): a typed loss-receipt projection

```
GET /api/v1/jobs/:job_id/receipt
```

- Read-only. Returns the persisted receipt as a **typed JSON object**, not a string:

```json
{
  "job_id": "...",
  "state": "succeeded",
  "engine": "python-worker-text",
  "engine_version": "0.1.0",
  "schema": "archeaxis.loss-receipt/v1",
  "params": { "decode": "utf-8-sig", "media_type": "text/markdown", "format": { "...": "..." } },
  "loss_note": "…",
  "losses": ["UTF-8 BOM stripped"],
  "covered": 17, "total": 17, "coverage": 1.0,
  "measured": { "accuracy": "NOT_MEASURED", "coverage_semantics": "declared-unit ratio, not extraction accuracy" }
}
```

Semantics to freeze if adopted:

| Condition | Required result |
| --- | --- |
| Unknown `job_id` | `404` (match the existing `"unknown job"` behaviour of `job_quality`) |
| Known job, no persisted receipt (e.g. queued/running, or failed without a receipt) | `200` with `"receipt": null` and an explicit reason; never a synthesized receipt |
| Receipt fails `LossReceipt` validation on read | `500` / `unavailable()` — never partially typed output |
| `losses` absent | `losses: null` and `measured.accuracy: "NOT_MEASURED"`; absence means unmeasured, per `loss_receipt.rs:24-27` |
| Coverage present | echo `covered`/`total`/`coverage` verbatim; do not recompute or round |
| Any accuracy-style field | must be a literal "not measured" marker. **No accuracy number may ever be emitted** |

### 3.2 Option B (smaller): extend the existing quality projection

Add `params` (verbatim) plus `losses` (verbatim) to `job_quality`'s JSON. This is a strictly
additive change to one route and needs no new route, but it mixes "summary" and "full receipt"
responsibilities on one endpoint and is harder to keep honest as the receipt evolves.

### 3.3 Option C (not recommended): change the outputs route

Making `/outputs/:kind` unwrap JSON content would break its existing generic contract (it also
serves `text` and `document_structure`, whose content is not JSON) and would invalidate current
consumers. Rejected.

### 3.4 Explicitly out of scope

- No schema change, no migration, no new table, no change to `SCHEMA_VERSION` (`= 6`,
  `crates/archeaxis-store-sqlite/src/lib.rs:8`).
- No worker change; no change to what the transport emits.
- No UI wiring in this proposal. If a receipt route is adopted, the Desktop must still consume it
  through an owner-approved write-set.
- No accuracy/relevance claims. The `measured` block exists precisely so a consumer cannot mistake
  presence-of-receipt for quality.

## 4. Why this cannot be closed by a test-only card

DP-F01 could assert the receipt through `/outputs/loss_report` **because it parses the string
twice in Rust**. A product UI or any non-Rust consumer would have to do the same, with no schema at
the boundary. A test that parses the string proves the data is durable; it cannot make the API
typed. Closing the consumer-facing part requires a production route decision — therefore this is a
proposal, not a fix, and it stays outside the DP-F01 write-set (which forbids Rust production
changes).

## 5. Requested owner decisions

1. **D1 — shape.** Option A (new typed `/receipt` route) or Option B (widen `/quality`)?
2. **D2 — schema at the boundary.** Should the response be validated against
   `archeaxis.loss-receipt/v1` before serialization, failing closed on mismatch?
3. **D3 — absence semantics.** Confirm `losses: null` / `receipt: null` with an explicit unmeasured
   marker is the honest representation, rather than defaulting to `[]`.
4. **D4 — attempt addressing.** Is latest-attempt-only sufficient, or must earlier attempts become
   addressable (which adds a query parameter and a retention question)?
5. **D5 — fallback/unsupported.** Confirm that Core must **not** invent a fallback or unsupported
   flag and that the worker's named-loss + `params` representation stays the single source of that
   fact.

## 6. Correction record (accuracy of prior reporting)

The DP-F01 card's first summary stated that a "non-runtime projections router exposes
`GET /api/v1/jobs/{job_id}/outputs/loss_report` (`crates/archeaxis-api/src/lib.rs:291-306`)" and
concluded the params were "NOT reachable through the runtime router".

Verified against the baseline, both parts were wrong:

- there is no separate `outputs` route in `crates/archeaxis-api/src/lib.rs`; `lib.rs` declares
  `/api/v1/jobs/:job_id/quality` (line 70) and `projections()` ends at line 77;
- the outputs route is `/api/v1/jobs/:job_id/outputs/:kind` in
  `crates/archeaxis-api/src/runtime/mod.rs:36`, i.e. **inside the runtime router**, and that router
  is merged with the base projections and is what the shipped binary serves (`main.rs:37`);
- the DP-F01 Rust test itself asserts `.../outputs/loss_report` and reads `params` successfully,
  which is direct evidence that params **are** reachable.

The corrected gap — no typed receipt projection, and `params` absent from `/quality` — is stated in
§1 and is the basis of this proposal. The same correction is applied to
`docs/current/dsh-review/dp-handoff-20260925.md` on the DP-GIT-01 branch.

## 7. Non-claims

- No test was executed for this note; the Rust and Python lanes cited here were executed under
  DP-F01, not for this document.
- Nothing in this note changes R6/M0 status, the release freeze, or any route authority.
- This proposal does not authorize touching `MainWindow.axaml(.cs)`, the theme, Core/API code,
  route authority, schemas, or any unavailable Research/Plugin/Model/Editor/Evidence contract.
