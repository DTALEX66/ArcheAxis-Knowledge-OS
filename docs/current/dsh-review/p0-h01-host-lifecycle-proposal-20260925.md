# P0-H01 — formal-host Provider lifecycle contract proposal

> **STATUS: PROPOSAL / OWNER DECISION REQUIRED.**
> Read-only design note. **Not** an adopted contract and **not** an implementation authorization.
> No Rust, C#, Python, route, schema, default-Provider or configuration file is changed by this
> document.
>
> - task_id: `DP-NF-02`
> - baseline_sha: `a9ead3e1597808ca751c6ccec1dba27bcfff5b4b`
> - baseline_tree: `ce69abf1493481591534979be1223b1a447fc9bb`
> - branch: `codex/dp-nf-02-20260925`
> - evidence class: `STRUCTURAL / READ-ONLY` (citation-only; no test executed for this note)

## 1. Why this proposal exists — the exact unconnected boundary

The formal host **cannot** currently route a job to a provider other than one hard-wired text
worker. This is not a defect of the provider code; it is an unclosed integration boundary.

| Layer | What exists | What the formal host actually uses |
| --- | --- | --- |
| Rust Core (formal writer) | `Executor::open_routes(db, staging, python, default_worker, extra)` accepting extra `(capability, worker)` routes — `crates/archeaxis-application/src/executor.rs:29-42` | `crates/archeaxis-api/src/main.rs:35-39` calls **`Executor::open`** (the single-route form) with one default worker script and **no extra routes**. Repository-wide, `open_routes` is called **only** by `Executor::open` itself (`executor.rs:22`, with an empty extra list) and by 12 test files — **never** by the shipped binary or the Desktop host |
| Rust routing table | `routes: Vec<(String, PathBuf, bool)>` seeded with exactly one entry: `("text.extract", default_worker, false)` — `executor.rs:36` | `worker_for(capability)` returns `None` for everything else and dispatch fails explicitly with `no worker registered for capability <c>` — `executor.rs:45-46, 77-80` |
| Python capability/plugin layer | `CapabilityStore` with stage → activate → disable → enable → quarantine and pack content-hash verification — `app/capability/store.py:115-400`; HTTP surface — `app/capability/router.py:37-100`; builtin converter plugins — `app/capability/builtin/*`; dispatcher — `app/capability/conversion.py:202` | Only the **legacy FastAPI** `app/*` surface. `app/workspace/service.py:158-160` consults the store on intake |
| Provider-routing sidecar contract | `shared/provider_routing.py` (`SCHEMA_VERSION = "archeaxis.provider-routing/v1"`) | **Referenced by no Rust file and no C# file.** Grep across `crates/**/*.rs` finds no `provider_routing` / `provider-routing` token; the only C# hits are user-facing strings, one of which is explicitly honest: `apps/ArcheAxis.Desktop/MainWindow.axaml.cs:2827` — "插件、模型、Sidecar 未接入权威 readiness 投影" |
| Handshake capability matching | Protocol-level: a worker must advertise the requested capability — `crates/archeaxis-application/src/executor.rs:244-256`, `crates/archeaxis-sidecar-protocol/src/worker.rs:103-114` | Used for the one route that exists; it is not a provider registry |

**Therefore:** the Python `provider_routing` snapshot parser is a **contract-only** component. It
must not be described as integrated into the formal host, and no UI may be enabled on the strength
of its existence. R6 records P0-H01 as `BLOCKED_BY_AUTHORITY_DECISION`, and the baseline
`docs/current/M0-DIRECTION-OVERRIDE-20260920.md` keeps it there.

## 2. What the owner is being asked to freeze

One authoritative lifecycle for providers on the formal host, covering: authoritative publisher,
generation/manifest identity, installed/enabled state, health receipt, default/fallback selection,
atomic publication and crash recovery, replacement/disable, startup readback, permission boundary,
migration compatibility, and acceptance tests.

## 3. Verified constraints any answer must respect

