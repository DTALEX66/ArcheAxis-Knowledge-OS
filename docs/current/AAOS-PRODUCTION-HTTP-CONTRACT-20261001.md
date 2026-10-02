# AAOS Production HTTP Contract (live-verified) — 2026-10-01

Contract id: `archeaxis.production-http/v1`
Status: `PARTIAL` — the route inventory and authentication model below were read from the
source and then **observed on a real Core process**; every block marked `OBSERVED`
carries a receipt. Blocks marked `UNVERIFIED` were not exercised on this machine.

This document is the hand-off surface for the UI branch (`codex/aaos-ui-phase2-20261001`,
writer: MiniMax Design). It exists because the previous contract artifact
`packages/contracts/v1/openapi-outline.yaml` self-declares
`status: reference-not-implementation` and its path list is **stale**: it names
`/api/v1/workspaces`, `/api/v1/candidate-extractions`, `/api/v1/exports`,
`/api/v1/restore-validations` and `/api/v1/learning-items/{id}/events`, none of which
are registered, while omitting the real `/api/v1/evidence/anchors`,
`/api/v1/machine/tasks`, `/api/v1/learning/items/{item_key}/state` and others. A UI
built against that outline would call routes that return 404.

Source identity for every observation in this document:

| Item | Value |
| --- | --- |
| Source commit | `1a981a4482b01f31989074e79c82a63400aa07a7` |
| Worktree | `.project-local/worktrees/dsh-backend-loop-20261001` |
| Core binary SHA-256 | `a2d2746edb752fd7034940f129e874093fd71c35eea5aa65ac718eeeefeb8e29` |
| Storage schema version | `6` (`archeaxis_store_sqlite::SCHEMA_VERSION`) |
| Contract string reported by Core | `0.1.0-outline` |
| Launch protocol | `archeaxis.desktop-launch/v2` |

## 0. What the UI may do with this document

`docs/LANGUAGE_BOUNDARY_AUTHORITY_INDEX.md` fixes what each layer owns, and the UI's side of that
boundary is a constraint on how this contract is used, not decoration:

| Layer | Owns | Must not |
| --- | --- | --- |
| C#/Avalonia desktop (`apps/ArcheAxis.Desktop/`) | the UI and the Core supervisor | execute SQL, or **duplicate business rules** |
| Rust (`crates/`) | the vNext domain, jobs, storage and API; **the one authoritative writer** | write the legacy database |
| Python (`services/python-workers/`) | parsing, OCR, ASR, model and scheduling computation | hold a main-database handle, or grant human approval |

So this document is a **surface to call, not a specification to reimplement**. Concretely:

* the UI reads state through these routes and renders it; when it needs a decision — whether an
  item is assessable, whether a job settled, whether a schedule exists — the answer comes from the
  Core, and the UI must not recompute it from the fields it happens to see. §4 lists the fields
  that exist precisely so a reader does not have to guess which of them is authoritative.
* the UI never opens the workspace database, and never writes to the legacy one. There is no
  dual-write path and no live synchronization.
* the UI verifies readiness, `system/version`, session and workspace identity before using the
  business routes, and re-checks workspace identity after a restart rather than treating a
  successful response from another database as recovery.
* credentials stay out of the UI's logs, screenshots, public receipts and Git; the Core overwrites
  a wire-supplied actor, so sending one is never a way to widen access.
* a language or framework choice is **not** evidence that a capability is absorbed. Nothing in
  this document, and no directory layout, substitutes for R6 A13 / M0 P5 migration acceptance or
  for the P6 Owner gate on Green replacement.

## 1. Process model and launch handshake

The Core is a child process owned by the desktop Supervisor. It is **not** a service the
UI may start, restart or connect to on its own terms.

```
archeaxis-api <workspace-db-path> [port]
```

* `port` defaults to argv, then env `ARCHAXIS_VNEXT_PORT`, then `47831`. `0` asks the OS
  for a loopback port — the real desktop passes `0` and reads the chosen port from stdout.
  *Observed:* all three resolutions, including an argv port winning while the environment
  named a different one.
* Binding is **IPv4 loopback only**. There is no remote or LAN surface. *Observed:* an IPv4
  connection on `127.0.0.1` succeeds, a connection to `::1` on the same port is refused, and
  the host's own LAN address is not served. This is the claim with the most consequence for a
  client: a UI that resolved `localhost` to IPv6 would appear to fail while the Core is
  healthy, and a successful IPv6 connection would be a surface §1 says does not exist.
* Before binding, the parent must write **one** JSON line to the Core's stdin (≤4096 bytes)
  and close it within 5 s, or the Core exits `2`. *Observed:* an empty document, an unknown
  field, a v2 document with no `machine_token`, one whose `machine_token` equals
  `launch_token`, and a document over 4096 bytes all exit `2`, as does a call with no
  workspace argument.
* On success the Core writes one line to stdout:
  `archeaxis-api ready on http://127.0.0.1:<port>`. *Observed*, including the port chosen
  when `0` was passed.

Exit codes: `2` = usage / launch-input / launch-identity failure; `1` = workspace open,
executor init, identity protect, or bind failure.

All of the above is asserted by `crates/archeaxis-api/tests/contract_process_model.rs`, which
drives the real binary.

### Launch document (v2)

```json
{
  "protocol": "archeaxis.desktop-launch/v2",
  "actor": "human",
  "launch_token": "<64 hex>",
  "machine_token": "<64 hex, different from launch_token>",
  "session_id": "<32 hex>",
  "text_worker": {
    "python": "<absolute path to interpreter>",
    "script": "<absolute path to services/python-workers/transport/text_ndjson.py>",
    "staging": "<absolute writable directory>"
  }
}
```

Field rules (enforced, `crates/archeaxis-api/src/launch.rs`):

* `deny_unknown_fields` — an unknown key rejects the launch.
* v2 **requires** `actor:"human"` and a `machine_token` distinct from `launch_token`.
* v1 (no `protocol`) is a single-principal session and **rejects** `machine_token`.
* Each of `python` / `script` / `staging` must be absolute, must not be `e:`, `//` or
  contain `..`, must not traverse a reparse point, and `python` and `script` must be files.

