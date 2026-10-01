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

## 1. Process model and launch handshake

The Core is a child process owned by the desktop Supervisor. It is **not** a service the
UI may start, restart or connect to on its own terms.

```
archeaxis-api <workspace-db-path> [port]
```

* `port` defaults to argv, then env `ARCHAXIS_VNEXT_PORT`, then `47831`. `0` asks the OS
  for a loopback port — the real desktop passes `0` and reads the chosen port from stdout.
* Binding is **IPv4 loopback only**. There is no remote or LAN surface.
* Before binding, the parent must write **one** JSON line to the Core's stdin (≤4096 bytes)
  and close it within 5 s, or the Core exits `2`.
* On success the Core writes one line to stdout:
  `archeaxis-api ready on http://127.0.0.1:<port>`.

Exit codes: `2` = usage / launch-input / launch-identity failure; `1` = workspace open,
executor init, identity protect, or bind failure.

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

* Every request to every route must carry **exactly one** `x-archeaxis-launch-token`
  header. Duplicate headers are rejected.
* The value is compared (constant time) against `launch_token` **or** `machine_token`.
  No match → `401 `AAK-AUTH-001``.
* **The actor is derived server-side from which token matched.** Matching `machine_token`
  makes the request a machine request; otherwise it is human.
* The Core **overwrites** `x-archeaxis-actor` before dispatch, so a client cannot escalate
  by sending that header. Wire-supplied `x-archeaxis-actor` / `x-archeaxis-scopes` are
  ignored in production.
* Any request carrying an `origin` header → `403 `AAK-AUTH-002` browser origin not allowed`.
  The formal desktop is a native client; a browser is deliberately not a valid client.
* There is **no** `x-archeaxis-machine-token` header in this protocol.

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

## 3. Route inventory (30 pairs in a `text_worker` launch)

`PROD` = reachable in a production launch. `PROD` marks the routes the UI may rely on.
All paths are relative to the loopback base URL.

### Session and workspace

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 1 | `GET /api/v1/system/version` | any token | Session/identity readback. See §2. |
| 26 | `GET /api/v1/workspaces/info` | any token | Workspace projection. |

### Source intake and conversion

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 2 | `POST /api/v1/imports` | any token | Body `{name, content_base64}`. `202` + `source_id` is **acceptance, not conversion**. |
| 3 | `POST /api/v1/jobs` | any token | Body `{job_id, kind, input_ref}`. `kind` selects the route (§6). |
| R2 | `POST /api/v1/jobs/{job_id}/executions` | any token | Requires header `idempotency-key`. Body `{deadline_ms}` (1..300000). `202` follows a durable claim, not completion. |
| R1 | `GET /api/v1/jobs/{job_id}` | any token | `{job_id, state, attempt, request_id, error}`. `state` ∈ `queued`/`running`/`succeeded`/`failed`/`cancelled`. |
| R3 | `POST /api/v1/jobs/{job_id}/executions/{request_id}/cancel` | any token | Requesting a cancel is not the same as observing `cancelled`; re-read the job. |
| R4 | `GET /api/v1/jobs/{job_id}/outputs/{kind}` | any token | Persisted job output. |
| 22 | `GET /api/v1/jobs/{job_id}/quality` | any token | Aggregate projection; not a typed loss receipt. |
| 5 | `GET /api/v1/sources/{source_id}/jobs/{job_id}/transform` | any token | **Filters `kind='text'`** — a non-text transform is not readable here even when the job succeeded. |
| 24 | `GET /api/v1/sources/{source_id}/members` | any token | Source members. |
| 25 | `GET /api/v1/sources/{source_id}/jobs` | any token | Jobs for a source. |

### Evidence and knowledge

| # | Method + path | Auth | Notes |
| --- | --- | --- | --- |
| 4 | `POST /api/v1/sources/{source_id}/anchors` | any token | Anchor creation. |
| 23 | `GET /api/v1/evidence/anchors` | any token | Anchor listing. Not a complete cross-domain evidence service. |
| 6 | `POST /api/v1/knowledge-items/from-transform` | any token | Body carries `source_id`, `job_id`, `transform_id`, UTF-16 selection range and `quote`. Core validates the **persisted** transform and selection. Returns a **candidate** + anchor. |
| 7 | `POST /api/v1/knowledge-items` | any token | Direct candidate creation. |
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
| 12 | `POST /api/v1/learning/reviews` | **human only** | Body `{item_key, client_event_id, exposure_id?, assessment_id, knowledge_version, answer, correct, rating, now?}`. `client_event_id` is the idempotency identity — retry replays the original receipt. Machine → `403`. Never falls back to the placeholder ladder. |
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
  competence ledger.
* `learner.recording` is a fixed explanatory string.
* Fixed `note` literals are appended to real data on machine readback, job quality and
  source members.
* `mastery_projection.closed` is a **constant `false`** — mastery is deliberately an open
  projection, never a closed claim. `correct_streak` is re-derived on every read.
* `POST /learning/events` without `schedule_state` reports
  `schedule_authority:"placeholder_ladder"` and `next_review:null`. That is the 1/2/4/7/14
  stub, **not** FSRS. Distinguish it from `"fsrs"` and from `"unavailable"`.
