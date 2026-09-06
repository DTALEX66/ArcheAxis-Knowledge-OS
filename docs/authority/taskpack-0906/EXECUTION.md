# 2026-09-06 Full Loop execution

User authorized execution of `ARCHEAXIS-UPDATED-FULL-LOOP-TASKPACK-2026-09-06.zip`.
Package: 2026-09-06-r1; all 25 manifest file hashes verified. Baseline:
`4ca46eaf94c486dadcf200aac6b41cd968b1ce6e`; remote main read back at start.
The package supersedes r2/r3 plans, not historical test receipts.
The original 21-task DAG is preserved byte-for-byte as [TASKS.json](TASKS.json),
SHA-256 `1aa5c17c94f8c279987b5f4c70777e25d3614b6419fda65fd351abf71ff6bc94`.
It remains a frozen plan (`plan_only`), not an issued remote authorization or
implementation claim. Early repairs below do not satisfy unmet task dependencies.

## Accepted scope and ownership

- Formal desktop: `apps/ArcheAxis.Desktop`, C#/Avalonia; Rust owns a separate
  vNext database; Python workers provide computation only. Existing Green
  v0.6.14 and its user data stay recoverable. No release/version churn.
- E drive remains prohibited. Shared tools/models stay in existing libraries.
- Development root: project-owned `.project-local`; `.hermes` is preserved legacy
  material. Product workspaces and agent-private configuration are separate.
- One writer owns `codex/full-loop-0906`; the quality worker used its own
  `codex/worker-quality-0906` worktree. Its three-file patch was reviewed and
  integrated serially; its dirty worktree is retained. Storage/CI review is read-only.
- T20 is inventory/preservation planning; no blanket deletion or claimed GB savings.

## Progress ledger

| Tasks | State | Next acceptance |
| --- | --- | --- |
| T00 | PARTIAL | Approved decisions loaded; actual shared toolchain/local Python verified; baseline intake still to finish |
| T19 | TESTED_LOCAL / PARTIAL | Shared launcher and normal/linked/concurrent/failure path tests pass; remaining legacy fixed-path entrypoints need adoption |
| T01/T02 | PARTIAL | Classifier/actual receipt/worker schema regressions implemented; complete cross-language DTO and no duplicate CI still open |
| T17 | PLANNED | Existing inventory reviewed for bounded reuse assignments |
| T03/T04 | TESTED_LOCAL / PARTIAL | CAS originals, transaction/replay/migration and verified backup/archive implemented; writer actor, process lock, executor and Supervisor still open |
| T05/T06/T07 | TESTED_LOCAL / PARTIAL | Byte-faithful CER/WER and loss/coverage regressions pass; real corpus, all format chains and worker/Core integration still open |
| T08/T09/T10/T11 | PLANNED | Research, knowledge and both usage/feedback loops |
| T18/T12 | PLANNED | Interactive Avalonia workbench with real Core integration |
| T13/T14 | PLANNED | Nonempty migration, old capability absorption, index closure |
| T15/T16 | PLANNED | Same-candidate Windows qualification and reversible delivery |
| T20 | PLANNED | Byte-based non-following inventory; unknown assets retained |

Current order: finish T19 entrypoint exceptions and T00/T17 baseline inventory,
then T01/T02 real contracts, T03 writer ownership, T04 executor, format workers
and the actual desktop/learning loops. T20 read-only inventory tooling is running
in the separate worker worktree; no cleanup is authorized merely by a size result.

## Foundation slice evidence and known limits

Evidence below is local execution on a dirty worktree based on the baseline SHA,
not exact-SHA CI or installed delivery. Run artifacts are ignored development
data, not uploaded source; this ledger retains the compact result.

- Rust workspace: `python -B scripts/runtime/dev.py -- cargo test --workspace --locked --offline -q`,
  PASS, run `be268a2d33/82aa87283335`. Includes 8 job atomicity/migration tests,
  API rejection/readback, 6 archive tests and 2 online-backup original/protection tests.
  The current-run 12-step in-process journey receipt passed strict identity/step validation;
  its worker receipt is simulated, not real worker qualification.