`text_worker` is optional. Its presence decides the router (see §6) — this is the single
most consequential fact for UI behaviour.

## 2. Authentication and identity

Every claim below was exercised against a live Core and is asserted by
`crates/archeaxis-api/tests/contract_auth_boundaries.rs`. The observations are recorded with
each line, because two of them are easy to get wrong in a client.

* Every request to every route must carry **exactly one** `x-archeaxis-launch-token`
  header. Duplicate headers are rejected. *Observed:* a duplicated header answers
  `401 AAK-AUTH-001`, as does no header at all.
* The value is compared (constant time) against `launch_token` **or** `machine_token`.
  No match → `401 `AAK-AUTH-001``. *Observed:* a value of the right length with the wrong
  content, a value of the wrong length, and an empty value all answer the same `401`.
* **Both principals use that same header.** There is no second header for the machine token.
  *Observed:* sending the machine token in `x-archeaxis-launch-token` answers `200`, while the
  otherwise-plausible `x-archeaxis-machine-token` and `x-machine-token` both answer `401` —
  a client that names the machine header gets a credential error rather than a machine request.
* **The actor is derived server-side from which token matched.** Matching `machine_token`
  makes the request a machine request; otherwise it is human. *Observed on a machine-only
  route:* the machine token succeeds even when the request also claims `x-archeaxis-actor:
  human`, and the human token is refused with `403 machine task receipts are written by a
  machine principal only` even when it claims `x-archeaxis-actor: machine`.
* The Core **overwrites** `x-archeaxis-actor` before dispatch, so a client cannot escalate
  by sending that header. Wire-supplied `x-archeaxis-actor` / `x-archeaxis-scopes` are
  ignored in production.
* Any request carrying an `origin` header → `403 `AAK-AUTH-002` browser origin not allowed`.
  The formal desktop is a native client; a browser is deliberately not a valid client.
  *Observed:* refused with a valid token, and `origin: null` is refused too.
* There is **no** `x-archeaxis-machine-token` header in this protocol.
* Human-only and machine-only routes refuse the other actor: *observed* the machine token on
  a human-only review route answers `403 machine principal cannot perform human review
  actions`.

> Defect fixed in this branch: `scripts/release/backend_launcher.py` published the machine
> token under `x-archeaxis-machine-token`, which the Core never reads. A machine call made
> with those credentials was therefore authenticated as the **human** actor — a silent
> identity downgrade rather than a visible error. The launcher now selects the credential
> by role and sends the machine token in `x-archeaxis-launch-token`.

### Health and identity readback (OBSERVED)

`GET /api/v1/system/version` is answered by the auth middleware before route dispatch, so
it is the only route that reports the session identity the Supervisor should verify.

```json
{
  "runtime": "archeaxis-api",
  "contract": "0.1.0-outline",
  "schema_version": 6,
  "session_id": "dddddddddddddddddddddddddddddddd",
  "workspace_db": "\\\\?\\D:\\...\\workspace.sqlite",
  "launch_protocol": "archeaxis.desktop-launch/v2",
  "actor": "human"
}
```

`launch_protocol` and `actor` appear **only** for a v2 launch. The Supervisor compares
`runtime`, `contract`, `launch_protocol`, `actor`, `session_id` and `workspace_db`
against what it launched; a mismatch means it is talking to a different Core.

`runtime` and `contract` are hard-coded string literals, not derived from the crate
version. Do not use them to infer a build.

## 3. Route inventory (35 pairs in a `text_worker` launch)

`PROD` = reachable in a production launch. `PROD` marks the routes the UI may rely on.
All paths are relative to the loopback base URL.

### Session and workspace

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 1 | `GET /api/v1/system/version` | any token | Session/identity readback. See §2. |
| 26 | `GET /api/v1/workspaces/info` | any token | Workspace projection. |

### Capability registry (R7/G1)

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| R5 | `GET /api/v1/capabilities` | any token | The routes the Core actually registered, one record each: `capability`, `provider` (kind, worker path, whether the worker and interpreter files exist, whether the route may import site packages), `enabled`, `health`, `is_default`, `fallback`. **Left with the executor rather than the projections because it reads the registered routes**, and it reads no database, so it answers even when the store will not open. |
| R6 | `GET /api/v1/capabilities/{capability}` | any token | One capability by its **exact** dot-separated name. A near miss is `404` with a plain-text body rather than the nearest match, because a registry that guesses is worse than one that says it does not know. |
| R7 | `PUT /api/v1/capabilities/{capability}/enabled` | any token | Body `{"enabled": true\|false}`. **`enabled` is a required boolean and unknown fields are `422`** — `{}` must not be read as "disable", which would make the most destructive action the default. Answers with the record re-read from the workspace, not echoed from the request. A capability that is not registered is `404`; a capability the workspace has turned off is refused by the execute path with `409 AAK-CAP-001` and by the claim transaction, so no attempt row is created. |
| R9 | `POST /api/v1/ask` | any token | Body `{"question","limit"?}`. Answers from **accepted material only**, and every answer is the cited excerpts themselves rather than a Core-composed paraphrase, so a claim with no citation cannot appear. Each citation carries the knowledge id, status, an excerpt, its **anchor** (id, source id, revision, position) and the **source** file name, so a reader can open the thing being quoted; an item with no anchor says so instead of inventing provenance. A blank question or an unknown field is `422`. **No match is `answered: false` with `answer: null`**, not an empty string, because "the workspace says nothing" and "nothing matched" are different facts. `authority` is `projection_of_accepted_knowledge`, and the route writes nothing. |
| R8 | `POST /api/v1/machine/answers` | any token | Body `{"knowledge_id","question","max_tokens"?,"timeout_s"?}`. Asks the local model one question about **one accepted knowledge item**, whose own `body` is the context, so an answer is grounded in material this workspace accepted. **There is no free-text context field** and an unknown field is `422`: an answer grounded in a caller-supplied string would be unverifiable. Replies `{"schema":"archeaxis.machine-answer/v1","knowledge_id","question","authority":"candidate","note","answer"}`, where `answer` is the worker's own JSON with its `loss_receipt`. A blank question is `422`, an unknown or bodyless knowledge item is `404`, a disabled `machine.answer` is `409`, and a model that cannot answer is `503` with the worker's own reason. **Nothing here writes knowledge and nothing is promoted.** |

