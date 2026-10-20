# Week-1 gates and owner checkpoints

## Day 1 — authority

- PR-00 is merged alone.
- The old G0 rule continues to protect the legacy database.
- The vNext separate-database exception is explicit, reviewable and reversible.

## Day 2 — governance and contract skeleton

- PR-01 hermetic full-suite and PR-02 fail-closed qualification receipt pass.
- PR-03 hostile scope-gate fixtures pass for rejection and allowed cases.
- PR-04 is issued only after PR-03 merges.
- No runtime lane starts against an unmerged contract.

## Day 3 — four disjoint lanes

- PR-05 owns Rust service/WriterActor only.
- PR-06 owns Avalonia shell/Supervisor only.
- PR-07 owns the Python runner/capability fixture only.
- PR-08 owns contract/process fixtures only.
- No issued slice spans two serial resource families; no grant is held while
  waiting for a machine, artifact, credential or approval. Each slice stays at
  or below 25 changed files, 16 effective hours and 48 elapsed hours.

## Day 5 — Hello Triangle architecture proof

On a clean Windows 11 machine, Avalonia starts one Rust child on a random
loopback port, performs a version/auth handshake, and Rust starts one pinned
Python worker over NDJSON. Demonstrate success, incompatible major, timeout,
malformed output, crash, visible error and clean Job-Object shutdown. Python and
C# have no database package/path/handle. Rust persists one receipt, restarts and
online-backs it up.

This is not product Alpha and must not be presented as user-data-ready.

## Capacity and stop rule

The 4+2 week plan assumes an Owner/Integrator plus three or four active Agent
lanes. Across an 80 lane-day budget, reserve roughly 60% for product/infra, 25%
for tests/integration/package/recovery and 15% contingency. A task exceeding
two working days or 25 files splits before implementation. If a gate requires
weakening, skipping or another database writer, work stops for Owner review.
