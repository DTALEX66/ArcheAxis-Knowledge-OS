# Protocol channel mapping and vocabulary freeze (Contract v1)

Canonical companion to `compatibility-policy.md`. Every runtime surface
(HTTP API, worker NDJSON, MCP) speaks one business vocabulary; only the
transport envelope differs.

## Channel envelope mapping

| Concept | HTTP | Worker NDJSON | MCP |
|---|---|---|---|
| Request identity | `x-archeaxis-request-id` | `request_id` | `requestId` |
| Write idempotency | `idempotency-key` header (1..200 chars, per scope) | `job_id` + `attempt` (retry of same attempt is idempotent) | `idempotencyKey` |
| Version | `/api/v1` + contract minor negotiation | `protocol_major/min_minor/max_minor` hello | `protocolVersion` |
| Success | 2xx + body | `status:"succeeded"` envelope | `result` |
| Failure | error catalog code + HTTP status | `status:"failed"` + `error{code,message,retryable}` | `error{code,message}` |
| Invalid request | 4xx (AAK-VAL/AAK-PROTO) | `status:"rejected"` + `retryable:false` | `rejected` |
| Auth/scope | launch token + scope header | worker never authenticates Core; identity via stdin env | session token + budget |

## Status vocabulary (single source)

- Job lifecycle: `job-status.schema.json` — `queued|running|succeeded|failed|rejected|cancelled`.
- Worker response status maps: `succeeded`→`succeeded`; `rejected`→`rejected` (never retryable);
  `failed`→`failed` (retryable only when `error.retryable`).
- Research verdicts: `PASS|PARTIAL|FAIL|UNMEASURED|BLOCKED_CREDENTIALS` — search outage, network
  loss or budget exhaustion yield `PARTIAL`; never a fake `PASS`; a missing original source forbids
  fabricated citations (coverage receipt `stop` records why).
- Machine competence display: only probed capabilities report `MEASURED`; everything else
  `UNMEASURED`/`NOT_TESTED`.
- Review/evidence/knowledge states: `assessment-vocabulary.schema.json` (closed enums; machines
  cannot write `USER_ACCEPTED`).

## Anchor rules

Coordinates use `anchor-coordinate.schema.json`. Bounds are strict (non-negative page/char/time
values, `end >= start`, block paths non-empty). A selector that does not match the exact source
revision bytes is rejected (`AAK-ANCHOR-001`); source revision changes invalidate anchors
(`AAK-ANCHOR-002`) until re-resolution.

## Idempotency

Every write carries a bounded key scoped to the caller+operation. Replay with the same key returns
the original result and never double-applies; the same key with a different payload is rejected
(`AAK-CON-002`). Worker retries keep `job_id`+`attempt`; a second completion for an attempt already
recorded is ignored (no duplicate `completed`).

## Error objects

All channels carry `{code, message, retryable}` (HTTP additionally maps code→status via
`errors.catalog.yaml`). Unknown worker statuses/fields and unknown schema versions are rejected;
a future major version is refused with `AAK-PROTO-001` (compatibility-policy.md major rule).

## Representation

Enums serialize as strings, never ordinals. Generated Rust/C#/Python bindings come from these
schemas only; regeneration must leave the Git tree clean (drift check in `tests/contract` and
`crates/archeaxis-contracts`).
