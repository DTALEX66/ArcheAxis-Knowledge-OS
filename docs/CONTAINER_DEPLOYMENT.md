# Container Deployment

This stack packages Cognitive-Loop-OS as an installed wheel and runs one durable
application process for Core, Knowledge-Base, and the internal Research mount.
SQLite lives on one local named Docker volume. This is for a single host,
single worker, and local SSD-backed SQLite only; it is not a multi-host, Kubernetes,
Postgres, Redis, or scaled-worker deployment.

## Build

```bash
docker compose --env-file .env.container build
```

The image uses digest-pinned Python and uv bases. Runtime and build inputs come
from the committed `uv.lock`; `setuptools` is pinned exactly, exported with
hashes into the builder-only environment, and the wheel is built with an explicit
Python 3.11 interpreter and `--no-build-isolation`. After `pip check`, the runtime
removes pip, setuptools, wheel, and the builder-only `jaraco.context`. No APT
packages are installed. Caddy's runtime is a scratch image containing only a
Caddy `v2.11.4` binary rebuilt by the digest-pinned Go 1.26.5 builder, its module
build provenance, the CA bundle, and writable data/config directories; Alpine's
curl/c-ares package set is not copied into production. The publish job pushes only
when its deterministic rebuild has the same image ID as the completed smoke job.

Before the stack starts, pinned Trivy checks both final runtime images for
CRITICAL, HIGH, and MEDIUM vulnerabilities with an available fix. Any such finding
fails the job. Findings for which no upstream fix exists remain visible in scan
reports but do not create an impossible permanent release block; the next rebuilt
base is re-evaluated on every run.

## Configure

```bash
cp .env.container.example .env.container
openssl rand -hex 32
openssl rand -hex 32
```

Put different generated values in `COGNITIVE_API_KEY` and
`COGNITIVE_JWT_SECRET`. The example intentionally leaves both empty so Compose
fails until the operator generates real values. Set `COGNITIVE_DOMAIN`,
`CADDY_TLS_EMAIL`, and keep `.env.container` untracked.

## Start

```bash
docker compose --env-file .env.container up -d migration core caddy
```

`migration` is the only container schema owner. It creates only the empty database
file, then applies every registry owner whose kind starts with `sqlite`, currently
`core.sqlite`, `taskpack.sqlite`, and `research.sqlite`. `core.sqlite` owns both
baseline DDL groups and their normalized table/constraint/index contract; no
container entry point creates tables outside `MigrationOperator`. `core` starts
only after the migration job succeeds, validates the complete schema and current
operator provenance through read-only SQLite connections, and then serves Core,
`/kb`, and `/internal/research` from one process, establishing one durable SQLite writer.
Caddy is the only public entry point and blocks `/internal/*`.

The gateway enforces role authorization after authentication: `readonly` is
safe-method only, ordinary `user` tokens cannot invoke backup, runtime execution,
sleep-loop control, host-file conversion/ingestion, token issuance, or internal
Research routes, and the provisioned API-key administrator retains those controls.

## Health

```bash
curl -fsS https://$COGNITIVE_DOMAIN/health
docker compose --env-file .env.container exec -T core \
  python -c "import os, urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/internal/research/health', headers={'X-API-Key': os.environ['COGNITIVE_API_KEY']}); urllib.request.urlopen(r, timeout=5)"
docker compose --env-file .env.container ps
```

Caddy overwrites `X-Forwarded-For` and `X-Real-IP` with the direct client peer
before proxying. The app accepts those headers only from Caddy's fixed
`172.28.0.2/32` address; other containers on the edge network cannot rotate
forwarded identities to evade pre-auth or anonymous rate-limit buckets.

## Migration

```bash
docker compose --env-file .env.container stop caddy core
docker compose --env-file .env.container run --rm migration
docker compose --env-file .env.container run --rm core migration-status
docker compose --env-file .env.container up -d core caddy
```

Migration truth is `shared.migration_runner.default_registry`. The one-shot
container command applies only registry owners whose kind starts with `sqlite`;
Vector/FTS switch owners remain explicit operator actions because they require an
existing active index. Application startup does not create or migrate tables. If
migration has not run or the ledger has pending schema work, `core` fails closed
before Uvicorn starts.

## Backup

```bash
docker compose --env-file .env.container --profile ops run --rm --no-deps integrity
docker compose --env-file .env.container --profile ops run --rm --no-deps backup
```

Backups are SQLite backup API snapshots plus a manifest binding source identity,
backup SHA256, migration ledger, migration status, and required domain
invariants. A missing or mismatched manifest is rejected. The explicit
`--no-deps` is required for ops one-shots: the stack has already completed its
schema gate, and starting the `migration` dependency while Core holds the runtime
lease must fail closed rather than rerun schema ownership online.

## Restore Drill

Stage a candidate from an exact verified backup:

```bash
export COGNITIVE_RESTORE_BACKUP=/app/data/backups/cognitive_os_YYYYMMDDTHHMMSS.sqlite
docker compose --env-file .env.container --profile ops run --rm --no-deps restore-candidate
```

## Restore Activation

Activate only while the app is offline:

```bash
docker compose --env-file .env.container stop caddy core
export COGNITIVE_RESTORE_CANDIDATE=/app/data/backups/restore-candidates/restore_YYYYMMDDTHHMMSS.sqlite
docker compose --env-file .env.container --profile ops run --rm --no-deps restore-activate
docker compose --env-file .env.container up -d core caddy
```

`restore-activate` verifies that the candidate manifest is bound to this exact target
database, requires the OS runtime lease held across the Core/Uvicorn process to be
free and holds that lease through replacement and compensation, then takes an exclusive
SQLite lock, checkpoints/removes WAL and SHM sidecars safely,
atomically replaces the live database, verifies it after replacement, and restores
the previous live database from a compensation copy if activation fails. Backup and
candidate manifests are also bound to a persistent UUID stored on the named data volume,
so the common in-container pathname alone cannot authorize a cross-deployment restore.

## Upgrade

```bash
docker compose --env-file .env.container stop caddy core
docker compose --env-file .env.container build --pull
docker compose --env-file .env.container up -d migration core caddy
docker compose --env-file .env.container ps
```

Run `integrity` and a fresh `backup` before upgrading. Do not scale `core` above
one replica without a separate SQLite and rate-limit review.

## Rollback

Keep the previous immutable GHCR SHA tag available before upgrade. To roll back
code, pull and retag that verified image as `cognitive-loop-os:${COGNITIVE_IMAGE_TAG}`
and restart without rebuilding the current source tree. To roll back data, use
only the verified offline restore activation flow above.