- Python full suite: `scripts/ci/run_tests.ps1 --full -q --tb=short`, run
  `be268a2d33/82bf1c1f0ccf`: 2144 passed, 7 skipped, 1 failed (removed historical
  normalization link). That link is restored as historical, not current authority.
  Follow-up targeted verification PASS: 81 tests and 10 subtests, run
  `be268a2d33/266cbe5d9306`, covers authority links, CI/classifier, runtime paths
  and byte-faithful worker regressions. This is not a second full-suite result
  and not a claim that all 21 taskpack tasks passed.
- Windows Avalonia shell build: shared .NET 10.0.400, `dotnet build
  apps/ArcheAxis.Desktop/ArcheAxis.Desktop.csproj -v minimal -p:NuGetAudit=false`,
  PASS with zero warnings/errors, run `be268a2d33/50fe8d007849`.
  Build outputs are under `.project-local/build/be268a2d33/dotnet/`.
  This is compilation only; the UI still displays the starter content.
- Supervisor regression harness: `dotnet run --project
  tests/runtime-paths/CoreSupervisor.Tests`, PASS, run `be268a2d33/04e9c814e017`.
  Exercises a real unrelated loopback service, an owned stderr-flooding child
  cancelled before readiness, and real Rust Core using a spaced database path,
  an OS-assigned port, HTTP handshake and shutdown. Old wrong-workspace attach
  and Core reporting port zero were reproduced before their fixes.
- Repository conventions PASS, run `be268a2d33/901bebc82b93`.
- No new Release/tag/version, Green replacement, user-data migration or E-drive
  access was performed. No remote CI is qualified by these local runs.

Remaining safety/qualification gaps (do not conceal):

1. Store still exposes SQLite connections; the formal single writer actor and
   cross-process workspace lock remain T03. Backup source validation is pinned
   to one read transaction; destructive restore still needs full fault injection.
2. CAS and archive restore preserve original bytes and reject bad hashes, FK,
   future/unrelated databases and existing destinations. Publication uses
   same-filesystem no-clobber hard links; NTFS tested, other filesystems unqualified.
   Crash between object publication and DB publication can leave `<target>.objects`
   with no DB. Preserve this directory, inspect it, and use a different fresh
   destination for retry. Never delete it blindly. Automatic interrupted-publication
   recovery and power-loss durability remain unqualified. Ordinary cleanup
   failures can also leave owned staging objects; errors must not mean “cleaned”.
3. Legacy metadata-only archive formats are rejected by the new v2 path; they
   cannot reconstruct absent originals. Nonempty legacy migration remains T13.
4. Actual Rust/C#/Python DTO roundtrips remain T02. New worker coverage fields
   must not be silently discarded at the Core boundary. Local engine probes are
   not full multi-format accuracy or full-chain evidence.
5. Supervisor fixed-port attach, readiness cancellation/drain and silent-child
   startup are fixed in the tested slice. Launch authentication, process-level
   workspace lock, crash-restart policy and the actual interactive UI remain open.
   Do not launch the new GUI as the user's usable product.
6. Initial .NET first-run output reported development-certificate installation;
   trust/credential stores were not inspected or modified by commands. The launcher
   now disables ASP.NET certificate generation for subsequent runs. No certificate
   cleanup was attempted because ownership has not been established.

## Execution rulings

- Current user authorization adopts `.project-local` over older guidance naming
  `.hermes`. No global software configuration is changed.
- Routing is not an OS sandbox. External-root overrides are rejected until
  an explicit ownership configuration is implemented.
- Historical receipts retain their original test SHA; current handoff instructions
  point to the replacement launcher.
- A source compile or Green install is not vNext completion. Full tasks remain
  open until their acceptance, including negative paths, is measured.
