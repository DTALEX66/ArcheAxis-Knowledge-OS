# R6 Executor Start

- Plan ID: AAK-LOCAL-GREEN-ABSORB-FIRST-20260919-R6
- Taskpack: TASKPACK.md
- Taskpack source SHA-256 (user-provided CRLF bytes): `dcc51e922a35d30ca361e9014e040674b62cee644a3ea57aae12ffa6c2949529`
- Repository Taskpack SHA-256 (canonical LF bytes): `788c5d50b5953d21eb9f67587d5406d37ad2e5457c2ca3b991399d9988e5951b`
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