Three limits are part of the contract, not caveats on it:

* `health` is `declared`, `worker_missing` or `interpreter_missing` — **file existence only**. A
  passing entry is not evidence a capability works; only a job is. The body says so in
  `health_basis` and `declared_only`.
* `enabled` comes from the workspace's own `capability_settings` record, where **an absent row means
  enabled** so the table records decisions rather than restating the launch. When that record cannot
  be read the field falls back to the registration state and `enabled_basis` says so, instead of
  reporting a decision nobody made.
* `is_default`, `default_provider` and `fallback` describe **which registered route would answer**.
  `is_default` is true only for the provider the Core actually chooses — the first registered route
  whose worker and interpreter files both exist — and `default_provider` names it. Reporting
  `is_default` true on every row, as this contract first did, described a registry that cannot say
  who answers. `fallback` names a second registered route, and is reported **only on the default's
  record** because naming one on every row would leave a reader unable to tell which provider runs.
* **No capability has a second provider in a production launch yet**, so `fallback` reads `null`
  there. The field becomes meaningful as soon as a launch declares two routes for one capability, and
  the tests cover that case rather than leaving it to the future: a route whose worker is missing is
  skipped in favour of a usable one, because registering a broken route is a configuration mistake
  rather than a provider choice.

Disabling is a real barrier, not a label: `attempts::claim` reads the record inside the claim
transaction, so a disabled capability leaves behind no attempt row, no staging copy and no partial
output. The `409` is produced before the worker starts, and an attempt to disable a capability that
is not registered is a `404` rather than a row about nothing.

### Source intake and conversion

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 2 | `POST /api/v1/imports` | any token | Body `{name, content_base64}`. `202` + `source_id` is **acceptance, not conversion**. |
| 3 | `POST /api/v1/jobs` | any token | Body `{job_id, kind, input_ref}`. `kind` selects the route (§6). |
| R2 | `POST /api/v1/jobs/{job_id}/executions` | any token | Requires header `idempotency-key`. Body `{deadline_ms}` (1..300000). `202` follows a durable claim, not completion. |
| R1 | `GET /api/v1/jobs/{job_id}` | any token | `{job_id, state, attempt, request_id, error}`. `state` ∈ `queued`/`running`/`succeeded`/`failed`/`cancelled`. |
| R3 | `POST /api/v1/jobs/{job_id}/executions/{request_id}/cancel` | any token | Requesting a cancel is not the same as observing `cancelled`; re-read the job. |
| R4 | `GET /api/v1/jobs/{job_id}/outputs/{kind}` | any token | `200` with `{content, metadata}`; `metadata` carries `kind`, `schema`, `sha256`, `byte_length` and `authority_effect: "candidate_or_measurement_only"`. A text job writes `text`, `document_structure` and `loss_report`. **Every other answer is `404 AAK-VAL-004` "output not found"** — a kind this job never writes, a kind no route writes, a job that does not exist, *and* a job that has not finished. The status cannot distinguish those, so resolve with the job's own state: `running`/`queued` → retry, `succeeded` → it will never appear. Reads the **latest attempt's** rows, so a replay does not blank them. |
| 22 | `GET /api/v1/jobs/{job_id}/quality` | any token | Aggregate projection; not a typed loss receipt. |
| 5 | `GET /api/v1/sources/{source_id}/jobs/{job_id}/transform` | any token | The succeeded job's stored projection, whatever its kind: every extraction route writes its projection to `transforms.text`, so a PDF, OCR, Office, HTML, canvas, subtitle, archive, media or ASR transform reads back here. A job with no stored projection is `404`, and the `source_id` binding is enforced rather than the job id alone. |
| 24 | `GET /api/v1/sources/{source_id}/members` | any token | Source members. |
| 25 | `GET /api/v1/sources/{source_id}/jobs` | any token | Jobs for a source. |

### Evidence and knowledge

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 4 | `POST /api/v1/sources/{source_id}/anchors` | any token | Anchor creation. |
| 23 | `GET /api/v1/evidence/anchors` | any token | Anchor listing. Not a complete cross-domain evidence service. |
| 6 | `POST /api/v1/knowledge-items/from-transform` | any token | Body carries `knowledge_type` and `body` (both **required**, no defaults), plus `source_id`, `job_id`, `transform_id`, UTF-16 selection range and `quote`. Core validates the **persisted** transform and selection. Returns a **candidate** + anchor. |
| 7 | `POST /api/v1/knowledge-items` | any token | Direct candidate creation. Body `{knowledge_type, body, status, created_by, v3?}` — all four are **required**. **There is no `review_state` field**, and an unknown field is silently ignored, so sending `review_state:"accepted"` leaves the item at whatever `status` you sent; to make an item assessable, send `status:"accepted"`. See the request-body table in §4. |
| 8 | `GET /api/v1/knowledge-items/{id}/v3` | any token | Knowledge V3 projection (`schema_version: "3.0.0"`). |
| 9 | `GET /api/v1/knowledge-items/{id}/qualification` | any token | Qualification projection. |
| 10 | `POST /api/v1/knowledge-items/{id}/review-decisions` | **human only** | Body `{action, reviewer, new_body?, note?}`; `action` ∈ `accepted`/`rejected`/`deprecated`/`modified`. Machine principal → `403`. This is the **only** human-correction write path; `modified` creates a successor revision. |

### Search

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 21 | `GET /api/v1/search?q=&active_only=` | any token | Lexical **FTS5 only**. Returns `count`, `items[]`, `transforms[]`. `count=0` is a successful empty result. No vector, reranker or graph route exists. |