- **C1 — single canonical writer.** The Rust Core is the sole canonical writer
  (`AGENTS.md` §6; R6 A12 contract `archeaxis-core-rust-sqlite`). A provider registry may not become
  a second source of durable product truth.
- **C2 — the host has no registry today.** Only `text.extract` is routable
  (`executor.rs:36`). Any additional capability needs an explicit route to exist at all.
- **C3 — no provider state file is read by the host.** The `provider-routing/v1` sidecar has no
  Rust or C# reader. A sidecar cannot be assumed to be authoritative merely because a parser exists.
- **C4 — the Desktop already states the gap honestly.** The UI text at
  `MainWindow.axaml.cs:2827` must not be replaced by invented readiness before the contract exists.
- **C5 — capability matching is per-job, not per-provider.** The handshake deliberately refuses to
  pin one capability: `crates/archeaxis-sidecar-protocol/src/worker.rs:103-107` states that the
  handshake "validates the protocol shape, the worker identity and a unique, non-empty
  capability/schema set; whether the worker advertises the capability a *particular job* needs is
  checked where that request is known (the executor), never by pinning one capability here".
  Provider selection must not be smuggled into the handshake.
- **C7 — multi-route plumbing is test-only today.** `open_routes` is invoked by the shipped binary
  nowhere; only `Executor::open` (empty extra list, `executor.rs:22`) and 12 test files use it. So
  the *mechanism* for extra routes exists and is exercised, but the *host* never supplies one.
- **C6 — R6 A02 is unresolved.** External resource roots (including the shared model library) are
  `BLOCKED_BY_OWNER_DECISION`; a provider lifecycle that resolves model paths would prejudge A02.

## 4. Proposed contract (for owner review — nothing implemented)

### 4.1 Authoritative publisher

Exactly one writer for provider state. The proposal is that this be the **Rust Core**, exposing an
append-only, hash-chained publication record, with the Desktop strictly read-only. Any alternative
(a Core-owned sidecar written by a separate tool) requires an explicit owner statement that it does
not create a second source of truth. Decision **D1**.

### 4.2 Identity and generation

- `provider_id` — stable, non-empty, delimiter-safe (the Rust route validator already constrains the
  capability charset: `worker.rs:85-87`).
- `provider_version` — immutable per published artifact.
- `generation` — monotonic integer, incremented on every publication; the only ordering authority.
- `manifest_sha256` — content hash of the exact manifest bytes.
- A publication is identified by `(provider_id, provider_version, generation, manifest_sha256)`.
- **Identity normalisation must be rejected, not silently trimmed** (whitespace/case handling must
  be one rule, fail-closed). The R6 P0-H01 identity-hardening regression already requires this.
  Decision **D2**.

### 4.3 Installed / enabled state

Modelled as **two independent facts**, never one enum:

| Fact | Meaning | Who may change it |
| --- | --- | --- |
| `installed` | artifact bytes are present and hash-verified | publisher |
| `enabled` | the host may route to it | owner/integration step, read by the host |

A provider that is installed but not enabled must never be dispatched to. A provider that is
enabled but not installed is a hard configuration error, not a fallback candidate.

### 4.4 Health receipt

- An explicit, dated, content-hashed record: `provider_id`, `generation`, `checked_at`,
  `outcome ∈ {healthy, unhealthy, unknown, not_run}`, `evidence_ref`.
- **`not_run` and `unknown` must exist** and must be distinguishable from `unhealthy`; absence of a
  health receipt must never read as healthy. This mirrors the R6 rule that unmeasured is not a pass.
- Health may inform selection; it may never be presented as a quality/accuracy figure.

### 4.5 Default and fallback

- At most one default provider per capability, declared, not inferred from directory order.
- Fallback is an **ordered, explicit list**; an empty list means "no fallback", not "any".
- Fallback must be attempted only for declared, enumerable failure classes; a fallback that
  silently changes the extraction contract is worse than a failed job.
