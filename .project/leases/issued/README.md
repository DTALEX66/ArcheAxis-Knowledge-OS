# Issued authority grants

These are remote-verifiable authorization records, not same-machine locks.
Each grant must validate against `authority-grant.schema.json`, bind one issued
envelope by SHA-256, cover every serial resource touched, be unexpired and
unrevoked, and be added in the same metadata-only activation commit at
`.project/leases/issued/<plan-id>/<task-id>/<issuance-id>/<grant-id>.json`.
Revocation is a later immutable record under `.project/leases/revocations/`;
the original grant and activation commit are never edited.

The Git-common-dir `archeaxis-agent/state.sqlite` database only coordinates
local worktrees. It can never replace this protected-branch grant.