### Human learning

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 15 | `POST /api/v1/learning/items/{item_key}/references` | any token | Links an accepted knowledge id. **No actor guard** — a machine principal may call it. |
| 17 | `POST /api/v1/learning/items/{item_key}/assessment` | any token | Body `{knowledge_id}`. **No actor guard.** Returns `assessment_id` + `knowledge_version`. |
| 16 | `GET /api/v1/learning/items/{item_key}/assessment` | any token | Latest assessment. |
| 12 | `POST /api/v1/learning/reviews` | **human only** | Body `{item_key, client_event_id, exposure_id?, assessment_id, knowledge_version, answer, correct, rating?, now?}`. `rating` is a **number**, not a label, and is optional. `assessment_id` is required **whenever `answer` is submitted**, and `knowledge_version` must equal the one the assessment reports or the Core answers `400`. `client_event_id` is the idempotency identity — retry replays the original receipt. Machine → `403`. Never falls back to the placeholder ladder. The response carries `mastery_projection`. |
| 11 | `POST /api/v1/learning/events` | **human only** | Legacy keyed path. With no `schedule_state`, authority is `placeholder_ladder` and `next_review` is `null`. With `schedule_state`, the reused FSRS worker decides. Machine → `403`. |
| 13 | `GET /api/v1/learning/events/{item_key}` | any token | Event history. |
| 14 | `GET /api/v1/learning/items` | any token | Queue; one latest deadline per item. |
| 18 | `GET /api/v1/learning/items/{item_key}/state` | any token | Learner state + a **fixed** `machine` block (§4). |

### Machine loop

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 19 | `POST /api/v1/machine/tasks` | **machine only** | Body `{task_id, conditions, knowledge_version, method_version, tool_version, model_version, scope, outcome, failure?, retest_of?}`. `outcome` ∈ `succeeded`/`failed`/`unmeasured`. Receipts are immutable. Human → `403`. |
| 20 | `GET /api/v1/machine/tasks/{task_id}` | **machine only** | Readback projection. |

## 4. Fields that are constants, not data

The UI must not render these as measured values.

* `GET /learning/items/{item_key}/state` → `machine` is the fixed literal
  `{"status":"not_recorded","note":"machine capability receipts are written by the machine
  loop; learner progress is never presented as machine competence"}`. It is
  `not_recorded` **even when machine receipts exist**, because no route writes the machine
  competence ledger — so a UI must not present `not_recorded` as "the machine has done
  nothing". Both states are driven by `crates/archeaxis-api/tests/contract_constant_fields.rs`.
* `learner.recording` is a fixed explanatory string.
* Fixed `note` literals are appended to real data on machine readback, job quality and
  source members. The notes at those three routes are asserted to be present by
  `crates/archeaxis-api/tests/contract_constant_fields.rs`.
* `mastery_projection.closed` is a **constant `false`** and `mastery_projection.status` is the
  constant `"projection"` — mastery is deliberately an open projection, never a closed claim, and
  the projection is not Knowledge Truth. The projection's keys are exactly
  `basis`, `closed`, `correct_streak`, `review_state`, `stability`, `status`. `correct_streak` is
  re-derived on every read. **Where to
  find it:** the projection travels with a `POST /learning/reviews` response and reaches
  `GET /learning/items/{item_key}/state` under `learner.latest_review.mastery_projection` —
  **not** at the response's top level, which is `null` until a review exists. The same test
  checks that `correct_streak` equals the correct events on record.
* An event's `outcome` in `GET /learning/events/{item_key}` is a **JSON document carried as a
  string** (`"{\"outcome\": \"correct\"}"`), not a bare word. A UI that compares it to
  `"correct"` directly will see every event as unknown.
* `POST /learning/events` without `schedule_state` reports
  `schedule_authority:"placeholder_ladder"` and `next_review:null`. That is the 1/2/4/7/14
  stub, **not** FSRS. Distinguish it from `"fsrs"` and from `"unavailable"`.
* **`schedule_authority` has three values, and `POST /learning/reviews` can only produce two of
  them.** Which one appears depends on the interpreter the Core was launched with, so it is a
  property of the launch, not of the request:

  | `ARCHEAXIS_PYTHON` points at | `schedule_authority` | `next_review` | `next_review_days` |
  | --- | --- | --- | --- |
  | an interpreter with `fsrs` | `"fsrs"` | a real timestamp | `0` |
  | no such variable, or a path that does not exist | `"unavailable"` | `null` | `-2` |

  Observed all three cases against the real binary. `"placeholder_ladder"` does **not** appear on
  this route in either case — it belongs to `POST /learning/events` with no `schedule_state`. A UI
  that renders `unavailable` as "scheduled" is making a claim the Core explicitly declined to
  make, which is why the launch injects `ARCHEAXIS_PYTHON` rather than asking a user to set it.
* `mastery_projection.schedule` is `null` on a review even when `schedule_authority` is `"fsrs"`,
  so the schedule must be read from the top-level fields, not from the projection.
* When no `knowledge_v3_metadata` row exists, the V3 projection invents
  `confidence:null`, `risk_level:"low"` and a `support_level`.

**Request bodies ignore unknown fields.** Every body struct is deserialised with serde's default
behaviour, so a misspelled or renamed field is **silently dropped** — the request still succeeds,
just not doing what the caller meant. This has cost real time on this branch three times
(`review_state`, `review_state` again on a different route, and `body` where the field is
`new_body`), so the exact field names are listed here and asserted against the source by
`tests/maintenance/test_request_body_fields.py`.

| Route | Body fields (`?` = optional) |
| --- | --- |
| `POST /api/v1/imports` | `name`, `content_base64`, `origin_kind?`, `origin_ref?`, `origin_name?`, `received_at?` |
| `POST /api/v1/jobs` | `job_id`, `kind`, `input_ref` |
| `POST /api/v1/jobs/{job_id}/executions` | *(no body fields; needs the `idempotency-key` header)* |
| `POST /api/v1/sources/{source_id}/anchors` | `revision`, `position` |
| `POST /api/v1/knowledge-items` | `knowledge_type`, `body`, **`status`**, **`created_by`**, `v3?` |
| `POST /api/v1/knowledge-items/from-transform` | `knowledge_type`, `body`, `source_id`, `job_id`, `transform_id`, `selection_start_utf16`, `selection_end_utf16`, `quote` |
| `POST /api/v1/knowledge-items/{id}/review-decisions` | `action`, `reviewer`, `note?`, **`new_body?`** |
| `POST /api/v1/learning/items/{item_key}/references` | `knowledge_id` |
| `POST /api/v1/learning/items/{item_key}/assessment` | `knowledge_id` |
| `POST /api/v1/learning/events` | `item_key`, `kind`, **`correct`**, `client_event_id?`, `schedule_state?`, `now?` |
| `POST /api/v1/learning/reviews` | `item_key`, `client_event_id`, `correct`, `rating?`, `now?`, `answer?`, `assessment_id?`, `question_version?`, `knowledge_version?`, `exposure_id?`, `assist_strategy?`, `rating_version?`, `correction_id?` |
| `POST /api/v1/machine/tasks` | `task_id`, `conditions`, `model_version`, `scope`, `outcome`, `knowledge_version?`, `method_version?`, `tool_version?`, `failure?`, `retest_of?` |
| `POST /jobs/{id}/receipts` (out of contract) | `state`, `engine?`, `text?`, `loss_receipt?`, `error?` |