- A job's receipt must record which provider actually ran and whether a fallback occurred, so
  provenance is never lost.
- Until this is frozen, **keep failure explicit** (the existing behaviour: no registered route →
  explicit error, `executor.rs:77-80`). Decision **D3**.

### 4.6 Atomic publication and crash recovery

- Publish by write-to-temp + fsync + atomic rename, then a single commit record that carries the new
  `generation`; readers must never observe a partially written generation.
- Crash between artifact write and commit record ⇒ the generation does not exist; recovery must
  garbage-collect the orphan temp by hash, never "repair" a half state into an enabled provider.
- Startup readback must be verifiable: after restart, the host must be able to state, for every
  capability, the active `(provider_id, generation, manifest_sha256)` it will route to.
- Decision **D4** (does publication need to be transactional with respect to any Core table, or is a
  hash-chained file record sufficient?).

### 4.7 Replace / disable

- Disable is a state transition, never a delete; the artifact stays for rollback.
- Replace = publish a higher generation, then switch; the previous generation must remain
  addressable by generation for rollback.
- A disable of the last provider for a capability must degrade that capability to explicit
  "unavailable", not to a silent default from another capability.

### 4.8 Permissions

- Only the owner/integration path may enable or replace a provider; a running job may not.
- The Desktop may read provider readiness but may not write provider state.
- No provider metadata may embed absolute private paths in a projection returned to the UI.

### 4.9 Migration compatibility

- The contract must be additive: no change to `SCHEMA_VERSION` (`= 6`,
  `crates/archeaxis-store-sqlite/src/lib.rs:8`) is required for the read-only parts.
- Existing single-route behaviour (`text.extract`) must remain the default if no provider record
  exists, so an empty registry cannot break the current text path.
- Historical `provider-routing/v1` documents, if ever adopted, must be read via a versioned parser
  with an explicit unsupported-version error — never silently upgraded.

### 4.10 Acceptance tests (to be added only after the contract is frozen)

1. Empty registry ⇒ `text.extract` still works; everything else fails explicitly.
2. Installed-but-not-enabled provider is never dispatched to.
3. Enabled-but-not-installed is a hard error with no fallback substitution.
4. Generation ordering: a lower generation can never win.
5. Crash injection between artifact write and commit ⇒ no enabled provider, no half state.
6. Restart readback returns the exact active generation for every capability.
7. Disable → capability unavailable; re-publish → routes again.
8. Health `not_run` / `unknown` never counted as healthy.
9. Fallback attempt is recorded in the job receipt.
10. Identity normalisation: whitespace/case variants are rejected, not merged.

## 5. Owner decisions requested

| ID | Decision |
| --- | --- |
| **D1** | Is the Rust Core the sole authoritative publisher of provider records (Desktop read-only)? |
| **D2** | Confirm the identity tuple and the fail-closed normalisation rule. |
| **D3** | Is explicit failure the required interim behaviour until default/fallback is frozen? |
| **D4** | Atomic publication: hash-chained file record, or transactional with a Core table? |
| **D5** | Does provider/model path resolution fall under the unresolved A02 resource-root decision (i.e. must this wait for A02)? |
| **D6** | Which provider classes (converter plugins, ASR/OCR engines, local model providers) are in scope for the first freeze, given M0 keeps one domain/renderer and no second provider? |

## 6. Explicit non-claims

1. This note does **not** claim the formal host integrates provider routing — it claims the opposite
   and cites the exact lines.
2. It does **not** describe `shared/provider_routing.py` as integrated; that module is contract-only
   and unread by Rust/C#.
3. It does **not** authorize enabling Plugin/Model UI, adding a provider, or changing defaults.
4. It does **not** change P0-H01 status: it remains `BLOCKED_BY_AUTHORITY_DECISION`.
5. It does **not** resolve A02; D5 asks whether the two are coupled.
6. No test was executed for this note. Every claim is a file/line read of the baseline; the
   acceptance tests in §4.10 are proposals, not evidence.
