# Workspace BFF v1 Contract

Status: **BE01 implementation candidate — read-only contract**  
Owner: Cognitive-OS workspace boundary  
Scope: local loopback product shell only

## 1. Boundary

The v1 BFF is a server-owned projection boundary for the product shell. It is not a
second persistence API and it is not an authorization credential.

- Base path: `/workspace/api/v1`
- Transport: same-origin loopback HTTP only
- Methods in this contract: `GET` only
- No API key, JWT, approval reason, retry command, cancellation command, or manual
  action is required by the local product shell
- Existing `/workspace/api/*` endpoints remain a compatibility surface and are not
  part of this contract. UI migration must not silently mix the two surfaces.

## 2. Privacy and identity rules

Responses MUST NOT contain `command_id`, `job_id`, `package_id`, `artifact_id`,
`unit_id`, database paths, backup paths, SQL/table names, credentials, or raw
persistence payloads.

Object identity is represented by `public_ref`:

- format: `wr1_` plus 32 lowercase hexadecimal characters;
- stable for the same object key and contract version;
- does not encode a persistence identifier;
- is not an authorization token; loopback and same-origin checks remain mandatory;
- an unknown or malformed reference returns the same 404 object-not-found shape.

## 3. DTOs

### `GET /workspace/api/v1/home`

```json
{
  "schema_version": "v1",
  "observed_at": "2026-08-01T00:00:00Z",
  "release": { "version": "0.4.1", "status": "..." },
  "components": { "api": "available", "database": "available" },
  "counts": {},
  "capabilities": {},
  "recent_activity": [Activity]
}
```

The existing truthful aggregate status is reused; no fabricated progress or ETA is
allowed. If its projection cannot be read, the endpoint returns HTTP 503 with
`{"detail":"workspace projection is unavailable"}`.

### `GET /workspace/api/v1/activity`

Parameters:

- `limit`: integer `1..50`, default `20`;
- `cursor`: opaque cursor returned by the previous page.

```json
{
  "schema_version": "v1",
  "items": [Activity],
  "next_cursor": "..."
}
```

`items` are stably ordered by `updated_at` descending, then `public_ref`
descending. Invalid cursors return HTTP 422. There is no offset pagination.

`Activity`:

```json
{
  "public_ref": "wr1_...",
  "kind": "job|source",
  "label": "资料导入|研究资料",
  "state": "candidate|queued|succeeded|...",
  "updated_at": "2026-08-01T00:00:00Z"
}
```

### `GET /workspace/api/v1/objects/{public_ref}`

Supported kinds in this first slice are `job` and `source`. A successful object
response contains only the corresponding public DTO. Unknown, expired, malformed,
or unsupported references return HTTP 404; the response must not reveal which
lookup failed.

## 4. Failure semantics

| Condition | HTTP | Meaning |
|---|---:|---|
| malformed limit/cursor | 422 | caller input invalid |
| object is unknown | 404 | no object is revealed |
| projection table/data unavailable | 503 | retry/readiness issue, no partial fake data |
| non-loopback, cross-site, or wrong-origin request | 403 | local boundary rejected |

## 5. Action boundary

The v1 BFF has no write routes. Approval, retry, delivery, learning, practice,
Runtime promotion, intake, and cancellation remain outside BE01 and must not be
triggered by a GET or hidden browser-side side effect.

## 6. Acceptance gates

- API route inventory shows only GET operations under `/workspace/api/v1`.
- Integration tests prove public-ref mapping, cursor pagination, 404/503 behavior,
  and absence of internal identifiers.
- `git diff --check`, Ruff, and targeted pytest pass.
- A later UI01 task may consume this contract only after deep-link and route
  migration tests are added in its own branch/PR.
