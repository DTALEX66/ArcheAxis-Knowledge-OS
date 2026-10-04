# AAOS backend → UI branch handoff summary — 2026-10-01

This is the one-page version of the backend loop's result, written for the UI branch
(`codex/aaos-ui-phase2-20261001`). The detail lives in the four documents below; this page says
what changed, what the UI must rely on, and what is still blocked.

## Where this lives

| Artifact | Purpose |
| --- | --- |
| `AAOS-PRODUCTION-HTTP-CONTRACT-20261001.md` | the route/behaviour contract the UI binds to |
| `AAOS-BACKEND-ACCEPTANCE-RUNBOOK-20261001.md` | how to reproduce every claim, one command per side |
| `AAOS-BACKEND-LOOP-EVIDENCE-20261001.md` | the P0–P6 measurements |
| `AAOS-BACKEND-KEY-DISPOSITION-20261001.json` | per-key status and evidence level for the 58 owned keys |

Branch `codex/dsh-aaos-real-multiformat-loop-20261001`, based on `1a981a44` — the **same base as the
UI branch**, so there is no rebase relationship between them; they diverged. Delivery is PR
[#157](https://github.com/DTALEX66/ArcheAxis-Knowledge-OS/pull/157) against `codex/Audit`.

**Do not read these documents as claims about the UI branch.** A shared base commit is not a shared
worktree, and neither branch contains the other's work.

## The five things the UI must not get wrong

Each was measured against a live Core on this branch, and each is checked by a test in
`crates/archeaxis-api/tests/` or `tests/maintenance/`.

1. **`schedule_authority` has three values, and a review can only produce two of them.**
   `POST /learning/reviews` answers `fsrs` when the launch's interpreter can schedule, and
   `unavailable` (with `next_review: null`, `next_review_days: -2`) when it cannot.
   `placeholder_ladder` belongs **only** to `POST /learning/events` with no `schedule_state`.
   Rendering `unavailable` as scheduled is a claim the Core explicitly declined to make.
2. **Error bodies are not uniform JSON.** The auth middleware and the two job routes answer JSON;
   `/jobs/{id}/quality`, `/sources/{id}/members`, `/knowledge-items/{id}/v3`, `/machine/tasks/{id}`
   and validation failures answer **plain text**. A client that parses JSON unconditionally fails
   there. `AAK-VAL-004` covers both "no such job" and "no such output", so the message distinguishes
   them.
3. **Request bodies silently ignore unknown fields.** `POST /knowledge-items` takes `status`, not
   `review_state`; a modified review takes **`new_body`**, not `body`. Sending the wrong name
   succeeds while doing something else — a successor revision comes out as a clone of the old one.
   The contract lists every field for all thirteen routes.
4. **`GET /search` takes only `q` and `active_only`.** There is no `limit`, `offset`, `sort` or
   `page`, and the result limit is a hardcoded **20**, so paging has to be client-side. `count: 0`
   is a successful empty result. A review is roughly **6× a projection read** and holds the single
   writer while it waits for the scheduler, so keep review submissions off the render thread.
5. **Some route families do not exist and must be shown as "not connected".** `/research*`,
   `/plugins*`, `/models*`, `/embeddings/search`, `/graph/search` all answer `404` — to their own
   method *and* to a wrong one, which is what proves they are unmounted rather than empty.

## Corrections this branch made to its own earlier claims

Recorded because a reader may have seen the earlier version. Full table in
`AAOS-ERRORS-BLOCKERS-20261001.md`. None of these were product code defects; they were this
document's statements failing against the product, plus two defects in the branch's own working
method.

| Earlier claim | Measured fact |
| --- | --- |
| a review with no card state reports `placeholder_ladder` | it reports `unavailable`; the ladder is the events route |
| error bodies are the JSON `{code,message,retryable}` shape | only auth and the job routes are JSON |
| — | the absent route families had no list at all |
| the M0 chain's sole validation error was `legacy migration not verified` | this host runs it with `validation_errors: []`, 27 of 27 stages |
| search filtering/paging/sorting was unverified | paging and sorting **do not exist**; the index cannot go stale |
| — | the review route's writer-blocking cost was not recorded |
| — | the contract had no consumer boundary at all |
| `CARGO_TARGET_DIR=...cargo-gnu` used without stating why | it is a supported override, now verified through the official entry point |

## What is still blocked, and by whom

| Item | State | Owner |
| --- | --- | --- |
| Legacy data migration, in-place Green replacement, release/tag | `NOT_EXECUTED` | frozen boundary |
| `A02` resource-root schema, `A16`, `P0-H01` provider identity, `DP-F01` typed loss receipt, Research DTO freeze | `BLOCKED` | Owner decision |
| `image.caption` | `BLOCKED` | needs a local Ollama vision endpoint |
| video decode, webpage fetch | `BLOCKED` | need an artifact-and-measurement contract |
| `faster-whisper-large-v3-turbo` undeclared; `sherpa-onnx` declared with a root-escaping path | open | Owner decision |

## Verification state of this handoff

Rust workspace **100 of 100 targets** pass; Python **3679 pass, 0 failed**; `cargo fmt --check`
clean. Every claim above names the test that checks it, and the runbook gives the commands. Two CI
runs in this window had `test (3.12)` **cancelled** in the "Install and verify local OCR engine"
step (not failed); both succeeded on re-run at the same exact SHA. A cancelled job is not a pass,
which is why the re-run is what is reported.
