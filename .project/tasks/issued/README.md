# Issued task envelopes

Only immutable documents with `schema: archeaxis.task/v1` and `state: issued`
belong here. Templates, placeholders and null authorization fields are rejected.

The path is
`.project/tasks/issued/<plan-id>/<task-id>/<issuance-id>.json`. One metadata-only activation
commit adds the envelope and every referenced authority grant. The task branch
must start from that activation commit or a later base proven disjoint by the
scope gate. The pull request must not modify its issued envelope.

`execution_mode: qualification-no-diff` requires empty operations and paths,
zero file/line/binary limits, no authority grant and no repository diff after
the activation commit. Qualification outputs are job-local or external only.

A PR-32 implementation envelope additionally carries `manifest_scope`. Its
exact paths must be the CI-recomputed, digest-bound partition of one approved
`retire` entry in `LEGACY_MANIFEST.yaml`; pseudo paths and globs never authorize
a write or deletion.
