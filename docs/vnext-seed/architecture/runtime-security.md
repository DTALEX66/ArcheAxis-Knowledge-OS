# Runtime and security baseline

## Process tree

Avalonia is the Supervisor and launches exactly one Rust local service. Rust launches capability workers on demand. Closing the desktop requests graceful shutdown, waits a bounded interval and then terminates only descendants carrying the current launch identity.

Process separation is a fault-containment boundary, not a complete sandbox for
hostile native code. Day-20 capability packs are trusted-but-fallible code with
pinned provenance. Untrusted third-party executables require a later OS sandbox
and a separate threat-model decision.

## UI to Core

- Bind only 127.0.0.1 on an operating-system-selected random port.
- Generate a high-entropy launch secret and deliver it through an inherited
  control pipe. Never place it in command-line arguments, a repository file,
  process-wide environment variables or logs. Use a challenge/proof handshake
  and derive the short-lived HTTP credential after the child is bound.
- Require bearer token, request ID, contract version and idempotency key where applicable.
- Reject Host, Origin or protocol versions outside the local contract.
- Do not log tokens, raw personal content or full model prompts by default.

## Core to Python

- Spawn a pinned capability pack with a clean working directory and constrained environment.
- Use one NDJSON message per line; stdout is protocol-only and diagnostics go to stderr.
- Validate request and response schemas, asset hashes and output hashes.
- Treat `job://input/<sha256>` and `job://output/<sha256>` as opaque identifiers,
  never filesystem paths. The final URI component must equal the sibling hash.
  Reject dot segments, extra path levels, percent escapes, backslashes, query,
  fragment, case drift, symlink/junction/reparse-point escape and any resolved
  path outside the canonical job root.
- Validate the Hello minor interval, let Core choose the highest common minor,
  require the worker to echo it, and reject out-of-range or mid-session changes.
- Enforce deadline, output-size limit and child-process cleanup.
- A worker receives opaque read tokens or job-local copies, never the main database path.
- Network access is denied by default and explicitly declared per capability.
- Launch Python with isolated/unbuffered settings (`-I -u`), an allow-listed
  environment, a job-local staging directory and stdout reserved for protocol.
- On Windows, Supervisor owns a Job Object with kill-on-close; Rust receives a
  nested job/control identity and never terminates unrelated processes.

## Storage

- Store immutable originals under objects/sha256 and reference them by hash.
- Keep the SQLite database, WAL and SHM on one local filesystem.
- Only WriterActor holds the read-write connection; commands serialize mutation.
- WriterActor runs on one dedicated thread with one bounded input queue and one
  read-write connection. A command uses `BEGIN IMMEDIATE` and commits domain
  state, audit, outbox, idempotency record and receipt together.
- Enable foreign keys, bounded busy timeout and short transactions.
- Use SQLite Online Backup or a qualified VACUUM INTO path. Never copy an active database with WAL/SHM as a backup.
- Export validates manifest, schema, record counts and hashes before restore into a new workspace.
- CAS writes go through a job staging file, streamed SHA-256, fsync/close,
  atomic rename into the hash path, and only then a database reference.

## Windows packaging

Day 20 Green contains all required runtimes and one qualified capability pack; it requires no SDK or global Python. Program files are treated as read-only. Even Green stores user data under `%LOCALAPPDATA%/ArcheAxis/profiles/<profile-id>/`; it is not "portable" merely because the executables are in a folder. Launch shows no console, update is disabled, and uninstall never deletes user workspaces.

Week 6 may add Setup and an explicit Portable mode. Portable requires a marker,
a writable local NTFS location, a visible data-path warning and refusal to run
the active SQLite database from network shares or cloud-synchronised folders.

## Failure injection required by Preview

- wrong contract version
- invalid or reused launch token
- worker timeout, crash and malformed JSON
- duplicate command and stale revision
- process termination during import
- Core and full-application restart
- export interruption and restore hash mismatch
- clean shutdown with no orphan process