The `v3` sub-object is `POST /api/v1/knowledge-items`'s nested body: `source_type`, `owner`,
`support_level`, `confidence?`, `risk_level`, `valid_from?`, `valid_to?`, `external_evidence`,
`requires_human_review`.

`GET /api/v1/search` takes **only** `q` and `active_only`. There is **no** `limit`, `offset`,
`sort` or `page` parameter, and no filtering beyond `active_only` — the result limit is a
hardcoded 20 in `crates/archeaxis-api/src/lib.rs`. A UI wanting paging has to do it client-side
and cannot ask for more than that many matches.

## 5. Idempotency, conflicts and errors

**Error bodies are not uniform, and the groups are not the ones a reader would guess.** Measured
with `crates/archeaxis-api/tests/contract_absent_surfaces.rs`: the auth middleware **and the two
job routes** answer JSON; every other family answers **plain text**.

| Error | Status | Content-Type | Body |
| --- | --- | --- | --- |
| missing / duplicated / unmatched credential | `401` | `application/json` | `{"code":"AAK-AUTH-001","message":"invalid launch credentials","retryable":false}` |
| any `origin` header | `403` | `application/json` | `{"code":"AAK-AUTH-002","message":"browser origin not allowed","retryable":false}` |
| unknown job (`GET /jobs/{id}`) | `404` | `application/json` | `{"code":"AAK-VAL-004","message":"job not found","retryable":false}` |
| unknown job outputs (`GET /jobs/{id}/outputs/{kind}`) | `404` | `application/json` | `{"code":"AAK-VAL-004", …}` |
| unknown job quality | `404` | `text/plain` | `unknown job` |
| unknown source members | `404` | `text/plain` | `source not found` |
| unknown knowledge (`GET /knowledge-items/{id}/v3`) | `404` | `text/plain` | `knowledge not found` |
| unknown machine task | `404` | `text/plain` | `unknown machine task` |
| unknown `knowledge_type` | `400` | `text/plain` | `Invalid parameter name: unknown knowledge_type: NOPE` |
| missing required body field | `422` | `text/plain` | `Failed to deserialize the JSON body into the target type: missing field \`knowledge_type\` …` |
| the other actor's route | `403` | `text/plain` | `machine principal cannot record human reviews` |

**Consequence for the UI:** parse the body as JSON for the auth middleware and the job routes; for
every other error the body is plain text, so a client that unconditionally parses JSON fails there.
Reading a `code` field gives a stable value (`AAK-AUTH-00x`, `AAK-VAL-004`) only on the JSON
group, and the same `AAK-VAL-004` covers both "no such job" and "no such output", so the message
is what distinguishes them.

The table below names the status meanings; the shapes above are what actually arrives.

| Status | Meaning | Real examples |
| --- | --- | --- |
| `200` / `201` / `202` | Accepted or returned. `202` on import/execute is **not** completion. | import `202`, knowledge create `201`, review `201` |
| `400` | Malformed identity or request field (e.g. a bad `now`, an unknown `retest_of`). | |
| `401` | `AAK-AUTH-001` — missing, duplicate or unmatched credential header. | `{"code":"AAK-AUTH-001","message":"invalid launch credentials","retryable":false}` |
| `403` | `AAK-AUTH-002` browser origin; or a principal calling a route guarded to the other actor. | `{"code":"AAK-AUTH-002","message":"browser origin not allowed","retryable":false}` |
| `404` | Unknown object, or a route that is not registered in this launch. | |
| `409` | Idempotency key reused with a different payload, or a disallowed state transition. | |
| `422` | A field the route validates (e.g. a machine principal injecting `schedule_state`). | |
| `503` | Runtime or terminal storage unavailable. | |

Conflict semantics the UI must honour:

* Re-POSTing `/jobs/{id}/executions` with the **same** `idempotency-key` and the same
  payload replays; a **different** payload under the same key is `409`.
* Re-POSTing a review with the same `client_event_id` returns `duplicate: true` and the
  original receipt; it does not schedule twice.
* A job that has settled `succeeded` is not re-executed.

UI states to map explicitly: `loading / empty / error / offline / permission / conflict /
unavailable`. `200` with `count=0` is a successful **empty** state, not an error.

Each of those states was then **exercised against a live Core** rather than assumed, and the
`empty` state did not hold: see *Search query semantics* below. After that fix, ten probes
across the states report no mismatch:

| State | How it was provoked | Observed |
| --- | --- | --- |
| `empty` | a search for text that cannot occur, an empty `q`, a query of only operators | `200`, `count: 0` |
| `permission` | no `x-archeaxis-launch-token`; an unknown token; a browser `origin` header | `401 AAK-AUTH-001`; `401 AAK-AUTH-001`; `403 AAK-AUTH-002` |
| `error` | a job body with neither `job_id` nor `input_ref`; an import with no name | `422` |
| `unavailable` | a `pdf` job on a launch that declares no route for it | job settles `failed` |
| `conflict` | an execution replayed under a different `idempotency-key`, and under the same one | see *Idempotency* above |
| `offline` | any remote-sync surface | `404` — the Core has none, which is the contract's claim |

`loading` has no server representation: it is the interval before the first response, so the
UI owns it.

### What a review costs, and why the UI should not block its own thread on it

