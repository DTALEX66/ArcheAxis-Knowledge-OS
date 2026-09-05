# Legacy absorption work waves

## Wave L0 — freeze and census (Week 1)

- Pin v0.6.14, exact commit/tree/lock hashes and release assets.
- Expand the manifest until every baseline file matches exactly once.
- Register all 58 legacy SQLite connection sites; CI rejects a 59th.
- Restore the old release on a clean machine and retain the receipt.

Exit: zero unclassified files, explicit G0 supersession and no-new-writer gate.

## Wave L1 — fixture harvest (Weeks 1–2, parallel with vNext)

- Extract project-owned/synthetic inputs and expected output/loss behavior.
- Classify tests as fixture reuse, invariant port, implementation oracle or
  mock-only retire.
- Create cross-language canonical JSON/hash/text-offset fixtures.

Exit: every reused/wrapped behavior has a lawful deterministic fixture.

## Wave L2 — capability wrapping (Weeks 2–4)

- Qualify only TXT, Markdown and native-text PDF for Day 20.
- Remove storage, global environment and hidden network side effects.
- Package one worker runtime with a fixed lock, notices and crash/timeout tests.

Exit: one real capability works through Rust without database authority.

## Wave L3 — one-way data migration (Weeks 5–6)

- Build the legacy read-only exporter and migration package v1.
- Run Rust validate/dry-run, staging import, projection rebuild and differential.
- Pass two fixed databases plus one real user-database copy.

Exit: zero unclassified loss/hash mismatch/dangling reference and READY receipt.

## Wave L4 — retire-ready, not automatic deletion

- Observe two exact-SHA Windows Green release candidates.
- Owner uses vNext for at least 14 days without a blocking issue.
- Prove no runtime/CI/package/docs references require old paths.
- Preserve tags, release assets, notices, migration receipts and backups.

Exit: Owner may authorize small deletion PRs. Never replace the old tree with a
permanent unowned `legacy/` directory.
