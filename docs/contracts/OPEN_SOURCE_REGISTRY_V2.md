# Open Source Registry V2 Contract

## Purpose

Registry V2 separates candidate inventory from provenance and implementation
evidence. Existing V1 records remain lossless candidates until their source,
license, implementation, and rollback evidence is independently recorded.

## Evidence states

| State | Meaning | May be described as verified? |
|---|---|---|
| `unknown` | No independently recorded provenance or implementation evidence | No |
| `recorded` | Evidence metadata is recorded, but verification gates are incomplete | No |
| `verified` | Required source, license, implementation, test, runtime, and rollback evidence passed | Yes, for the bounded adapter/capability only |

`candidate`, `reference_only`, `deferred_review`, and
`adapter_contract_pending` remain governance states. They must not be silently
upgraded when provenance fields are added.

## Provenance fields

Each future V2 entry may record:

- `canonical_source`
- `source_revision`
- `license_snapshot`
- `implementation_paths`
- `rollback_handle`
- `state`

Missing values are represented as `null` or an empty collection and mean
`unknown`; they are not replaced with guessed URLs, revisions, licenses, or
synthetic implementation paths.

## Registry/ledger boundary

`validate_registry_ledger_pair()` verifies the raw `project_id` set, shared
identity fields, closed ledger execution states, and the requirement that an
`implemented` ledger entry has implementation evidence. It does not promote
the source Registry status and does not claim that an upstream project has
been installed or absorbed.

## Rollback

Registry migration work must preserve the pre-change JSON bytes and SHA-256,
use a new commit, and record the exact rollback commit or backup manifest.
Raw duplicate IDs remain separate records until an explicit identity decision
is reviewed; names are not a primary key.