`POST /learning/reviews` waits for the FSRS worker **inside** the single-writer callback
(`crates/archeaxis-api/src/lib.rs` → `with_store`, recorded as a known limitation in
`docs/architecture/CURRENT_ARCHITECTURE.md`). Measured on this host, five reviews each way:

| Launch | `schedule_authority` | `POST /learning/reviews` median | a projection read, for scale |
| --- | --- | --- | --- |
| no usable scheduler interpreter | `unavailable` | **3.0 ms** | 14.7 ms |
| interpreter with `fsrs` | `fsrs` | **83.1 ms** | 15.0 ms |

The 83 ms is the subprocess round trip; the 3 ms case does not spawn one. Two consequences for the
UI: a review is roughly **6× a projection read** when scheduling is real, and because the wait
happens inside the writer, the one writer is occupied for that whole time — so reviews are the
serialisation point, not the reads. The UI should keep review submissions off its render thread and
expect a noticeable pause, rather than treating this route as a fast call.

Numbers are from a debug build with an empty workspace, so treat them as a shape (fast read, slow
write that holds the writer) rather than as production timings.

### Search query semantics

`GET /api/v1/search?q=` treats `q` as **text a person typed**, not as a query expression. The
core tokenises it on whitespace and matches rows containing **any** of the tokens, with
ranking ordering rows that match more of them first. Consequences the UI can rely on:

* `q` may contain anything — punctuation, quotes, hyphens, `AND`/`OR`/`NOT`, or be empty. None
  of these is an operator, and none produces an error. A `q` with nothing searchable in it is
  `200` with `count: 0`.
* **No phrase or boolean syntax is available.** A quoted string is not a phrase request and
  `OR` is not an operator; they are words like any other. A UI that wants "all of these words"
  must not express it as `AND`.
* A hyphen is a token separator: `radius-6371` matches text containing those tokens adjacent,
  and does not match them apart.

Before the fix this endpoint answered `500` with a raw FTS5 parser message for
`zzz-no-such-term`, an empty `q`, `zzz OR` and an unterminated quote.

## 6. Launch shape decides the router — the critical integration fact

| Launch | Routes served | Consequence for the UI |
| --- | --- | --- |
| **no** `text_worker` | 26 projection addresses (25 mounted routes, one of which carries GET and POST, plus the conditional legacy `/jobs/{id}/receipts`) | `/jobs/{id}`, `/executions`, `/outputs`, `/cancel`, `/capabilities` and its enable/disable write are **absent** (`404`). |
| **with** `text_worker` | 35 addresses (the 26 projection addresses + the 9 runtime routes) | All routes above are served. |

The runtime builder carries six routes: the four job-execution ones plus the two capability
registry reads added by R7/G1. They are mounted there rather than with the projections because
the capability surface reads the executor's registered routes, and the executor is the runtime
router's state while the projection builder holds only the store.

Both shapes were started from the real binary and asked over HTTP, and the result is asserted by
`crates/archeaxis-api/tests/contract_launch_shape.rs`. **How to tell "absent" from "no such
object":** ask the path with the *wrong* method. A mounted path answers `405 Method Not Allowed`;
an absent one answers `404`. The four **job-execution** runtime paths answer `405` with a worker and
`404` without one, while all projection paths answer `200` in both shapes. This matters because
with a worker the *correct*-method answer for an unknown job is also `404`, so a UI cannot
conclude from a `404` alone that the runtime routes are missing.

The three **capability registry** paths behave differently and the difference is deliberate: they
depend on the runtime router, not on a worker, so they answer `200` in both launch shapes. A
workspace that has declared no worker can still be asked which capabilities exist — that is the
question a broken launch most needs answered.

`POST /api/v1/jobs/{job_id}/receipts` is **not** in the production surface. It is mounted
only when the in-process router is built with `manual_receipts=true`, which the shipped
binary never does; a test asserts it answers `404` in the runtime router. Do not call it.

### Format reachability in a production launch (OBSERVED — see §7)

The production binary registers exactly **one** capability route, `text.extract`
(`Executor::open`). Every other format route exists only in test code
(`Executor::open_routes`). The configured worker script advertises only
`["text.extract"]`. Measured against the verified golden corpus:

| Fixture | Declared `kind` | Observed result |
| --- | --- | --- |
| `golden-text-anchor.txt` | `text` | **succeeded** |
| `golden-journey-evidence.pdf` | `pdf` | failed — `Core execution ended without a terminal receipt` |
| `golden-screenshot-ocr.png` | `image` | failed — same |
| `golden-docx-anchor.docx` | `office` | failed — same |
| `golden-pptx-anchor.pptx` | `office` | failed — same |
| `golden-xlsx-anchor.xlsx` | `office` | failed — same |
| `golden-web-anchor.html` | `html` | failed — same |
| `learning-evidence.canvas` | `canvas` | failed — same |
| `golden-audio-anchor.wav` | `media` | failed — same |
| `golden-video-anchor.mp4` | `media` | failed — same |

**Contract obligation for the UI:** until the Core registers the format routes, a non-text
job settles `failed` after being accepted with `202`. The UI must present that as
`unavailable` for the format, not as a conversion error, and must not offer a retry that
cannot succeed. Formats with no route at all (video decode, webpage fetch) must be reported
`unavailable` rather than `error`. ASR transcription now has a route and reaches the Core; its
engine must be present on the runtime, and the readiness check in §7 says so per route.

**A local model runtime is present, and this changes why some things are unavailable.** This
document previously said caption/VL needed "an absent local engine". A real vision model is served
locally and produced a real caption from a real fixture, and real text generation was measured too —
see the runbook for the receipts. So for `image.caption`, and for the machine loop, the blocker is
**wiring rather than a missing model**. A UI should still render those surfaces as not connected,
because no route reaches the model yet, but it should not be told the capability is impossible:

## 7. Evidence

