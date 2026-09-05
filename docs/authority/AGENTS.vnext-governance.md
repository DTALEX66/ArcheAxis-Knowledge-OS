# ArcheAxis Knowledge Agent Contract

This file is vendor-neutral. Codex, DSH, Hermes and future agents follow the same repository contract.

## Mission

Deliver the smallest trustworthy loop: import original material, create a precise anchor, save personal knowledge or a machine candidate, review it, search back to the original, record one learning event, restart, export and restore.

## Execution-instruction priority

1. Platform safety constraints and the Owner's current explicit instruction.
2. Effective Owner Decision with an explicit supersession record.
3. PROJECT_CONTRACT.yaml.
4. DIRECTORY_AUTHORITY.yaml.
5. Versioned product contracts and protected policy schemas.
6. The immutable issued task envelope and authority grants read from their
   protected activation commit.
7. Root and nearest-directory AGENTS.md files, which may only narrow the above.
8. Ordinary ADR/design documents and historical handoffs.

Lower authority may narrow a rule but cannot widen it.

This priority resolves what an Agent may do. It is not the evidence ranking used
to decide whether a product claim is true.

## Evidence priority

For completion claims, prefer an exact-SHA owner journey and signed receipt,
then exact-SHA integration/contract tests, then unit/static checks. Source code,
mock output, an older SHA, a skipped job, model confidence or an Agent statement
cannot by itself prove the user-visible path. Personal notes and hypotheses may
still be stored; their evidence state limits use rather than admission.

## Before writing

- Confirm canonical Program/Task-ID, slice key, issuance, activation SHA, exact
  work base, branch, worktree, authority grant and coordination-lock holder.
- Read allowed_paths and forbidden_paths from the trusted base branch.
- Confirm dependencies have merged and generated contracts match their source.
- Verify remote authority grants from the protected activation commit. Use the
  shared Git-common-dir `archeaxis-agent/state.sqlite` only for same-machine
  coordination; `.project-local` is only worktree scratch.
- Stop if the issued envelope/grant is absent, expired, revoked, a template,
  self-modified, based on the wrong subject SHA, or detached from its Program graph.
- Confirm `not_before`, machine, artifact, rights, network and credential
  prerequisites are already satisfied. Never hold a grant while waiting for them.

## Write rules

- One issued slice equals one behavior, one execution lane, at most one serial
  resource family, one branch, one worktree and one Agent owner.
- A slice is at most 25 changed files, 16 estimated effective hours and 48
  elapsed hours. The Program blueprint and template are never authorization.
- Read access may span the repository; writes are limited to allowed_paths.
- Never edit the task envelope to grant more paths.
- Never write credentials, model files, user data, databases, logs, downloads, caches or Agent sessions into tracked paths.
- Existing tracked `.hermes/**` files are legacy inventory: change them only in
  an explicitly allowed maintenance/migration task and never store live Agent state there.
- Never modify main directly.
- Never combine contract, migration, dependency-lock and product-feature changes in one PR.

## Runtime authority

- Only Rust Core may open the vNext SQLite database read-write.
- Avalonia and Python must use versioned contracts; they never receive the main database path.
- Python output is a candidate or measurement, never verified, approved or mastered state.
- Legacy and vNext databases are never dual-written or live-synchronized.

## Protected serial paths

AGENTS.md, PROJECT_CONTRACT.yaml, DIRECTORY_AUTHORITY.yaml, LEGACY_MANIFEST.yaml, DECISION_SUPERSESSION_LEDGER.yaml, `.project/**`, `.github/**`, `packages/contracts/**`, database migrations, Cargo.toml/Cargo.lock, rust-toolchain.toml, global.json, Directory.Packages.props, `**/uv.lock`, packaging, version files and release manifests require a protected authority grant as well as the local coordination lock.

## Required receipt

Every completed slice produces an external CI attestation bound to its Program,
issuance, activation/base/head/tree, envelope and authority/interface/GatePlan
digests, grants, changed paths, commands and results, skipped checks,
contract/migration/packaging impact, risks, rollback verification and artifact
hashes. A required absent/skipped/cancelled/blocked/timed-out/failed gate is not
a pass. The receipt payload digest excludes its own digest field under
`AAK-JCS-1`; a later repository copy is non-authoritative metadata. Only a
Program completion receipt whose atom coverage is complete unlocks dependents.

## Done

Done means the user path works through the UI, normal and rejection paths are tested, state survives restart, failure is recoverable, no new database writer exists, and the result is bound to an exact commit and fixture hashes.
