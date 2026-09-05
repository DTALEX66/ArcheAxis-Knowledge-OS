# Digest canonicalization

All `*_sha256` governance fields use profile `AAK-JCS-1` unless the field
explicitly says it hashes raw artifact bytes.

## AAK-JCS-1

1. Decode UTF-8 and reject a byte-order mark, duplicate mapping keys, YAML
   aliases, custom tags, non-string mapping keys, non-finite numbers and values
   outside the JSON data model.
2. Parse JSON directly or YAML 1.2 core syntax, then convert to the same JSON
   data model.
3. When a schema names excluded fields, remove exactly those fields. A receipt
   payload digest excludes only its own `receipt_payload_sha256` field.
4. Serialize with RFC 8785 JSON Canonicalization Scheme, encode UTF-8 and apply
   SHA-256. Emit 64 lowercase hexadecimal characters.

Implementations must qualify cross-language fixtures containing Chinese,
emoji, combining characters, negative zero, integer boundaries, reordered
keys and duplicate-key rejection before they may sign governance records.

RFC 8785 sorts object keys but does not sort arrays. Before hashing, every
GatePlan producer MUST emit `sources.*` and each trace `evidence_refs` in
ascending UTF-8 byte order; `selection_trace` in `(source-rank, rule_ref,
gate_id)` order where `task=0`, `path=1`, `risk=2`; and de-duplicated `gates`
in `gate_id` UTF-8 byte order. A Program completion receipt MUST order
`slice_receipts` by `(task_id, issuance_id, receipt_payload_sha256)`, atom
coverage arrays by atom ID, and unresolved string arrays by UTF-8 bytes.
Nonconforming order is rejected before digesting. Cross-language fixtures must
prove that shuffled inputs materialize byte-identical payloads and digests.

## What each identity means

- Git commit and tree fields are full native Git object IDs, never truncated.
- `envelope_sha256`, grant digests, Program graph digests, Gate Registry and
  GatePlan digests use `AAK-JCS-1`.
- The authority-manifest payload is a sorted array of protected policy paths,
  their Git blob IDs and schema versions as observed at the subject parent; its
  digest uses `AAK-JCS-1`. It excludes issued envelope/grant instances,
  revocations, receipts and activation SHA.
- A consumed-interface manifest is sorted by path, mode and blob SHA-256 before
  `AAK-JCS-1` hashing.
- Artifact `sha256` fields hash the exact raw bytes delivered to the consumer.

Never hash pretty-printed YAML bytes and call that a semantic digest. Never
place a hash inside the exact byte sequence that the hash claims to cover.
