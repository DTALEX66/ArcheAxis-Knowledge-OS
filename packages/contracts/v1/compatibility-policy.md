# Contract compatibility policy

`/api/v1` and schema names ending in `/v1` identify the major version only.
API, worker protocol, database schema and export format version independently.

## Minor negotiation

1. Each peer advertises an inclusive continuous range
   `[min_minor, max_minor]` and must satisfy `min_minor <= max_minor`.
2. The selected value is
   `min(local.max_minor, peer.max_minor)`. Negotiation succeeds only when that
   value is at least both minimums; otherwise it fails closed.
3. Core selects the minor for a worker request. The worker must echo it exactly
   in the response. A different value, an out-of-range value or a mid-session
   change is rejected.
4. A component may advertise a minor only while it retains the corresponding
   encoder and strict validator. It may not claim an old minor while silently
   using only the newest representation.
5. The sender emits only fields and values defined by the selected minor.
   Fields introduced by a higher minor are omitted after downgrade.

## Compatible and breaking changes

A minor may add optional fields or endpoints, or relax an input constraint,
but those additions are usable only after both peers negotiate that minor.
Deleting a field, changing its type or meaning, adding a required field,
tightening valid input, or changing a state transition requires a new major.

Closed command, status and authority enums cannot gain values in a minor.
Only an explicitly declared extensible informational response enum may map an
unknown value to `UNKNOWN(raw)`. Requests reject unknown fields. Worker results
are untrusted input to Core and reject unknown fields and closed-enum values;
they are not covered by a permissive “response consumer” exception.

Enums serialize as strings, never language ordinals. Generated Rust, C# and
Python bindings are never hand-edited, and regeneration must leave the Git tree
clean.

## Mutation and identity

Every mutation requires `Idempotency-Key`; aggregate mutation also requires an
`If-Match` version. Same key plus same canonical request replays the original
result; same key plus different request is `AAK-CON-002`. Canonical identities
use the digest profile in `docs/operations/digest-canonicalization.md`.

Contract qualification includes overlapping and non-overlapping minor ranges,
request/response mismatch, mid-session change, downgrade field omission,
valid and invalid examples in all three languages, NFC/LF/code-point anchors
with Chinese, emoji and combining characters, canonical JSON/hash fixtures,
major mismatch, unknown fields/enums, stale version and idempotency conflict.
