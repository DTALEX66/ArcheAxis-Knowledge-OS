# Container Delivery Handoff

## Delivery scope

This handoff covers the production-oriented, single-host container delivery for
Cognitive-Loop-OS. The container branch includes the Phase 4 persisted Research
candidate pipeline and keeps its fail-closed Phase 5 review boundary intact.

The supported deployment is deliberately narrow:

- one Linux Docker host;
- one installed-wheel Core process;
- Knowledge Base mounted at `/kb`;
- Research mounted internally at `/internal/research`;
- one durable SQLite writer and one named data volume;
- Caddy as the only public entry point;
- no Kubernetes, multi-host deployment, Redis, Postgres, or worker scaling.

## Authoritative files

| Concern | File |
| --- | --- |
| Application image | `Dockerfile` |
| Production stack | `docker-compose.yml` |
| CI overrides | `docker-compose.ci.yml` |
| Container commands | `app/container_entrypoint.py` |
| Caddy runtime | `docker/Caddy.Dockerfile`, `docker/Caddyfile` |
| Operator runbook | `docs/CONTAINER_DEPLOYMENT.md` |
| Container CI | `.github/workflows/container.yml` |
| Static/dynamic contracts | `tests/test_container_stack_contract.py` |
| Runtime dependency lock | `uv.lock` |

Do not restore the retired `docker/Dockerfile` or the standalone Research
service. Both would create drifting build or writer paths.

## Service topology

```text
Internet
  -> Caddy (only published ports; fixed proxy identity)
     -> Core :8000
        -> /kb
        -> /internal/research
        -> named SQLite volume

one-shot/ops jobs on the same application image:
  migration
  integrity
  backup
  restore-candidate
  restore-activate
```

Caddy blocks `/internal/*` from the public path. Research is reachable only
inside the governed Core application and remains subject to the Phase 4
candidate-only promotion boundary.

## Migration ownership

`migration` is the only container schema owner. It creates only the empty SQLite
file, then invokes `MigrationOperator` in deterministic registry order for every
owner whose kind starts with `sqlite`:

- `core.sqlite`, owning both baseline DDL groups and their normalized schema contract;
- `taskpack.sqlite`;
- `research.sqlite`.

Vector and FTS owners are not startup schema owners; they require an existing
active index and remain explicit operator actions. Core startup performs only
read-only canonical schema and current operator-provenance validation and fails
before Uvicorn if migration is incomplete or any named table has drifted columns,
constraints, or indexes.

Migration, restore activation, and the long-lived Core process use the same
target-scoped runtime lease. The published `cognitive-os serve`, PM2, Windows,
and POSIX launchers all delegate to `app.container_entrypoint core`; effectful
`cognitive-os pipeline` and `cognitive-os migrate apply/rollback` hold the same
explicit target lease for their full operation. Restore activation must run with
Core and Caddy stopped and holds that lease continuously across verification,
replacement, post-restore validation, and compensation.

## Configuration and secrets

1. Copy `.env.container.example` to the untracked `.env.container`.
2. Generate different high-entropy values for `COGNITIVE_API_KEY` and
   `COGNITIVE_JWT_SECRET`.
3. Set the public domain, TLS email, CORS origins, methods, and headers.
4. Never commit `.env.container`, runtime databases, backups, manifests, WAL/SHM
   files, image archives, or registry credentials.

The example file intentionally contains no usable secret. Compose fails closed
when required values are absent.

## Start and health

Use the exact commands in `docs/CONTAINER_DEPLOYMENT.md`. The normal sequence is:

```bash
docker compose --env-file .env.container build
docker compose --env-file .env.container up -d migration core caddy
docker compose --env-file .env.container ps
```

Acceptance requires more than `/health`:

- migration job completed successfully;
- Core and Caddy run as their configured non-root numeric users;
- only Caddy publishes host ports;
- public `/internal/research/*` is unavailable;
- authenticated in-container Research health succeeds;
- the named SQLite volume survives a Core restart;
- backup manifest validation and offline restore activation succeed.

## Authorization and proxy boundary

Authorization is effect-aware. A `readonly` role is not a synonym for every GET
route, and ordinary users cannot invoke backup, restore, migration, runtime
execution, sleep-loop control, host-file ingestion/conversion, token issuance,
or internal Research operations.

Caddy overwrites forwarded identity headers. Core trusts only Caddy's fixed
`172.28.0.2/32` address, not the full Compose subnet. Do not change this to a
broad CIDR without repeating the direct-to-Core spoof and rate-limit negative
controls.

## Backup and restore

- `integrity` verifies the live database before backup.
- `backup` uses SQLite's backup API and emits a manifest bound to source identity,
  SHA-256, migration state, volume identity, and required domain invariants.
- `restore-candidate` verifies and stages an exact backup without activating it.
- `restore-activate` is offline-only and retains a verified compensation copy
  until the restored live database passes post-replacement validation.

Never copy a raw SQLite file over the live path and never activate a candidate
while Core is running.

## CI and publication

Pull requests run two container jobs:

1. `quality`: Root, KB, Integration, Ruff, architecture, conventions, and lock
   validation.
2. `smoke`: deterministic image builds, final-image vulnerability gates,
   Compose validation, real stack startup, RBAC/network checks, non-root checks,
   volume persistence, backup, mutation, offline restore, restart, and teardown.

GHCR publication is a separate job restricted to a push on `main` and depends on
both `quality` and `smoke`. It publishes immutable `sha-<commit>` plus `latest`
only after the rebuilt image ID matches the smoke-tested image ID. A pull request
must not publish an image.

## Upgrade and rollback

Before an upgrade:

1. run integrity;
2. create and retain a verified backup;
3. retain the previous immutable GHCR SHA tag;
4. stop Caddy and Core;
5. build/pull the new image;
6. run migration;
7. start Core and Caddy;
8. repeat health, authorization, persistence, and backup checks.

Code rollback uses the previous immutable image tag. Data rollback uses only the
verified offline restore flow.

## Known boundaries

- Local Windows verification cannot claim a Docker build or Compose runtime when
  Docker is unavailable. The required real Linux container evidence comes from
  the PR `Container Stack` workflow.
- SQLite remains single-host and single-writer. Do not scale `core` above one
  replica without a new storage, lease, and rate-limit review.
- PR validation does not publish GHCR images; publication occurs only after merge
  and a successful `main` workflow.
- Phase 5 server-owned Research review provenance is not implemented here;
  candidate references continue to fail closed at downstream write boundaries.

## Handoff completion criteria

The container delivery is ready to hand over only when all of the following are
true for the uploaded branch:

- the staged tree has no conflicts, unstaged files, or untracked runtime data;
- full local non-Docker gates pass;
- an independent exact-tree security review returns GO;
- the branch is pushed and the PR is mergeable;
- standard CI and `Container Stack` quality/smoke jobs are GREEN;
- the PR description links this handoff and the operator deployment runbook.
