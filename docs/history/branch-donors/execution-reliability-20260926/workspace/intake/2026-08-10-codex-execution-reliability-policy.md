# Codex execution reliability policy intake

Date: 2026-08-10

## Decision

Adopt one stable project policy for Windows shell behavior, Git ref semantics,
Python environment qualification, exact runtime cleanup, failure
classification, and completion evidence. `AGENTS.md` remains the concise
operator contract, `docs/VERIFICATION_POLICY.md` remains the verification
cadence authority, and `docs/CODEX_EXECUTION_RELIABILITY.md` owns the detailed
reliability rules.

## Source absorbed

The policy absorbs the durable lessons from TaskPack
`CLO-CODEX-EXECUTION-RELIABILITY-20260810`: writer isolation, explicit Git
refs, PowerShell quoting, environment-versus-product failure separation,
postcondition-based cleanup, squash-merge interpretation, and layered delivery
evidence.

Exact PR numbers, SHAs, test counts, and ignored residue paths remain in their
own TaskPack, append-only execution log, Git history, or CI. They are excluded
from the stable policy so that the policy cannot become stale evidence.

## Compatibility

- Runtime-only state is standardized under ignored `.hermes/task-runtime/`.
- User-deliverable local evidence is standardized under ignored
  `.hermes/task-artifacts/`.
- Existing `.gitattributes` remains the line-ending authority.
- No runtime implementation, dependency, public API, or release status changes.

## Verification scope

This is a documentation and governance change. Required checks are link
resolution, policy consistency, `git diff --check`, the repository convention
scanner when available, and final diff/status inspection. Full application
tests are not required by `docs/VERIFICATION_POLICY.md` for this risk tier.
