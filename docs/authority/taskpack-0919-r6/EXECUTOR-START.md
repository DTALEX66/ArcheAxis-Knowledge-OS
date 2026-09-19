# R6 Executor Start

- Plan ID: AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6
- Taskpack: TASKPACK.md
- Taskpack SHA-256: $sha
- Current execution ledger: docs/current/R6-EXECUTION.md
- Current state: docs/current/R6-STATE.json
- Implementation plan: docs/superpowers/plans/2026-09-19-r6-local-green-absorb-first.md

## Required order

1. A00 authority reset and R6 registration.
2. A01 version/release freeze and A02 resource authority.
3. A03 capability registry before new capability implementation.
4. A04–A12 only against frozen contracts and registered providers.
5. A13–A14 require isolated staging and real first-use evidence.
6. A15 is independent and cannot be self-signed by the executor.
7. A16 stops at LOCAL_GREEN_READY_FOR_OWNER_REVIEW or NOT_READY; no release.

## Boundaries

Do not access E:, private .codex/.zcode/.hermes, credentials, real Green user data, or shared libraries except for exact authorized metadata probes. Do not create tags/releases, modify external libraries, replace the installed Green runtime, or claim runtime/CI evidence from documentation alone.
