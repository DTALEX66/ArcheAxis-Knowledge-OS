# 021 Container Stack

Implemented a production-oriented single-host Linux container stack for the committed baseline:

- multi-stage wheel image, non-root runtime, single Uvicorn worker, no reload;
- one-shot migration adapter delegating to the `MigrationOperator` registry for all SQLite schema owners;
- Compose migration gate, one unified Core process with mounted Knowledge Base and internal Research, Caddy proxy, named SQLite volume, and offline ops jobs;
- Caddy production TLS config plus CI-local override, exposing only Core while Research remains on an internal network;
- digest-pinned base images, a verified `uv.lock`, and GHCR publication after the full `main` container smoke;
- deployment runbook documenting SQLite, single-host, and future migration-runner limits.
