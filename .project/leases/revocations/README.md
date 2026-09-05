# Authority grant revocations

One immutable JSON record named `<grant-id>.json` revokes one previously issued
grant and validates against `authority-revocation.schema.json`. A revocation
never edits the original grant or rewrites its activation commit. Scope Gate
checks the protected branch for a matching revocation before accepting work.