* When no `knowledge_v3_metadata` row exists, the V3 projection invents
  `confidence:null`, `risk_level:"low"` and a `support_level`.

## 5. Idempotency, conflicts and errors

Error body shape for auth failures: `{"code","message","retryable"}`.

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

## 6. Launch shape decides the router — the critical integration fact

| Launch | Routes served | Consequence for the UI |
| --- | --- | --- |
| **no** `text_worker` | 26 projection routes only | `/jobs/{id}`, `/executions`, `/outputs`, `/cancel` are **absent** (`404`). |
| **with** `text_worker` | 30 routes (projection + the 4 runtime routes) | All routes above are served. |

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
cannot succeed. Format routes that require an absent local engine (caption/VL) and formats
with no route at all (ASR transcription, video decode, webpage fetch) must be reported
`unavailable` rather than `error`.

## 7. Evidence

| Claim | Command | Result |
| --- | --- | --- |
| Route inventory and auth model | source read of `crates/archeaxis-api/src/{main.rs,lib.rs,launch.rs,runtime/mod.rs}` | matches table above |
| Continuous M0 loop through the real Core | `python -B scripts/probes/m0_full_loop_smoke.py` | **27/27 stages ran**; `answer_recorded.schedule_authority = "fsrs"`; restart readback identical; online backup `exit_code 0`; restore `verified true` with `counts_after == counts_before`; `evidence_level: SYNTHETIC`; sole validation error `legacy migration not verified` |
| Format reachability in a production launch | `python -B scripts/probes/production_format_coverage_smoke.py` | `verdict_counts: {REACHABLE: 1, FAILED_AT_ROUTE: 9}`; worker advertises `['text.extract']` |
| Format reachability, independently reproduced | a separate direct launch of the same Core, `kind=pdf` vs `kind=text` control | PDF settles `failed` with the same error and its `job_attempts` row shows `capability=pdf.extract` never terminated; the `text` control `succeeded` |
| Same measurement on **real user material** | `python -B scripts/probes/real_material_conversion_smoke.py` | `{CONVERTED: 1, FAILED_AT_ROUTE: 5}` against a real Obsidian knowledge base (3,095 real `.md`, 66 `.pdf`, 24 `.docx`, 22 `.canvas`); the success is a real Chinese course note |
| Engines present and working with declared paths | `worker_transcribe.py --probe`/transcribe, `worker_ocr.py` | real ASR of a real 5.8 MB Chinese MP3 → 3,362 chars / 295 segments; real OCR of a Chinese image → `三命通会` read correctly, `covered 3/3` |
| Rust API suite | `cargo test -p archeaxis-api --no-fail-fast` with `ARCHEAXIS_PYTHON` set | all 28 targets pass |
| Rust application (per-format) suite | `cargo test -p archeaxis-application --no-fail-fast` | all targets pass |

Evidence level for this document: **REAL** for the route inventory, authentication model
and format-reachability measurements (real binary, real HTTP, real verified fixture bytes);
**SYNTHETIC** for the M0 loop receipt, which the probe itself labels as such because the
source, the human actions and the model failure are fixtures.

## 8. Explicitly out of contract

* Legacy copy migration, in-place Green replacement, release/tagging — **paused by the
  Owner**. Not available through this API and not to be assumed by the UI.
* Vector/semantic/hybrid search, rerankers, graph APIs — **do not exist** in the Core.
* A machine-competence write route — **does not exist**; `machine.status` stays
  `not_recorded`.
* Distillation approve/reject/revoke over HTTP — **does not exist**.
* Offline multi-client sync, accounts, or any remote surface — out of scope; the Core is
  an IPv4-loopback single-writer child process.

## 9. Open items this contract does not close

1. **Format routes are not wired into the production binary.** This is the single largest
   gap between "the loop exists in tests" and "the product can convert a real PDF". It
   needs a route-enablement mechanism (the worker profile naming its routes, or the Core
   registering routes for every capability the configured worker advertises) plus a
   regression test that launches the production shape and converts one real fixture per
   format.
2. The **open-format JSONL archive** (`archeaxis-archive` `EXPORT_TABLES`) silently omits
   four live data tables — `machine_tasks`, `learning_assessments`, `card_references` and
   `knowledge_v3_metadata` — so an archive/restore round trip loses human-learning,
   machine-receipt and V3-governance rows. This is **not** the online backup path:
   `--maintenance-backup`/`--maintenance-restore` use the SQLite Online Backup API
   (`crates/archeaxis-domain/src/backup.rs`) and were measured to preserve all four tables.
   The archive path is not reachable from the CLI or from any HTTP route today; it is
   exercised only by Rust tests.
3. `GET /sources/{id}/jobs/{job_id}/transform` filters `kind='text'`, so non-text
   transforms are unreadable through the source-scoped route.
4. ASR, video decode and webpage fetch have no sidecar mode and no declared capability.
5. The **path resolver that A02 specifies does not exist**: workers guess with
   `shutil.which` or derive relative paths instead of reading the declared resource
   registry, so real engines that are installed, registered and working stay unreachable.
   `worker_video.py` accepts no engine override at all. This is independent of the route
   gap and of the resource-root schema question.