| Claim | Command | Result |
| --- | --- | --- |
| Route inventory and auth model | source read of `crates/archeaxis-api/src/{main.rs,lib.rs,launch.rs,runtime/mod.rs}` | matches table above |
| Continuous M0 loop through the real Core | `ARCHEAXIS_CORE_BIN=<built core> python -B scripts/probes/m0_full_loop_smoke.py` | **27/27 stages ran**, `chain_stages_verified: true`, **`validation_errors: []`**, `ok: true`, `evidence_level: SYNTHETIC`. `answer_recorded.schedule_authority = "fsrs"`; `learning_event` (no card state) `= "placeholder_ladder"` in the same run, which is the two-route split §4 describes; restart readback identical on both `learning_state` and `knowledge_v3`; `machine_retest.retest_of` points at the failed task; online backup `exit_code 0` and restore `verified true` with `counts_after == counts_before`. **Re-run on this branch** rather than quoted: an earlier reading of this row said the sole validation error was `legacy migration not verified`, which was true of that environment and is not true of this one |
| Format reachability, **current** | `python -B scripts/probes/staged_format_matrix_smoke.py <core> <runtime-python>` | readiness `total 9 / ready 9 / not_ready 0`; `verdict_counts: {CONVERTED: 9}` on real course material; `accepted: true` |
| Format reachability, superseded measurement | `python -B scripts/probes/production_format_coverage_smoke.py` | `{REACHABLE: 1, FAILED_AT_ROUTE: 9}` — the state before route enablement; kept as the record of what was found |
| Format reachability, independently reproduced (at that time) | a separate direct launch of the same Core, `kind=pdf` vs `kind=text` control | PDF settled `failed` with the same error and its `job_attempts` row showed `capability=pdf.extract` never terminated; the `text` control `succeeded` |
| Real user material, superseded measurement | `python -B scripts/probes/real_material_conversion_smoke.py` | `{CONVERTED: 1, FAILED_AT_ROUTE: 5}` against a real Obsidian knowledge base. Superseded by the staged matrix above, which measures ten routes on real course material; this probe has not been re-run since and no newer figure is claimed for it |
| Engines present and working with declared paths | `worker_transcribe.py --probe`/transcribe, `worker_ocr.py` | real ASR of a real 5.8 MB Chinese MP3 → 3,362 chars / 295 segments; real OCR of a Chinese image → `三命通会` read correctly, `covered 3/3`. ASR is additionally reachable through the Core now (`media.transcribe`) |
| Route count in a production launch | the staged profile's own `routes` | **10** capabilities declared and served, including `media.transcribe`; the 30-route projection/runtime split in §6 is unchanged |
| Rust API suite | `cargo test -p archeaxis-api --no-fail-fast` with `ARCHEAXIS_PYTHON` set | all targets pass |
| Rust application (per-format) suite | `cargo test -p archeaxis-application --no-fail-fast` | all targets pass |
| Contract conflict rules | `cargo test -p archeaxis-api --test contract_conflict_rules`, and a live-Core probe | replay is `202 replayed:true`; a different deadline or a different job under one key is `409 AAK-CON-002`; a settled job is `409 AAK-CON-003`; no conflict path leaves a second attempt |
| **Local model runtime, measured** | `http://127.0.0.1:1234/v1` (LM Studio) with the shared library at `D:\\All projects\Model library` | six models served; `qwen3.5-4b` answered `AAOS-LOCAL-MODEL-OK` (`finish_reason: stop`, 4.5 s); `qwen2.5-vl-7b-instruct` captioned the real fixture `golden-screenshot-ocr.png` correctly; embedding and reranker models served. This **replaces** the earlier false claim that no real model exists |

Evidence level for this document: **REAL** for the route inventory, authentication model
and format-reachability measurements (real binary, real HTTP, real verified fixture bytes);
**SYNTHETIC** for the M0 loop receipt, which the probe itself labels as such because the
source, the human actions and the model failure are fixtures.

### What the M0 receipt's 27th stage does and does not mean

The chain's last stage reports `legacy_migration: status "ok"`, and it is worth being exact about
it, because it sits next to a frozen boundary. The stage migrates a **temporary copy** of
`data/cognitive_os.sqlite` — it copies the file, records the original's `sha256` before and
after, and asserts `original_untouched`. So the run demonstrates that the migration *capability*
works and that it left the source alone; it does **not** migrate any user data, does not replace
anything in place, and does not publish. Production legacy migration, in-place Green replacement
and release remain **`NOT_EXECUTED`** by the Owner's decision, and nothing here changes that.

The probe skips the stage when that file is absent, which leaves `status` unset and makes the
chain's own validation fail with `legacy migration not verified`. That is the message an earlier
reading of this document recorded; on this host the file is present and the stage runs.

## 8. Explicitly out of contract

Everything in this section is a **route family a UI might reasonably try and must not**, because
it does not exist. "Does not exist" is checked the only way that distinguishes it from "exists but
has no such object": `404` to the family's own method **and** `404` to a wrong method. A mounted
path answers `405` to a wrong method, so the wrong-method probe is what makes the claim testable.
Asserted by `crates/archeaxis-api/tests/contract_absent_surfaces.rs`.

**G4 status, stated plainly.** A real local model works here: `POST`ing to `/chat/completions` on the
OpenAI-compatible server at `127.0.0.1:1234` returns an answer with `finish_reason: stop`, and the
worker `services/python-workers/machine/worker_machine_answer.py` wraps that with endpoint
resolution, a capability probe, a token budget it reports, and a receipt labelling the answer a
**candidate**. Its identity is registered, so a launch may declare it.

What does **not** exist is a Core route that drives it. A route in the worker transport is validated
against the job protocol, and that protocol requires `parameters` to be empty, so there is no way to
carry the question the worker needs. Declaring a route there anyway would be a route that fails its
own validation. **The missing piece is a Core route that accepts a question**, and until it exists a
UI must show machine answering as not connected rather than calling anything.

| Attempted route | Observed | Meaning for the UI |
| --- | --- | --- |
| `GET/POST /api/v1/research`, `/research/tasks` | `404` in both methods | no research surface; show "not connected", never a success state |
| `GET/POST /api/v1/plugins` | `404` in both methods | no plugin surface; never render "plugin active" |
| `GET/POST /api/v1/models`, `/models/providers` | `404` in both methods | no model or provider surface; never render a provider or model version |
| `GET /api/v1/embeddings/search` | `404` in both methods | there is no embedding route |
| `GET /api/v1/graph/search` | `404` in both methods | there is no graph route |

