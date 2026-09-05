# Day-3 parallel dispatch

Dispatch only after PR-04 is merged and all envelopes are rebased to its exact SHA.

## Rust lane PR-05

Program ceiling: `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`,
`crates/archeaxis-{domain,application,store-sqlite,api,sidecar-protocol,archive}/**`
and `services/local-service/**`. Tests belong to the Journey lane unless an
issued Rust slice explicitly includes a narrower already-authorized test path.

Deliver: process start, version handshake, random loopback port, per-launch token, WriterActor owning the only read-write connection, empty schema migration, health and shutdown.

Reject: FFI, UI code, Python database access, shared legacy database or unversioned DTO.

## Avalonia lane PR-06

Program ceiling: `apps/desktop/**`, `global.json` and
`Directory.Packages.props`. Journey tests remain a separate slice/lane.

Deliver: window shell, Supervisor, child-process start/stop, generated API client, status/error panel and no terminal window.

Reject: embedded domain rules, SQLite packages, hand-written DTO drift or direct worker launch.

## Python lane PR-07

Program ceiling: `services/python-workers/**`. Contract tests remain under the
contract or Journey authority selected by a separate slice.

Deliver: NDJSON runner, version handshake, one echo capability, deadline, cancellation, malformed input rejection, loss/measurement envelope and deterministic exit.

Reject: database libraries for the main store, verified/mastery conclusions, network access not declared by the capability manifest or writes outside its job directory.

## Journey lane PR-08

Program ceiling: `fixtures/golden/**`, `tests/contract/**`,
`tests/integration/runtime/**` and `tests/journey/**`; it cannot widen to every
fixture or test path.

Deliver: project-owned fixtures, process harness, exact command/OS/runtime receipt, timeout/crash/no-orphan checks and the skeleton of JV-001 through JV-012.

Reject: mocks as milestone proof, private user material as a fixture or a skipped required step reported as pass.
