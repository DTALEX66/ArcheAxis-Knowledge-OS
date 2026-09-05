# Legacy absorption and migration authority

The legacy product remains recoverable while vNext starts from an independent
storage root. This is capability absorption and one-way verified data migration,
not line-by-line Python-to-Rust translation.

## G0 supersession boundary

- Old product, database and aggregates retain their original G0 protection;
  Python remains the old database writer and Rust never opens it read-write.
- vNext has its own root, SQLite `application_id`, schema and Rust WriterActor.
- The exporter reads only an internally consistent read-only copy.
- Only the Rust importer writes a new vNext workspace.
- Shared databases, dual write, live synchronization and in-place takeover are
  forbidden.
- The audited 58 legacy SQLite connection sites are frozen exceptions. They no
  longer block the new workspace, but CI rejects a 59th site and the manifest
  maps every existing site to a table/operation/aggregate/replacement/removal
  gate.

Earlier Phase-0 advice to keep `shared/storage.py` or Python migration code as a
new Repository Facade is superseded for vNext. Those modules are semantic
oracles only.

## Decision algorithm

1. Unclear rights means `blocked` work status; it cannot become reuse.
2. Anything owning domain state or database mutation is `port`.
3. Pure deterministic logic with safe rights/effects is `reuse`.
4. Heavy parser/OCR/ASR/model capability with no authority is `wrap`.
5. UI, routing or behavior in a retiring stack is `oracle`.
6. Duplicate, placeholder, mock-only, unsafe writer or unreachable code is
   `retire`.

The five final decisions are reuse, wrap, port, oracle and retire. `blocked` is
only a temporary review state. Every baseline file must match exactly one
manifest entry after glob expansion; a catch-all oracle entry is forbidden.

## Migration package

```text
workspace.axmigrate/
  manifest.json
  manifest.jcs.sha256
  records/{assets,sources,anchors,knowledge,evidence,reviews,learning}.ndjson
  objects/sha256/<prefix>/<hash>
  mappings/legacy-ids.ndjson
  losses/export-rejections.ndjson
  rights/rights-manifest.json
```

The canonical RFC 8785 manifest digest and every internal object digest are the
identity. An outer archive hash is transport evidence only because ZIP bytes can
vary by tool.

## Export, validate and activate

1. Pin release v0.6.14, exact commit, locks, exporter and schema fingerprint.
2. Create a consistent legacy SQLite snapshot with Online Backup; do not copy
   active database/WAL/SHM files.
3. Run integrity and foreign-key checks on the snapshot.
4. Open it using URI `mode=ro`, OS read-only permissions, no network and an
   allow-listed schema. `PRAGMA query_only` is only an extra guard.
5. Emit stable-ordered JCS NDJSON, byte-exact CAS objects, ID mapping, rights,
   rejection and loss records. Unknown schema fails; fields are never guessed.
6. Rust dry-run validates schema, quota, normalized paths, hashes, references
   and losses without creating an official workspace.
7. Rust imports into a same-volume staging workspace, rebuilds projections,
   closes/reopens the database and runs integrity, logical digest and journey.
8. Only a `READY` receipt permits atomic same-volume activation of the new
   current pointer.
9. Preserve the old database, snapshot, package and receipts through the stable
   period.

## Differential gates

- Originals and attachments: byte-exact SHA-256.
- Source, personal knowledge, review text: canonical-exact.
- IDs, enums and time: semantic-exact after an explicit versioned mapping.
- Relationships/anchors/evidence: referential completeness plus canonical
  digest.
- FTS/vector/cache/community data: rebuild, then qualify using a fixed query
  set; never migrate them as truth.
- `unclassified_loss`, `hash_mismatch` and `dangling_reference` are zero.
- Two exports of one snapshot have the same manifest digest; the exporter does
  not change the source snapshot; repeated import is a no-op.
- Every rejected row retains source-row hash, stable reason code and suggested
  action.

Unsourced personal notes, definitions, opinions, hypotheses and rumor reports
are retained with unassessed verification. Machine material becomes a candidate.
An unprovable old review state becomes UNKNOWN, never ACCEPTED. A legacy folder
named “verified” is not proof.

## Rollback truth

1. Before activation: discard/quarantine staging; legacy is untouched.
2. After activation but before the first vNext business write: the current
   pointer may return to the old product.
3. After the first vNext business write: automatic rollback to the old writer is
   forbidden because histories have diverged. Recover a vNext Online Backup,
   fix-forward into a new workspace, or explicitly accept new-data loss and
   remigrate. Never reverse-sync into the old database.

## Retirement gate

Legacy active paths become retire-ready only after manifest coverage is 100%,
all entries have final decisions, the v0.1 exact-SHA journey passes, two fixed
fixtures and one real database copy migrate with zero unclassified loss, failure
and rollback drills pass, two Windows Green candidates pass, the Owner uses
vNext for 14 days without a blocker, all references and rights/notices are
preserved, and the deletion PR passes clean-clone/build/migration tests.

Git history, release assets, tags, backups and migration receipts remain. Do not
replace the old tree with a permanent `legacy/` dumping ground.

## Licence profile

Personal noncommercial use is a product-use profile, not a licence exception.
Default distribution contains reviewed MIT/Apache/BSD-class components with
required notices. Copyleft packs are separately qualified. Source-available,
model-restricted or noncommercial packs require explicit local installation.
Unknown/conflicting terms block bundling. Process isolation does not waive
licence, copyright, site-terms, privacy, robots or redistribution duties.