* Legacy copy migration, in-place Green replacement, release/tagging — **paused by the
  Owner**. Not available through this API and not to be assumed by the UI.
* **`GET /api/v1/search` is lexical, not semantic.** It does not represent embedding, hybrid or
  graph retrieval, and a UI must not label it as such. `count: 0` is a **successful empty
  result**, not an error — see §5.
* Vector/semantic/hybrid search, rerankers, graph APIs — **do not exist** in the Core.
* A machine-competence write route — **does not exist**; `machine.status` stays
  `not_recorded`.
* Distillation approve/reject/revoke over HTTP — **does not exist**.
* **There is no typed loss receipt.** `GET /api/v1/jobs/{job_id}/quality` is a summary
  projection; for an unknown job it answers `404` with the literal body `unknown job`. A UI must
  not parse a two-layer JSON payload out of it or invent `fallback: true`.
* Offline multi-client sync, accounts, or any remote surface — out of scope; the Core is
  an IPv4-loopback single-writer child process.
* **This contract describes the Rust Core, not the Python backend wheel.** The packaged
  `archeaxis_workspace-0.6.14-py3-none-any.whl` is a *different* backend with its **own schema
  baseline** (`python_compatibility`, 97 tables, including `kb_attachment_facts`), which is **not
  the same database** as the Rust vNext Core's `workspace_meta` baseline. A UI must not treat the
  two as one source of truth and must not write both. The wheel also does **not** contain
  `services/python-workers/**`, so "run the full M0 loop from the wheel" is not currently possible;
  the M0 loop is carried by the source-built Core plus workers.
* Nothing here is a migration plan. Migration acceptance is R6 A13 / M0 P5 — a nonempty legacy-copy
  export, a staged import, semantic difference/loss accounting, identity-preserving restart and
  readback, and then the **separate** P6 Owner gate for Green replacement and rollback. A language
  decision, a build, a fixture or a directory move is not evidence that a capability was absorbed,
  and no directory move substitutes for migration.

## 9. Open items this contract does not close

1. ~~**Format routes are not wired into the production binary.**~~ **RESOLVED.** A launch
   now declares its routes, the staged runtime publishes the ones whose workers are present,
   and the Core registers exactly what is declared; a packaging-time readiness check answers
   per route. Measured on real course material: readiness 9 of 9, cases converted 9 of 9.
   See `docs/current/AAOS-BACKEND-LOOP-EVIDENCE-20261001.md` §7.
2. ~~The **open-format JSONL archive** (`archeaxis-archive` `EXPORT_TABLES`) silently omits
   four live data tables.~~ **RESOLVED.** `knowledge_v3_metadata`, `learning_assessments`,
   `card_references` and `machine_tasks` are exported, and `CURRENT_LAYOUTS` accepts both the
   sixteen-table and twenty-table shapes so genuine older archives still restore. The two that
   were created on demand (`card_references`, `machine_tasks`) are now created with the rest of
   the schema, because the export refuses a table it cannot account for and an exported set
   that depends on usage history cannot be identified from a manifest. The online backup path
   was never affected: `--maintenance-backup`/`--maintenance-restore` use the SQLite Online
   Backup API (`crates/archeaxis-domain/src/backup.rs`) and were measured to preserve all four.
   Verified by `crates/archeaxis-archive/tests/omitted_tables_roundtrip.rs`.
3. ~~`GET /sources/{id}/jobs/{job_id}/transform` filters `kind='text'`, so non-text transforms
   are unreadable through the source-scoped route.~~ **RESOLVED.** Every extraction route stores
   its projection in `transforms.text`, so the filter excluded readable content on the basis of
   the job's kind; a PDF transform was answered `404`. Verified by
   `crates/archeaxis-api/tests/source_transform_readback.rs`, which also checks that a job
   without a stored projection is still `404` and that the source binding is still enforced.
4. ~~ASR, video decode and webpage fetch have no sidecar mode and no declared capability.~~
   **ASR RESOLVED**: `media.transcribe` is declared, and a real Chinese recording reaches the
   Core (import → enqueue → execute → `succeeded`, `zh` at 0.9983, covered 2 of 2). Video
   decode and webpage fetch **remain open**, for the reasons the reachability record gives:
   `media/worker_video.py` returns no projected text at all, so it needs an
   artifact-and-measurement contract rather than a parameters field, and
   `web/worker_webpage.py` is a fetch client that no route may point at the network.
5. ~~The **path resolver that A02 specifies does not exist**.~~ **RESOLVED.**
   `services/python-workers/tool_paths.py` resolves engines from the declared capability
   registry, and the workers use it; an engine that is installed and declared is now found
   even when it is not on `PATH`. A manifest that cannot be read is a named failure rather
   than a silent "engine not found". The resource-root schema question itself is still the
   Owner's (`A02` remains `BLOCKED`), which is a decision, not a missing implementation.
   `worker_video.py` now resolves ffmpeg through the declaration as well as `PATH`.
6. ~~`DSH-BACKEND-GAP-MAP-20260927` §2C records the search filter/paging/sort/empty-result
   semantics and the index behaviour after a knowledge revision as still unverified.~~
   **RESOLVED, and two of the four do not exist to verify.** `GET /api/v1/search` takes only
   `q` and `active_only`: there is no `limit`, `offset`, `sort` or `page`, and the result limit
   is a hardcoded 20. `active_only=true` excludes a superseded revision and keeps its successor;
   the unfiltered call still lists the superseded revision with `active: false`. Empty results and
   escaping were already covered. The index cannot go stale across a revision because
   `search::reindex` deletes and rebuilds `knowledge_fts` from the `knowledge` table **before
   every query**; measured after a human correction, the corrected wording is found under the
   successor, the superseded wording is still found under the old revision, and an untouched
   sibling is unaffected.
   Worth recording because it misled this branch: the corrected text goes in **`new_body`**, and
   sending `body` instead is silently ignored, so the successor is created as a clone of the old
   revision and the correction appears to vanish. The request-body table in §4 names every field
   for this reason.
